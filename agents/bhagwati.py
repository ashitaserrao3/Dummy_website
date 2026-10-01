"""BHAGWATI bills (Excel). Origin is always PNQ."""

import pandas as pd

from utils.common import find_header_row, frame_from_header, strip_ext, to_date, to_num
from utils.excel_utils import read_raw_any

AGENT = "BHAGWATI"
KEY = "bhagwati"
LABEL = "BHAGWATI"
DESCRIPTION = "Bhagwati bills (.xlsx) · origin PNQ · HAWB charge 50 = Console, 500 = Direct"
FILE_TYPES = ["xlsx", "xls"]
OUTPUT_FILE = "BHAGWATI_Combined.xlsx"
EXTRA_COLS = ["HAWB_CHR"]

ORIGIN = "PNQ"

RENAME = {
    "HAWB NO": "AWB_NO",
    "DATE": "AWB_DATE",
    "PEC.": "PKGS",
    "CHG WT": "CHR_WT",
    "DEST": "DEST",
    "FLT NO.": "FLIGHT_NO",
    "RATE": "RATE",
    "FREIGHT": "BASIC_FRT",
    "AMOUNT": "TOTAL_FRT",
    "HAWB": "HAWB_CHR",
}


def get_mode(hawb_charge):
    """HAWB charge 50 = Console, 500 = Direct, anything else = Other."""
    if pd.isna(hawb_charge):
        return None
    r = round(float(hawb_charge), 0)
    return "Console" if r == 50 else "Direct" if r == 500 else "Other"


def parse(data, name, log):
    raw, _, _ = read_raw_any(data, name)
    header_row = find_header_row(raw, lambda cells: "HAWB NO" in cells and "CHG WT" in cells)
    if header_row is None:
        raise ValueError("table header (HAWB NO + CHG WT) not found")

    df = frame_from_header(raw, header_row)
    df.columns = [c.strip().upper() for c in df.columns]
    df = df.rename(columns=RENAME)
    df = df.loc[:, ~df.columns.duplicated()]

    awb = df["AWB_NO"].astype(str).str.strip()
    df = df[df["AWB_NO"].notna() & awb.str.contains(r"\d", na=False)].copy()

    for col in ["PKGS", "CHR_WT", "RATE", "BASIC_FRT", "HAWB_CHR", "TOTAL_FRT"]:
        if col in df.columns:
            df[col] = to_num(df[col])

    if "TOTAL_FRT" not in df.columns and {"BASIC_FRT", "HAWB_CHR"} <= set(df.columns):
        df["TOTAL_FRT"] = df["BASIC_FRT"] + df["HAWB_CHR"]

    if "AWB_DATE" in df.columns:
        df["AWB_DATE"] = to_date(df["AWB_DATE"], dayfirst=True)

    df["LODGE_MODE"] = df["HAWB_CHR"].map(get_mode) if "HAWB_CHR" in df.columns else None
    df["INVOICE_NO"] = strip_ext(name)
    df["ORIGIN"] = ORIGIN
    df["TRNSPT_MODE"] = "AIR"
    return df
