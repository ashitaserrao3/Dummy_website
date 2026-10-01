"""EDS bills (Excel). File name = ORIGIN-xxx-xxx... (first 3 parts = invoice no)."""

import pandas as pd

from utils.common import find_col, find_header_row, frame_from_header, strip_ext, to_date, to_num
from utils.excel_utils import read_raw_any

AGENT = "EDS"
KEY = "eds"
LABEL = "EDS"
DESCRIPTION = "EDS bills (.xlsx) · file name gives origin and invoice no."
FILE_TYPES = ["xlsx", "xls"]
OUTPUT_FILE = "EDS_Combined.xlsx"

ADDON_PARTS = ["AWB DO", "A/L CHG", "APT OUT", "APT IN", "SVC CHG"]
EXTRA_COLS = ADDON_PARTS + ["CGST", "SGST", "IGST", "AMOUNT"]

SOURCE = {
    "AWB_DATE": ["DATE"],
    "FLIGHT_NO": ["FLIGHT NO.", "FLIGHT NO"],
    "DEST": ["DSTN"],
    "PKGS": ["PCS"],
    "CHR_WT": ["CWGT KGS.", "CWGT KGS"],
    "RATE": ["RATE"],
    "BASIC_FRT": ["FREIGHT CHS"],
    "AWB DO": ["AWB DO"],
    "A/L CHG": ["A/L CHG"],
    "APT OUT": ["APT OUT"],
    "APT IN": ["APT IN"],
    "SVC CHG": ["SVC CHG"],
    "CGST": ["CGST 9%", "CGST"],
    "SGST": ["SGST 9%", "SGST"],
    "IGST": ["IGST 18%", "IGST"],
    "AMOUNT": ["AMOUNT"],
}


def parse(data, name, log):
    raw, _, _ = read_raw_any(data, name)

    # header used to be assumed on row 3; now found by looking for "AWB NO"
    header_row = find_header_row(raw, lambda cells: any(c.replace(".", "").strip() == "AWB NO" for c in cells))
    if header_row is None:
        raise ValueError("header row (AWB NO) not found")
    df = frame_from_header(raw, header_row)

    awb_col = find_col(df, ["AWB NO.", "AWB NO"], allow_partial=False)
    df = df[df[awb_col].notna()]
    df = df[~df[awb_col].astype(str).str.contains("Airline|Total", case=False, na=False)]

    out = pd.DataFrame(index=df.index)
    out["AWB_NO"] = df[awb_col].astype(str).str.strip()

    missing = []
    for target, cands in SOURCE.items():
        src = find_col(df, cands, allow_partial=False)
        if src is None:
            missing.append(cands[0])
            out[target] = pd.NA
        else:
            out[target] = df[src]
    if missing:
        log("warning", f"{name}: columns not found (left blank): {', '.join(missing)}")

    for col in ["PKGS", "CHR_WT", "RATE", "BASIC_FRT"] + EXTRA_COLS:
        out[col] = to_num(out[col], fill=0 if col in ADDON_PARTS else None)

    out["ADDON_CHR"] = out[ADDON_PARTS].sum(axis=1)
    out["TOTAL_FRT"] = out["BASIC_FRT"] + out["ADDON_CHR"]
    out["AWB_DATE"] = to_date(out["AWB_DATE"], dayfirst=True)

    parts = strip_ext(name).split("-")
    out["INVOICE_NO"] = "-".join(parts[:3])   # fixed: was blank for every row
    out["ORIGIN"] = parts[0].strip()
    out["LODGE_MODE"] = out["AWB_NO"].str.contains("-", regex=False).map({True: "Direct", False: "Console"})
    out["TRNSPT_MODE"] = "AIR"
    return out
