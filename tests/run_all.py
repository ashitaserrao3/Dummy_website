"""Run every agent parser on tests/samples and print the standardized output."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agents import AGENT_MODULES  # noqa: E402
from utils.page import process_agent_files  # noqa: E402

SAMPLES = Path(__file__).parent / "samples"
PREFIX = {"index": "INDEX", "pobc": "POBC", "pcf_south": "MAA-PCF", "pcfl_east": "CCU-PCFL",
          "surya": "SURYA", "bhagwati": "BHAGWATI", "fdc": "FDC", "eds": "BOM-EDS"}


class Upload:
    def __init__(self, p):
        self.name, self._b = p.name, p.read_bytes()

    def getvalue(self):
        return self._b


def run(mod):
    files = [Upload(p) for p in sorted(SAMPLES.glob(PREFIX[mod.KEY] + "*"))]
    logs = []
    df = process_agent_files(mod, files, lambda l, m: logs.append((l, m)))
    return df, logs


if __name__ == "__main__":
    pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_colwidth", 30)
    show = ["INVOICE_NO", "BILL_PERIOD", "OD_PAIR", "AWB_NO", "AWB_DATE", "AIRLINE", "CHR_WT",
            "BASIC_FRT", "TOTAL_FRT", "CPKG", "SLAB", "LODGE_MODE", "DUP_FLAG", "DATA_ISSUE"]
    for mod in AGENT_MODULES:
        df, logs = run(mod)
        print(f"\n===== {mod.AGENT}  rows={len(df)}  exact_dups_removed={df.attrs.get('exact_dups_removed')}")
        for l in logs:
            print("  log:", l)
        print(df[show].to_string())
