"""
Shared helpers used by every agent.

Keep ONE copy of each business rule here so agents can never drift apart
(slabs, airline codes, bill period, column matching, number cleaning).
"""

import re
from datetime import date, datetime

import pandas as pd


# =====================================================
# SLAB  (single source of truth)
# =====================================================

SLAB_ORDER = [
    "Less than 45Kg",
    "45Kg +",
    "100Kg +",
    "250Kg +",
    "300Kg +",
    "500Kg +",
    "1000Kg +",
]


def get_slab(wt):
    try:
        wt = float(wt)
    except (TypeError, ValueError):
        return None

    if pd.isna(wt) or wt <= 0:
        return None
    if wt < 45:
        return "Less than 45Kg"
    if wt < 100:
        return "45Kg +"
    if wt < 250:
        return "100Kg +"
    if wt < 300:
        return "250Kg +"
    if wt < 500:
        return "300Kg +"
    if wt < 1000:
        return "500Kg +"
    return "1000Kg +"


# =====================================================
# AIRLINE  (single source of truth)
# =====================================================

AIRLINE_CODES = {
    "AI": "AirIndia",
    "IX": "AirIndia",      # Air India Express
    "I5": "AirIndia",      # ex-AirAsia India, now Air India Express
    "6E": "Indigo",
    "SG": "SpiceJet",
    "S5": "StarAir",
    "QP": "Akasa",
    "9I": "AllianceAir",
}

# Some bills write the airline name instead of a flight number
AIRLINE_NAMES = [
    ("INDIGO", "Indigo"),
    ("AIR INDIA", "AirIndia"),
    ("AIRINDIA", "AirIndia"),
    ("AIRIN", "AirIndia"),
    ("SPICE", "SpiceJet"),
    ("AKASA", "Akasa"),
    ("STAR AIR", "StarAir"),
    ("ALLIANCE", "AllianceAir"),
]

# 3-digit air waybill prefix -> airline (used only when the flight cell is empty
# or unreadable, and only for 11-digit airline AWBs, not agent HAWB numbers)
AWB_PREFIX = {
    "098": "AirIndia",
    "236": "AirIndia",     # Air India Express
    "312": "Indigo",
    "775": "SpiceJet",
    "516": "Akasa",
}

_CODE_IN_TEXT = re.compile(
    r"(?<![A-Z0-9])(" + "|".join(AIRLINE_CODES) + r")\s*[-/.]?\s*\d{1,4}"
)


def get_airline(flight):
    """
    Airline from the flight cell. Handles 'AI 805', 'AI-805/12', '6E/201',
    'ai805del', 'IndiGo 6E 101', 'AIR INDIA'. Returns None when the cell is
    empty and 'Other' when there is text but no known airline in it.
    """
    if flight is None or (not isinstance(flight, str) and pd.isna(flight)):
        return None

    text = str(flight).strip().upper()
    if not text or text in ("NAN", "NONE", "-"):
        return None

    for key, name in AIRLINE_NAMES:
        if key in text:
            return name

    m = _CODE_IN_TEXT.search(text)
    if m:
        return AIRLINE_CODES[m.group(1)]

    code = re.sub(r"[^A-Z0-9]", "", text)[:2]
    return AIRLINE_CODES.get(code, "Other")


def airline_from_awb(awb):
    """Airline from the AWB prefix, e.g. 098-12345675 -> AirIndia. 11-digit AWBs only."""
    if awb is None or (not isinstance(awb, str) and pd.isna(awb)):
        return None
    d = re.sub(r"\D", "", str(awb))
    if len(d) != 11:
        return None
    return AWB_PREFIX.get(d[:3])


# =====================================================
# BILL PERIOD
# =====================================================

def get_bill_period(date):
    """FFN = 1st-15th, SFN = 16th-end. Missing date -> None (never guessed)."""
    if date is None or pd.isna(date):
        return None
    try:
        return "FFN" if pd.Timestamp(date).day <= 15 else "SFN"
    except (TypeError, ValueError):
        return None


# =====================================================
# CLEANING
# =====================================================

_NUM_JUNK = re.compile(r"(₹|RS\.?|INR|/-|,|\s)", re.I)


def _one_num(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return None if pd.isna(v) else float(v)
    t = _NUM_JUNK.sub("", str(v)).strip()
    if t in ("", "-", "--", "NA", "N/A", "nan", "None"):
        return None
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    try:
        x = float(t)
    except ValueError:
        return None
    return -x if neg else x


def to_num(series, fill=None):
    """Numbers from messy cells: '1,250.00', '₹ 500', 'Rs.300', '(100)', ' 75 '."""
    if series is None:
        return None
    if not isinstance(series, pd.Series):
        return series
    if pd.api.types.is_numeric_dtype(series):
        out = series.astype(float)
    else:
        uniq = {v: _one_num(v) for v in series.dropna().unique()}
        out = pd.to_numeric(series.map(uniq), errors="coerce")
    return out.fillna(fill) if fill is not None else out


_DATE_FORMATS = [
    "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%y", "%d-%m-%y",
    "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %b %y", "%d/%b/%Y", "%d/%b/%y", "%d-%B-%Y", "%d %B %Y",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d.%m.%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S",
]


def parse_date(v):
    """One cell -> Timestamp (day-first, Indian style) or NaT. Never guesses month-first."""
    if v is None:
        return pd.NaT
    if isinstance(v, (pd.Timestamp, datetime, date)):
        ts = pd.Timestamp(v)
    elif isinstance(v, (int, float)):
        if pd.isna(v) or not (20000 <= v <= 80000):   # Excel serial date numbers
            return pd.NaT
        ts = pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(v))
    else:
        t = re.sub(r"\s+", " ", str(v)).strip()
        if not t or t.lower() in ("nan", "nat", "none", "-"):
            return pd.NaT
        ts = pd.NaT
        if re.match(r"^\d{4}-\d{1,2}-\d{1,2}", t):           # 2026-08-07 (year first)
            ts = pd.to_datetime(t[:10], format="%Y-%m-%d", errors="coerce")
        elif re.fullmatch(r"\d{5}(\.0+)?", t):                 # serial number stored as text
            return parse_date(float(t))
        else:
            for f in _DATE_FORMATS:
                try:
                    ts = pd.Timestamp(datetime.strptime(t.title() if "%b" in f or "%B" in f else t, f))
                    break
                except ValueError:
                    continue
            if pd.isna(ts):
                ts = pd.to_datetime(t, dayfirst=True, errors="coerce")
    if pd.isna(ts) or not (2000 <= ts.year <= 2100):
        return pd.NaT
    return ts.normalize()


def to_date(series, dayfirst=True, fmt=None):
    """Column of mixed dates (real dates, text in any common format, Excel serials) -> datetime."""
    if series is None:
        return None
    uniq = {v: parse_date(v) for v in series.dropna().unique()} if len(series) else {}
    return pd.to_datetime(series.map(uniq), errors="coerce")


def digits_only(val):
    if val is None or (not isinstance(val, str) and pd.isna(val)):
        return None
    d = re.sub(r"\D", "", str(val))
    return d or None


def norm(text):
    """Header normaliser: upper-case, letters/digits only."""
    return re.sub(r"[^A-Z0-9%]", "", str(text).upper())


def find_col(df, candidates, allow_partial=True, exclude=()):
    """
    Find a column by name.
    1st pass: exact match (ignoring case/spaces/punctuation) on ANY candidate.
    2nd pass (optional): candidate contained in the header.
    """
    if isinstance(candidates, str):
        candidates = [candidates]
    bad = [norm(e) for e in exclude]
    cols = [c for c in df.columns if not any(b and b in norm(c) for b in bad)]
    normed = {c: norm(c) for c in cols}

    for cand in candidates:
        n = norm(cand)
        for c in cols:
            if normed[c] == n:
                return c

    if allow_partial:
        for cand in candidates:
            n = norm(cand)
            for c in cols:
                if n and n in normed[c]:
                    return c
    return None


def clean_headers(values):
    """Strip/flatten header text and make duplicates unique (RATE, RATE_1...)."""
    seen = {}
    out = []
    for h in values:
        h = "" if h is None or (not isinstance(h, str) and pd.isna(h)) else str(h)
        h = re.sub(r"\s+", " ", h.replace("\n", " ")).strip() or "col"
        if h in seen:
            seen[h] += 1
            out.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            out.append(h)
    return out


def find_header_row(df_raw, predicate, max_rows=60):
    """First row (within max_rows) whose upper-cased cell texts satisfy predicate(list_of_cells)."""
    for idx in range(min(len(df_raw), max_rows)):
        cells = [
            str(x).strip().upper()
            for x in df_raw.iloc[idx].tolist()
            if x is not None and not (not isinstance(x, str) and pd.isna(x))
        ]
        if cells and predicate(cells):
            return idx
    return None


def frame_from_header(df_raw, header_row):
    """Build a DataFrame using df_raw row `header_row` as headers."""
    headers = clean_headers(df_raw.iloc[header_row].tolist())
    df = pd.DataFrame(df_raw.values[header_row + 1:], columns=headers)
    return df.dropna(how="all").reset_index(drop=True)


def strip_ext(name):
    return re.sub(r"\.(xlsx|xlsm|xls|pdf|csv)$", "", str(name), flags=re.I)
