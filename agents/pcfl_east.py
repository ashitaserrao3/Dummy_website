"""PCFL East bills (Excel). Total = GROSS column."""

from agents.pcf_common import EXTRA_COLS, parse_pcf

AGENT = "PCFL(E)"
KEY = "pcfl_east"
LABEL = "PCFL East"
DESCRIPTION = "PCFL East bills (.xlsx) · total taken from the GROSS column"
FILE_TYPES = ["xlsx", "xls"]
OUTPUT_FILE = "PCFL_East_Combined.xlsx"
EXTRA_COLS = EXTRA_COLS


def parse(data, name, log):
    return parse_pcf(data, name, log, total_header="GROSS")
