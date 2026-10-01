"""INDEX co-loader bills (Excel)."""

import pandas as pd

from utils.common import find_col, find_header_row, frame_from_header, strip_ext, to_date, to_num
from utils.excel_utils import read_raw_any

AGENT = "INDEX"
KEY = "index"
LABEL = "INDEX"
DESCRIPTION = "Co-loader bills (.xlsx) · Console when every extra charge is zero"
FILE_TYPES = ["xlsx", "xls"]
OUTPUT_FILE = "INDEX_Combined.xlsx"

# Charge columns kept in the output (between BASIC_FRT and TOTAL_FRT)
EXTRA_COLS = [
    "A.Do", "xray", "Tsp in", "Tsp out", "addntsp", "Addntsp Destination",
    "Unit", "Deunit", "Surch.", "Misc Chg.", "Other Dc", "Service", "Handling",
]

# If ALL of these are zero/blank -> Console, else Direct
MODE_COLS = [c for c in EXTRA_COLS if c != "A.Do"]


def parse(data, name, log):
    raw, _, _ = read_raw_any(data, name)

    header_row = find_header_row(raw, lambda cells: any("AWB" in c and "NO" in c for c in cells))
    if header_row is None:
        raise ValueError("header row (AWB No) not found")

    df = frame_from_header(raw, header_row)

    awb_col = find_col(df, ["Awb No", "AWB No.", "AWBNO"])
    if awb_col is None:
        raise ValueError("AWB No column not found")

    out = pd.DataFrame(index=df.index)
    out["AWB_NO"] = df[awb_col].astype(str).str.strip()
    out["AWB_DATE"] = to_date(df[find_col(df, ["Awb Date", "Date"])]) if find_col(df, ["Awb Date", "Date"]) else pd.NaT
    flight_col = find_col(df, ["Flight No", "Flight No.", "Flt No", "Flight"], exclude=["DATE", "DT"])
    out["FLIGHT_NO"] = df[flight_col] if flight_col else None
    out["ORIGIN"] = df[find_col(df, ["Origin"], allow_partial=False)] if find_col(df, ["Origin"], allow_partial=False) else None
    out["DEST"] = df[find_col(df, ["Dest.", "Dest"], allow_partial=False)] if find_col(df, ["Dest.", "Dest"], allow_partial=False) else None
    out["PKGS"] = to_num(df.get("Pkts"))
    out["CHR_WT"] = to_num(df.get("Charge Wt."))
    out["RATE"] = to_num(df.get("Rate"))
    out["BASIC_FRT"] = to_num(df.get("Basic Freight"))
    out["TOTAL_FRT"] = to_num(df.get("Total"))

    for col in EXTRA_COLS:
        src = find_col(df, [col], allow_partial=False)
        out[col] = to_num(df[src]) if src else pd.NA

    # keep real AWB rows only (drops totals / blank lines)
    awb = out["AWB_NO"]
    out = out[(awb.str.lower() != "nan") & (awb.str.len() > 5) & awb.str.contains(r"\d", na=False)]

    charges = out[MODE_COLS].apply(pd.to_numeric, errors="coerce").fillna(0)
    out["LODGE_MODE"] = (charges == 0).all(axis=1).map({True: "Console", False: "Direct"})

    out["INVOICE_NO"] = strip_ext(name)
    out["TRNSPT_MODE"] = "AIR"
    return out
