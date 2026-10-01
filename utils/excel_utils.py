from io import BytesIO

import openpyxl
import pandas as pd


def read_sheet_unmerged(data, sheet=None, fill_merged=True):
    """
    Load one sheet with merged cells split.
    fill_merged=True copies the merged value into every cell of the range
    (so a merged 'Date' or header shows on each row it covers).
    Returns (raw DataFrame with header=None, sheet name, workbook).
    """
    wb = openpyxl.load_workbook(BytesIO(data), data_only=True)
    ws = wb[sheet] if sheet else wb.active
    unmerge(ws, fill_merged)
    raw = pd.DataFrame(list(ws.values))
    return raw, ws.title, wb


def unmerge(ws, fill_merged=True):
    for rng in list(ws.merged_cells.ranges):
        value = ws.cell(row=rng.min_row, column=rng.min_col).value
        ws.unmerge_cells(str(rng))
        # Copy text/dates into every cell of the merge (e.g. one date merged over
        # several AWB rows). Numbers are NOT copied, so amounts are never doubled.
        if fill_merged and not isinstance(value, (int, float)):
            for r in range(rng.min_row, rng.max_row + 1):
                for c in range(rng.min_col, rng.max_col + 1):
                    ws.cell(row=r, column=c).value = value


def sheet_to_raw(ws):
    return pd.DataFrame(list(ws.values))


def read_raw_any(data, name):
    """For .xls (old format) openpyxl can't open; fall back to pandas."""
    if str(name).lower().endswith(".xls"):
        return pd.read_excel(BytesIO(data), header=None), None, None
    return read_sheet_unmerged(data)


def formula_cells_without_values(data, name):
    """
    Cells that hold a formula but no saved result. Files exported by some
    systems are never opened/saved in Excel, so these read as BLANK.
    Fix for the user: open the file in Excel, Save, upload again.
    """
    if not str(name).lower().endswith((".xlsx", ".xlsm")):
        return 0
    try:
        f_wb = openpyxl.load_workbook(BytesIO(data), data_only=False, read_only=True)
        v_wb = openpyxl.load_workbook(BytesIO(data), data_only=True, read_only=True)
        missing = 0
        for ws_f, ws_v in zip(f_wb.worksheets, v_wb.worksheets):
            for row_f, row_v in zip(ws_f.iter_rows(values_only=True), ws_v.iter_rows(values_only=True)):
                for a, b in zip(row_f, row_v):
                    if isinstance(a, str) and a.startswith("=") and b is None:
                        missing += 1
        return missing
    except Exception:
        return 0
