import pandas as pd
import streamlit as st

from utils.ui import html_table, section

SLAB_GROUPS = {
    "Less than 45Kg": ["Less than 45Kg"],
    "45Kg +": ["45Kg +"],
    "100Kg & above": ["100Kg +", "250Kg +", "300Kg +", "500Kg +", "1000Kg +"],
}


def _cpkg(frame):
    wt = frame["CHR_WT"].sum()
    return frame["TOTAL_FRT"].sum() / wt if wt else 0


def _options(df, col):
    return ["All"] + sorted(df[col].dropna().astype(str).unique().tolist())


def _n(x, dp=0):
    return f"{x:,.{dp}f}"


def apply_filters(df, key):
    filters = ["ORIGIN", "DEST", "BILL_PERIOD"]
    if df["AGENT"].nunique() > 1:
        filters = ["AGENT"] + filters
    labels = {"AGENT": "Agent", "ORIGIN": "Origin", "DEST": "Destination", "BILL_PERIOD": "Bill period"}

    cols = st.columns(len(filters))
    filtered = df
    for col_ui, col in zip(cols, filters):
        with col_ui:
            choice = st.selectbox(labels[col], _options(df, col), key=f"{key}_{col}")
        if choice != "All":
            filtered = filtered[filtered[col].astype(str) == choice]
    return filtered


def show_dashboard(df, key="dash"):
    """Filters + KPIs + slab matrix + lane summary. Returns the filtered rows."""
    filtered = apply_filters(df, key)

    # ---------------- KPIs ----------------
    k = st.columns(4)
    k[0].metric("AWBs", _n(len(filtered)))
    k[1].metric("Total freight (₹)", _n(filtered["TOTAL_FRT"].sum()))
    k[2].metric("Chargeable weight (kg)", _n(filtered["CHR_WT"].sum(), 1))
    k[3].metric("CPKG (₹/kg)", _n(_cpkg(filtered), 2))

    # ---------------- SLAB × MODE ----------------
    section("Slab-wise · Direct vs Console")
    mode = filtered["LODGE_MODE"].astype(str).str.upper()
    rows = []
    for title, slabs in SLAB_GROUPS.items():
        in_slab = filtered["SLAB"].isin(slabs)
        cells = [f"<b>{title}</b>"]
        for name in ("DIRECT", "CONSOLE"):
            part = filtered[in_slab & (mode == name)]
            cells += [_n(len(part)), _n(_cpkg(part), 2) if len(part) else '<span class="acl-muted">–</span>']
        rows.append(cells)

    tot = ["Total"]
    for name in ("DIRECT", "CONSOLE"):
        part = filtered[mode == name]
        tot += [_n(len(part)), _n(_cpkg(part), 2) if len(part) else "–"]

    html_table(
        ["Slab", "Direct AWBs", "Direct CPKG", "Console AWBs", "Console CPKG"],
        rows, total_row=tot, group_starts=(1, 3),
    )

    other = filtered[~mode.isin(["DIRECT", "CONSOLE"])]
    notes = []
    if len(other):
        split = other["LODGE_MODE"].value_counts().to_dict()
        notes.append(f"{len(other):,} rows not Direct/Console ({', '.join(f'{k}: {v}' for k, v in split.items())})")
    no_slab = int(filtered["SLAB"].isna().sum())
    if no_slab:
        notes.append(f"{no_slab:,} rows without weight")
    if notes:
        st.caption("Not in the table above: " + " · ".join(notes))

    # ---------------- LANES ----------------
    section("Lane summary")
    lanes = (
        filtered.dropna(subset=["OD_PAIR"])
        .groupby("OD_PAIR")
        .agg(AWBs=("AWB_NO", "size"), CHR_WT=("CHR_WT", "sum"), TOTAL_FRT=("TOTAL_FRT", "sum"))
        .sort_values("TOTAL_FRT", ascending=False)
        .reset_index()
    )
    lanes["CPKG"] = lanes["TOTAL_FRT"] / lanes["CHR_WT"].where(lanes["CHR_WT"] > 0)
    st.dataframe(
        lanes,
        hide_index=True,
        width="stretch",
        height=min(38 + 35 * len(lanes), 360),
        column_config={
            "OD_PAIR": st.column_config.TextColumn("Lane (OD)"),
            "AWBs": st.column_config.NumberColumn(format="localized"),
            "CHR_WT": st.column_config.NumberColumn("Chg. wt (kg)", format="localized"),
            "TOTAL_FRT": st.column_config.NumberColumn("Freight (₹)", format="localized"),
            "CPKG": st.column_config.NumberColumn("CPKG", format="%.2f"),
        },
    )
    return filtered
