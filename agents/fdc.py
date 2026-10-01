"""FDC bills (Excel, road). Uses the latest-dated sheet in each workbook."""

import re
from datetime import datetime
from io import BytesIO

import openpyxl
import pandas as pd

from utils.common import find_col, find_header_row, frame_from_header, strip_ext, to_date, to_num
from utils.excel_utils import sheet_to_raw, unmerge

AGENT = "FDC"
KEY = "fdc"
LABEL = "FDC"
DESCRIPTION = "FDC road bills (.xlsx) · latest-dated sheet used · total = rate × weight + ODA"
FILE_TYPES = ["xlsx"]
OUTPUT_FILE = "FDC_Combined.xlsx"
EXTRA_COLS = ["ODA_CHARGES"]

ORIGIN = "HYD"


def sheet_date(ws):
    for row in ws.iter_rows(min_row=1, max_row=10, values_only=True):
        for cell in row:
            if isinstance(cell, datetime):
                return cell
            m = re.search(r"(\d{2})[./-](\d{2})[./-](\d{4})", str(cell or ""))
            if m:
                try:
                    return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                except ValueError:
                    pass
    return datetime(1900, 1, 1)


def invoice_no_from(raw):
    for idx in range(min(len(raw), 30)):
        text = " ".join(str(x) for x in raw.iloc[idx].tolist() if x is not None)
        m = re.search(r"([0-9]{1,3}/[0-9]{4}-[0-9]{2})", text)
        if m:
            return m.group(1)
    return None


def is_header(cells):
    """Consignment/AWB column AND a date or weight column in the same row."""
    has_con = any(c.startswith("CON") and ("NO" in c or "NOTE" in c) or "AWB" in c for c in cells)
    has_other = any("DATE" in c for c in cells) or any("WEIGHT" in c or c in ("WT", "WT.") for c in cells)
    return has_con and has_other


def parse(data, name, log):
    wb = openpyxl.load_workbook(BytesIO(data), data_only=True)
    ws = max(wb.worksheets, key=sheet_date)
    log("info", f"{name}: using sheet '{ws.title}'")

    unmerge(ws, fill_merged=True)
    raw = sheet_to_raw(ws)

    header_row = find_header_row(raw, is_header)
    if header_row is None:
        raise ValueError(f"header row not found in sheet '{ws.title}'")

    df = frame_from_header(raw, header_row)
    df.columns = [c.upper() for c in df.columns]

    awb_col = find_col(df, ["CON.NO.", "CON NO", "AWB"])
    if awb_col is None:
        raise ValueError("consignment/AWB column not found")

    def col(cands):
        c = find_col(df, cands)
        return df[c] if c is not None else pd.Series(pd.NA, index=df.index)

    out = pd.DataFrame(index=df.index)
    out["AWB_NO"] = df[awb_col].astype(str).str.strip()
    out["AWB_DATE"] = to_date(col(["DATE"]), fmt="%d.%m.%Y")
    out["DEST"] = col(["DEST"])
    out["CHR_WT"] = to_num(col(["WEIGHT", "WT"]))
    out["RATE"] = to_num(col(["RATE"]))
    out["PKGS"] = to_num(col(["QTY"]))
    out["ODA_CHARGES"] = to_num(col(["ODA CHARGES", "ODA"]), fill=0)

    out = out[(out["AWB_NO"].str.len() > 5) & out["AWB_NO"].str.contains(r"\d", na=False)].copy()

    # FDC total is calculated: rate x weight + ODA (as agreed)
    out["BASIC_FRT"] = out["RATE"] * out["CHR_WT"]
    out["TOTAL_FRT"] = out["BASIC_FRT"] + out["ODA_CHARGES"]
    out["ADDON_CHR"] = out["ODA_CHARGES"]

    out["INVOICE_NO"] = invoice_no_from(raw) or strip_ext(name)
    out["ORIGIN"] = ORIGIN
    out["TRNSPT_MODE"] = "ROAD"
    out["LODGE_MODE"] = "N/A"
    return out
