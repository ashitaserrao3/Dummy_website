"""
The ONE output format every agent produces.

Each agent parser only has to return a DataFrame with (some of) the
standard column names below plus any agent-specific charge columns.
`standardize()` then fills in everything that is calculated the same way
for all agents, and adds the check columns DUP_FLAG / DATA_ISSUE.
"""

import pandas as pd

from utils.common import airline_from_awb, get_airline, get_bill_period, get_slab, to_date, to_num


# Columns before the agent-specific charge columns
LEAD_COLS = [
    "INVOICE_NO",
    "BILL_PERIOD",
    "AGENT",
    "TRNSPT_MODE",
    "OD_PAIR",
    "ORIGIN",
    "DEST",
    "AWB_NO",
    "AWB_DATE",
    "FLIGHT_NO",
    "AIRLINE",
    "PKGS",
    "CHR_WT",
    "RATE",
    "BASIC_FRT",
]

# Columns after the agent-specific charge columns
TAIL_COLS = [
    "TOTAL_FRT",
    "ADDON_CHR",
    "ADDON_PER_KG",
    "CPKG",
    "SLAB",
    "LODGE_MODE",
    "DUP_FLAG",
    "DATA_ISSUE",
    "SOURCE_FILE",
]

STANDARD_COLS = LEAD_COLS + TAIL_COLS
NUMERIC_COLS = ["PKGS", "CHR_WT", "RATE", "BASIC_FRT", "TOTAL_FRT", "ADDON_CHR"]


def _text(s):
    return s.astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaT": pd.NA})


def standardize(df, agent, extra_cols=None):
    """
    df         : rows from one or more files of ONE agent
    agent      : value written to AGENT
    extra_cols : agent charge columns to keep (in this order) between
                 BASIC_FRT and TOTAL_FRT. Anything else is dropped.
    """
    extra_cols = [c for c in (extra_cols or []) if c not in STANDARD_COLS]
    df = df.copy()

    for col in STANDARD_COLS + extra_cols:
        if col not in df.columns:
            df[col] = pd.NA

    # ---------- types ----------
    for col in NUMERIC_COLS + extra_cols:
        df[col] = to_num(df[col])

    for col in ["INVOICE_NO", "ORIGIN", "DEST", "AWB_NO", "FLIGHT_NO", "LODGE_MODE", "SOURCE_FILE"]:
        df[col] = _text(df[col])
    df["ORIGIN"] = df["ORIGIN"].str.upper()
    df["DEST"] = df["DEST"].str.upper()

    df["AWB_DATE"] = to_date(df["AWB_DATE"])

    df["AGENT"] = agent
    df["TRNSPT_MODE"] = _text(df["TRNSPT_MODE"]).str.upper().fillna("AIR")

    # ---------- derived ----------
    air = df["TRNSPT_MODE"] != "ROAD"
    no_airline = df["AIRLINE"].isna() & air
    df.loc[no_airline, "AIRLINE"] = df.loc[no_airline, "FLIGHT_NO"].map(get_airline)

    # flight empty or unreadable -> try the AWB prefix (098 = Air India, 312 = IndiGo ...)
    unknown = air & (df["AIRLINE"].isna() | (df["AIRLINE"] == "Other"))
    from_awb = df.loc[unknown, "AWB_NO"].map(airline_from_awb)
    got = from_awb.notna()
    df.loc[from_awb[got].index, "AIRLINE"] = from_awb[got]


    df["OD_PAIR"] = (df["ORIGIN"] + "-" + df["DEST"]).where(
        df["ORIGIN"].notna() & df["DEST"].notna()
    )

    df["BILL_PERIOD"] = df["AWB_DATE"].map(get_bill_period)

    no_addon = df["ADDON_CHR"].isna()
    df.loc[no_addon, "ADDON_CHR"] = df.loc[no_addon, "TOTAL_FRT"] - df.loc[no_addon, "BASIC_FRT"]

    wt = df["CHR_WT"].where(df["CHR_WT"] > 0)
    df["CPKG"] = (df["TOTAL_FRT"] / wt).round(2)
    df["ADDON_PER_KG"] = (df["ADDON_CHR"] / wt).round(2)
    df["SLAB"] = df["CHR_WT"].map(get_slab)
    df["LODGE_MODE"] = df["LODGE_MODE"].fillna("N/A")

    # ---------- data issues ----------
    issues = pd.DataFrame(index=df.index)
    issues["d"] = df["AWB_DATE"].isna().map({True: "Missing/invalid AWB date", False: ""})
    issues["w"] = (~(df["CHR_WT"] > 0)).map({True: "Missing/zero CHR_WT", False: ""})
    issues["t"] = df["TOTAL_FRT"].isna().map({True: "Missing TOTAL_FRT", False: ""})
    issues["o"] = df["OD_PAIR"].isna().map({True: "Missing origin/dest", False: ""})
    no_al = (df["TRNSPT_MODE"] != "ROAD") & (df["AIRLINE"].isna() | (df["AIRLINE"] == "Other"))
    issues["a"] = no_al.map({True: "Airline not recognised", False: ""})

    prior = _text(df["DATA_ISSUE"]).fillna("")
    df["DATA_ISSUE"] = (
        pd.concat([prior.rename("p"), issues], axis=1)
        .apply(lambda r: "; ".join(x for x in r if x), axis=1)
        .replace("", pd.NA)
    )

    df = df[LEAD_COLS + extra_cols + TAIL_COLS]
    return flag_duplicates(df)


def flag_duplicates(df):
    """
    1. Exact repeats (same AWB + invoice + date + weight + total) are removed.
    2. Remaining repeats of the same AWB are KEPT and flagged in DUP_FLAG.
    """
    if df.empty:
        return df

    key = ["AWB_NO", "INVOICE_NO", "AWB_DATE", "CHR_WT", "TOTAL_FRT"]
    before = len(df)
    df = df.drop_duplicates(subset=key).reset_index(drop=True)
    df.attrs["exact_dups_removed"] = before - len(df)

    counts = df.groupby("AWB_NO", dropna=True)["AWB_NO"].transform("size")
    df["DUP_FLAG"] = pd.Series(pd.NA, index=df.index, dtype="string")
    rep = counts > 1
    df.loc[rep, "DUP_FLAG"] = "AWB repeated x" + counts[rep].astype(int).astype(str)
    return df


def combine(frames):
    """Stack several standardized agent outputs (Multi-Agent)."""
    frames = [f for f in frames if f is not None and not f.empty]
    if not frames:
        return pd.DataFrame(columns=STANDARD_COLS)

    extras = []
    for f in frames:
        for c in f.columns:
            if c not in STANDARD_COLS and c not in extras:
                extras.append(c)

    out = pd.concat(frames, ignore_index=True, sort=False)
    removed = sum(f.attrs.get("exact_dups_removed", 0) for f in frames)
    out = out[LEAD_COLS + extras + TAIL_COLS]
    out["DUP_FLAG"] = pd.NA
    out = flag_duplicates(out)
    out.attrs["exact_dups_removed"] = removed + out.attrs.get("exact_dups_removed", 0)
    return out
