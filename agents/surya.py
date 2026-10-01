"""SURYA bills (PDF, MAWB and HAWB sections)."""

import re
from io import BytesIO

import pandas as pd
import pdfplumber

from utils.common import _one_num, digits_only, parse_date, strip_ext

AGENT = "SURYA"
KEY = "surya"
LABEL = "SURYA"
DESCRIPTION = "Surya PDF invoices · MAWB and HAWB sections · origin DEL"
FILE_TYPES = ["pdf"]
OUTPUT_FILE = "SURYA_Combined.xlsx"
EXTRA_COLS = ["OTHER_CHR", "SECTION"]

ORIGIN = "DEL"


def _num(x):
    return _one_num(x)


def _parse_line(parts):
    """
    Expected: SNo AWB Date Dest Flight Pkts Wt Rate <x> Basic Other Total ...
    Returns a dict, or None if the numbers don't line up.
    """
    if len(parts) < 12:
        return None
    date = parse_date(parts[2])
    nums = [_num(parts[i]) for i in (5, 6, 7, 9, 10, 11)]
    if pd.isna(date) or any(n is None for n in nums):
        return None
    pkts, wt, rate, basic, other, total = nums
    return {
        "AWB_NO": parts[1], "AWB_DATE": date, "DEST": parts[3], "FLIGHT_NO": parts[4],
        "PKGS": pkts, "CHR_WT": wt, "RATE": rate,
        "BASIC_FRT": basic, "OTHER_CHR": other, "TOTAL_FRT": total,
    }


def extract_rows(text, log, name):
    rows, skipped = [], 0
    section = None

    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        # section switch (MAWB rows stop when HAWB section starts and vice versa)
        if "MAWB" in s.upper():
            section = "MAWB"
            continue
        if "HAWB" in s.upper():
            section = "HAWB"
            continue
        if section is None or "TOTAL" in s.upper():
            continue

        parts = s.split()
        if len(parts) < 12 or not re.search(r"\d{6,}", parts[1] if len(parts) > 1 else ""):
            continue

        # Try the line as-is, then with a split flight joined ("6E 123" -> "6E123").
        # Accept the reading where Basic + Other = Total.
        options = [parts]
        if len(parts) >= 13:
            options.append(parts[:4] + [parts[4] + parts[5]] + parts[6:])
        readings = [r for r in (_parse_line(o) for o in options) if r]
        good = [r for r in readings if abs(r["BASIC_FRT"] + r["OTHER_CHR"] - r["TOTAL_FRT"]) <= 1]
        row = (good or readings or [None])[0]
        if row is None:
            skipped += 1
            continue
        row["SECTION"] = section
        rows.append(row)

    if skipped:
        log("warning", f"{name}: {skipped} lines looked like AWB rows but could not be read – please check the PDF")
    return rows


def parse(data, name, log):
    with pdfplumber.open(BytesIO(data)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    df = pd.DataFrame(extract_rows(text, log, name))
    if df.empty:
        return df

    df["AWB_NO"] = df["AWB_NO"].map(digits_only)
    df = df[df["AWB_NO"].notna()].copy()

    # Basic / total fall-backs (unchanged rule)
    df["BASIC_FRT"] = df["BASIC_FRT"].fillna(df["RATE"] * df["CHR_WT"])
    df["OTHER_CHR"] = df["OTHER_CHR"].fillna(0)
    df["TOTAL_FRT"] = df["TOTAL_FRT"].fillna(df["BASIC_FRT"] + df["OTHER_CHR"])

    mismatch = (df["BASIC_FRT"] + df["OTHER_CHR"] - df["TOTAL_FRT"]).abs() > 1
    df["DATA_ISSUE"] = pd.Series(pd.NA, index=df.index, dtype="string")
    df.loc[mismatch, "DATA_ISSUE"] = "Basic + Other ≠ Total (check PDF)"

    df["LODGE_MODE"] = df["AWB_NO"].str.len().eq(11).map({True: "Direct", False: "Console"})
    df["ORIGIN"] = ORIGIN
    df["INVOICE_NO"] = strip_ext(name)
    df["TRNSPT_MODE"] = "AIR"
    return df
