"""POBC bills (Excel, one sheet per station invoice)."""

from io import BytesIO

import openpyxl
import pandas as pd

from utils.common import find_header_row, frame_from_header, to_date, to_num
from utils.excel_utils import sheet_to_raw, unmerge

AGENT = "POBC"
KEY = "pobc"
LABEL = "POBC"
DESCRIPTION = "Station invoices, one sheet per station (.xlsx) · origin taken from the sheet name"
FILE_TYPES = ["xlsx"]
OUTPUT_FILE = "POBC_Combined.xlsx"

CHARGE_COLS = ["awbc", "oth", "hndc", "dunt", "tspi", "tspo", "unit", "xray", "srch"]
EXTRA_COLS = ["BAGS"] + CHARGE_COLS

SKIP_SHEETS = ["bill summary", "way bill report", "waybill report"]
AIRLINE_PREFIX = r"\b(AI|6E|S5|SG|QP|IX)\b[- ]*"


def should_skip(sheet_name):
    name = " ".join(sheet_name.lower().split())
    return any(p in name for p in SKIP_SHEETS)


def map_column(c):
    c = c.lower()
    rules = [
        ("waybill", "AWB_NO"), ("awbc", "awbc"), ("route", "FLIGHT_NO"), ("srv", "TRNSPT_MODE"),
        ("pcs", "PKGS"), ("bag", "BAGS"), ("frt", "BASIC_FRT"), ("revenue", "TOTAL_FRT"),
        ("oth", "oth"), ("hndc", "hndc"), ("dunt", "dunt"), ("tspi", "tspi"), ("tspo", "tspo"),
        ("unit", "unit"), ("xray", "xray"), ("srch", "srch"),
    ]
    exact = {"date": "AWB_DATE", "dest": "DEST", "wt": "CHR_WT", "rate": "RATE"}
    if c in exact:
        return exact[c]
    for key, target in rules:
        if key in c:
            return target
    return c


def compute_mode(row):
    """Console/Direct rule for POBC (unchanged business logic)."""
    if str(row.get("TRNSPT_MODE", "")).strip().upper() != "AIR":
        return "N/A"

    def v(col):
        x = row.get(col, 0)
        try:
            return 0.0 if pd.isna(x) else float(x)
        except (TypeError, ValueError):
            return 0.0

    # One of awbc / dunt / oth is between 0 and 125 and every other charge is zero
    for single in ("awbc", "dunt", "oth"):
        others = sum(v(c) for c in CHARGE_COLS if c != single)
        if 0 < v(single) <= 125 and others == 0:
            return "Console"
    return "Direct"


def parse_sheet(ws, log):
    raw = sheet_to_raw(ws)
    header_row = find_header_row(
        raw, lambda cells: any("WAYBILL" in c for c in cells)
        and any("ROUTE" in c for c in cells) and any("DEST" in c for c in cells)
    )
    if header_row is None:
        return None

    df = frame_from_header(raw, header_row)
    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={c: map_column(c) for c in df.columns})
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.apply(lambda s: s.map(lambda x: x.strip() if isinstance(x, str) else x))

    if "AWB_NO" not in df.columns:
        return None

    # AWB clean + keep only real AWB rows
    awb = df["AWB_NO"].astype(str).str.strip().str.replace(AIRLINE_PREFIX, "", regex=True)
    df["AWB_NO"] = awb
    df = df[awb.str.contains(r"\d", na=False) & (awb.str.lower() != "nan")].copy()

    # Date: only this column is carried down when a bill leaves it blank
    # for following AWBs of the same day (charges are NEVER carried down).
    if "AWB_DATE" in df.columns:
        dates = to_date(df["AWB_DATE"])
        blanks = int(dates.isna().sum())
        dates = dates.ffill()
        carried = blanks - int(dates.isna().sum())
        if carried:
            log("info", f"sheet '{ws.title}': {carried} blank dates taken from the row above")
        df["AWB_DATE"] = dates

    if "DEST" in df.columns:
        df["DEST"] = df["DEST"].astype(str).str.replace(r"^(PAF-|POBC-)", "", regex=True).str.strip()

    origin = ws.title[2:5] if len(ws.title) >= 5 else ws.title
    df["ORIGIN"] = "IXM" if origin == "XM1" else origin

    for col in CHARGE_COLS + ["CHR_WT", "BASIC_FRT", "TOTAL_FRT"]:
        if col in df.columns:
            df[col] = to_num(df[col], fill=0)

    if "TRNSPT_MODE" in df.columns:
        df["TRNSPT_MODE"] = df["TRNSPT_MODE"].astype(str).str.strip().str.upper().replace({"ACG": "AIR", "RDS": "ROAD"})
    else:
        df["TRNSPT_MODE"] = "N/A"

    df["INVOICE_NO"] = ws.title
    return df


def parse(data, name, log):
    wb = openpyxl.load_workbook(BytesIO(data), data_only=True)
    frames = []
    for ws in wb.worksheets:
        if should_skip(ws.title):
            continue
        try:
            unmerge(ws, fill_merged=True)
            df = parse_sheet(ws, log)
            if df is not None and not df.empty:
                frames.append(df)
        except Exception as e:
            log("error", f"{name} / sheet '{ws.title}': {e}")

    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True, sort=False)

    df["LODGE_MODE"] = df.apply(compute_mode, axis=1)

    # AWB with "/" -> Console
    df.loc[df["AWB_NO"].str.contains("/", na=False), "LODGE_MODE"] = "Console"

    # RPR -> DEL with awbc 50 and handling charged -> Console
    if {"awbc", "hndc"} <= set(df.columns):
        rule = (
            (df["ORIGIN"].astype(str).str.upper() == "RPR")
            & (df["DEST"].astype(str).str.upper() == "DEL")
            & (df["awbc"] == 50)
            & (df["hndc"] != 0)
        )
        df.loc[rule, "LODGE_MODE"] = "Console"

    return df
