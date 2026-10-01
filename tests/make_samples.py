"""
Builds small FAKE bills in each agent's layout (tests/samples/).
They only mimic the column layouts the parsers expect – replace/add real
bills here to test against your actual formats.
"""

from datetime import datetime
from pathlib import Path

import openpyxl
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "samples"


def xlsx(path, sheets):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for title, rows, merges in sheets:
        ws = wb.create_sheet(title)
        for r in rows:
            ws.append(r)
        for m in merges:
            ws.merge_cells(m)
    wb.save(OUT / path)


def build():
    OUT.mkdir(exist_ok=True)

    # ---------------- INDEX ----------------
    h = ["Sr", "Awb No", "Awb Date", "Origin", "Dest.", "Flight", "Pkts", "Charge Wt.", "Rate", "Basic Freight",
         "A.Do", "xray", "Tsp in", "Tsp out", "addntsp", "Addntsp Destination", "Unit", "Deunit", "Surch.",
         "Misc Chg.", "Other Dc", "Service", "Handling", "Total"]
    z = [0] * 12
    xlsx("INDEX_INV-001.xlsx", [("Sheet1", [
        ["INDEX LOGISTICS"], ["Bill for Aug"], h,
        [1, "09812345671", datetime(2026, 8, 3), "BOM", "DEL", "AI 805", 2, 40, 50, 2000, 50] + z[:11] + [None, 2050],  # blank Handling -> Console
        [2, "09812345672", datetime(2026, 8, 20), "BOM", "BLR", "6E 201", 5, 120, 45, 5400, 50, 100] + z[:10] + [0, 5550],
        [3, "09812345673", None, "BOM", "MAA", "SG 11", 1, 10, 60, 600, 50] + z[:12] + [650],
        [None, "Total", None, None, None, None, 8, 170, None, 8000] + [None] * 13 + [8250],
    ], ["A1:F1"])])
    xlsx("INDEX_INV-002.xlsx", [("Sheet1", [
        ["INDEX LOGISTICS"], h,
        [1, "09812345672", datetime(2026, 8, 20), "BOM", "BLR", "6E 201", 5, 120, 46, 5520, 50, 100] + z[:10] + [0, 5670],
    ], [])])

    # ---------------- POBC ----------------
    ph = ["No.", "Waybill", "AWBC", "Date", "Route", "Dest", "Srv", "Pcs", "Bags", "Wt", "Rate", "Frt",
          "OTH", "HNDC", "DUNT", "TSPI", "TSPO", "UNIT", "XRAY", "SRCH", "Revenue"]
    xlsx("POBC_Aug.xlsx", [
        ("Bill Summary", [["summary"]], []),
        ("S-BOM-01", [
            ["POBC"], ph,
            [1, "AI-09822222221", 50, datetime(2026, 8, 2), "AI 101", "PAF-DEL", "ACG", 2, 1, 30, 40, 1200, 0, 0, 0, 0, 0, 0, 0, 0, 1250],
            [2, "09822222222", 0, None, "6E 55", "DEL", "ACG", 3, 1, 60, 40, 2400, 0, 150, 0, 0, 0, 0, 80, 0, 2630],
            [3, "09822222223", 50, datetime(2026, 8, 18), "6E 55", "BLR", "ACG", 1, 1, 20, 40, 800, None, None, None, None, None, None, None, None, 850],
            [4, "09822222224", 0, datetime(2026, 8, 18), "ROAD", "PNQ", "RDS", 1, 1, 20, 10, 200, 0, 0, 0, 0, 0, 0, 0, 0, 200],
            [None, "Total", None, None, None, None, None, 7, None, 130, None, 4600, None, None, None, None, None, None, None, None, 4930],
        ], []),
    ])

    # ---------------- PCF South / PCFL East ----------------
    def pcf(total_name):
        hh = ["S.No", "AWB NO", "DATE", "DEST", "FLIGHT", "PKT", "WGT", "RATE", "BASIC", "AWBDO", "FSC", "OCDC",
              "TSP", "SSP", "SSP AMT", "DIS", "DISC", "CGST", "SGST", "IGST", total_name, "AMOUNT"]
        return [
            ["PCF"], ["Invoice"], hh,
            [1, "098-33333331", datetime(2026, 8, 5), "DEL", "AI-440", 2, 50, 40, 2000, 50, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2050, 2050],
            [2, "098-33333332", datetime(2026, 8, 25), "CCU", "6E-12", 4, 150, 35, 5250, 50, 200, 100, 0, 0, 0, 5, 262, 0, 0, 0, 5338, 5338],
            [3, "098-33333333", datetime(2026, 8, 25), "HYD", "QP 1", 1, "M", 0, 800, 50, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 850, 850],
            [None, "TOTAL", None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 8238, 8238],
        ]
    xlsx("MAA-PCF-0801.xlsx", [("Sheet1", pcf("NET"), [])])
    xlsx("CCU-PCFL-0801.xlsx", [("Sheet1", pcf("GROSS"), [])])

    # ---------------- BHAGWATI ----------------
    xlsx("BHAGWATI_Aug.xlsx", [("Sheet1", [
        ["BHAGWATI CARGO"], ["HAWB NO", "DATE", "PEC.", "DEST", "FLT NO.", "CHG WT", "RATE", "FREIGHT", "HAWB", "AMOUNT"],
        ["B1001", "05/08/2026", 2, "DEL", "INDIGO 6E 101", 55, 40, 2200, 50, 2250],
        ["B1002", "21/08/2026", 3, "BLR", "AIR INDIA", 280, 38, 10640, 500, 11140],
        ["B1003", None, 1, "CCU", "AKASA", 20, 45, 900, 70, 970],
        [None, None, None, None, None, 355, None, 13740, None, 14360],
    ], [])])

    # ---------------- FDC ----------------
    fh = ["S.NO", "CON.NO.", "DATE", "DEST", "QTY", "WEIGHT", "RATE", "ODA CHARGES"]
    xlsx("FDC_Aug.xlsx", [
        ("1st Half", [["FDC Invoice No: 11/2026-27 Dt: 01.08.2026"], ["Consignor: ABC Contact No 999"], fh,
                      [1, "FDC000111", "02.08.2026", "VTZ", 2, 30, 12, 0]], []),
        ("2nd Half", [["FDC Invoice No: 12/2026-27 Dt: 16.08.2026"], ["Consignor: ABC Contact No 999"], fh,
                      [1, "FDC000211", "17.08.2026", "VTZ", 2, 30, 12, 0],
                      [2, "FDC000212", "18.08.2026", "BZA", 1, 50, 10, 150]], []),
    ])

    # ---------------- EDS ----------------
    eh = ["AWB NO.", "DATE", "FLIGHT NO.", "DSTN", "PCS", "CWGT KGS.", "RATE", "FREIGHT CHS", "AWB DO",
          "A/L CHG", "APT OUT", "APT IN", "SVC CHG", "CGST 9%", "SGST 9%", "IGST 18%", "AMOUNT"]
    xlsx("BOM-EDS-0042-Aug26.xlsx", [("Sheet1", [
        ["EDS"], ["Bill"], eh,
        ["098-44444441", "04/08/2026", "AI 660", "DEL", 2, 60, 30, 1800, 50, 20, 30, 0, 10, 0, 0, 342, 2252],
        ["44444442", "19/08/2026", "6E 330", "GOI", 1, 12, 55, 660, 50, 0, 0, 0, 0, 0, 0, 128, 838],
        ["Airline total", None, None, None, None, 72, None, 2460, None, None, None, None, None, None, None, None, 3090],
    ], [])])

    # ---------------- SURYA (PDF) ----------------
    c = canvas.Canvas(str(OUT / "SURYA_Aug.pdf"), pagesize=landscape(A4))
    y = 560
    for line in [
        "SURYA AIR CARGO - Invoice SUR/26/088",
        "MAWB Details",
        "SNo AwbNo Date Dest Flight Pkts ChWt Rate Disc Basic Other Total",
        "1 09855555551 03/08/2026 DEL AI805 2 45 40 0 1800 100 1900",
        "2 09855555552 17/08/2026 BLR 6E 203 3 110 35 0 3850 150 4000",
        "Total 5 155 5650 250 5900",
        "HAWB Details",
        "1 H5555553 20/08/2026 CCU SG15 1 20 50 0 1000 50 1050",
        "2 H5555554 21/08/2026 MAA QP33 1 20 50 0 1000 50 1090",
    ]:
        c.drawString(30, y, line)
        y -= 18
    c.save()


if __name__ == "__main__":
    build()
    print("samples written to", OUT)
