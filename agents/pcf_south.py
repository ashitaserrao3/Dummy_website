"""PCF South bills (Excel). Total = NET column."""

from agents.pcf_common import EXTRA_COLS, parse_pcf

AGENT = "PCF(S)"
KEY = "pcf_south"
LABEL = "PCF South"
DESCRIPTION = "PCF South bills (.xlsx) · total taken from the NET column"
FILE_TYPES = ["xlsx", "xls"]
OUTPUT_FILE = "PCF_South_Combined.xlsx"
EXTRA_COLS = EXTRA_COLS


def parse(data, name, log):
    return parse_pcf(data, name, log, total_header="NET")
