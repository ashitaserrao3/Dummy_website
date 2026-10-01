from io import BytesIO

import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill("solid", start_color="1F4E79", end_color="1F4E79")
HEADER_FONT = Font(color="FFFFFF", bold=True)
KEY_FILL = PatternFill("solid", start_color="FFD6D6", end_color="FFD6D6")     # CHR_WT / TOTAL_FRT / CPKG
FLAG_FILL = PatternFill("solid", start_color="FFF2CC", end_color="FFF2CC")    # DUP_FLAG / DATA_ISSUE

KEY_COLS = ["CHR_WT", "TOTAL_FRT", "CPKG"]
FLAG_COLS = ["DUP_FLAG", "DATA_ISSUE"]
MONEY_COLS = ["RATE", "BASIC_FRT", "TOTAL_FRT", "ADDON_CHR", "ADDON_PER_KG", "CPKG"]


def _write_sheet(writer, df, sheet_name):
    df.to_excel(writer, index=False, sheet_name=sheet_name)
    ws = writer.sheets[sheet_name]
    n = len(df)

    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT

    ws.freeze_panes = "A2"
    if n:
        ws.auto_filter.ref = ws.dimensions

    for idx, col in enumerate(df.columns, start=1):
        letter = get_column_letter(idx)

        # width from header + a sample of values (fast on big files)
        lengths = df[col].head(500).dropna().astype(str).str.len()
        sample = int(lengths.max()) if len(lengths) else 0
        ws.column_dimensions[letter].width = min(max(len(str(col)), sample) + 2, 40)

        if col == "AWB_DATE":
            for r in range(2, n + 2):
                ws.cell(row=r, column=idx).number_format = "DD-MMM-YYYY"
        elif col in MONEY_COLS:
            for r in range(2, n + 2):
                ws.cell(row=r, column=idx).number_format = "#,##0.00"

        if col in KEY_COLS:
            for r in range(2, n + 2):
                ws.cell(row=r, column=idx).fill = KEY_FILL
        elif col in FLAG_COLS:
            values = df[col].tolist()
            for r, v in enumerate(values, start=2):
                if v is not None and not pd.isna(v):
                    ws.cell(row=r, column=idx).fill = FLAG_FILL
    return ws


def _clean_for_excel(df):
    out = df.copy()
    for c in out.columns:
        if str(out[c].dtype) == "string":
            out[c] = out[c].astype(object).where(out[c].notna(), None)
    return out


def export_excel(df, sheet_name="Data"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _write_sheet(writer, _clean_for_excel(df), sheet_name[:31])
    output.seek(0)
    return output


def export_multi(df, summary_by="AGENT"):
    """
    Multi-Agent workbook:
      Summary  - Excel formulas (COUNTIFS/SUMIFS) over the All_Data sheet,
                 so numbers recalculate if rows are edited or filtered out.
      All_Data - every row
      <AGENT>  - one sheet per agent
    """
    data = _clean_for_excel(df)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # placeholder so Summary is the first tab
        pd.DataFrame().to_excel(writer, sheet_name="Summary", index=False)
        _write_sheet(writer, data, "All_Data")

        for agent, part in data.groupby("AGENT", sort=True):
            _write_sheet(writer, part, str(agent).replace("/", "-")[:31])

        ws = writer.sheets["Summary"]
        cols = {c: get_column_letter(i + 1) for i, c in enumerate(data.columns)}
        last = len(data) + 1

        def rng(col):
            return f"All_Data!${cols[col]}$2:${cols[col]}${last}"

        headers = ["AGENT", "AWBs", "CHR_WT", "TOTAL_FRT", "CPKG", "Rows with DATA_ISSUE", "Rows with DUP_FLAG"]
        for i, h in enumerate(headers, start=1):
            c = ws.cell(row=1, column=i, value=h)
            c.fill = HEADER_FILL
            c.font = HEADER_FONT

        agents = sorted(data["AGENT"].dropna().unique().tolist())
        for r, agent in enumerate(agents, start=2):
            ws.cell(row=r, column=1, value=agent)
            ws.cell(row=r, column=2, value=f'=COUNTIFS({rng("AGENT")},$A{r})')
            ws.cell(row=r, column=3, value=f'=SUMIFS({rng("CHR_WT")},{rng("AGENT")},$A{r})')
            ws.cell(row=r, column=4, value=f'=SUMIFS({rng("TOTAL_FRT")},{rng("AGENT")},$A{r})')
            ws.cell(row=r, column=5, value=f'=IFERROR(D{r}/C{r},0)')
            ws.cell(row=r, column=6, value=f'=COUNTIFS({rng("AGENT")},$A{r},{rng("DATA_ISSUE")},"<>")')
            ws.cell(row=r, column=7, value=f'=COUNTIFS({rng("AGENT")},$A{r},{rng("DUP_FLAG")},"<>")')

        t = len(agents) + 2
        ws.cell(row=t, column=1, value="TOTAL").font = Font(bold=True)
        for col in "BCDFG":
            ws[f"{col}{t}"] = f"=SUM({col}2:{col}{t - 1})"
            ws[f"{col}{t}"].font = Font(bold=True)
        ws[f"E{t}"] = f"=IFERROR(D{t}/C{t},0)"
        ws[f"E{t}"].font = Font(bold=True)

        for r in range(2, t + 1):
            for col in "CDE":
                ws[f"{col}{r}"].number_format = "#,##0.00"
        for col, w in zip("ABCDEFG", [14, 10, 14, 16, 10, 20, 18]):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = "A2"

    output.seek(0)
    return output
