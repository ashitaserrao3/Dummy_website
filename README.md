# Dummy_website – ACL Dummy

Just a dummy acl website to test and track the updates and push new changes/requirements in original repo.


Streamlit app that reads co-loader / agent bills (Excel & PDF), converts them
to ONE standard format, shows a CPKG dashboard and exports Excel.

## Deploy (Streamlit Community Cloud)
1. Push this repo to GitHub.
2. App → Settings → **Secrets** → paste the contents of your private `secrets.toml`
   (layout: see `secrets.toml.example`). Logins are **not** stored in the repo.
3. New/changed password: `python generate_password.py`, paste the hash into Secrets.

Local run: copy your secrets to `.streamlit/secrets.toml` (git-ignored), then `streamlit run app.py`.

## Activity log (Google Sheet)
Records who logs in, failed logins, logouts, how long each visit lasted, which agent
was opened, which files were processed and what was downloaded.

Sheet tabs (created automatically): **Sessions** (one row per visit; `DURATION_MIN` and
`STATUS` are formulas), **Events** (every action), **Summary** (visits / minutes / last login per user).
While someone has the app open, `LAST_SEEN` updates every minute, so a visit that ends by closing
the tab still gets a duration (accurate to about 1 minute).

One-time setup (desktop, ~10 min):
1. console.cloud.google.com → create a project → *APIs & Services → Library* → enable **Google Sheets API**.
2. *IAM & Admin → Service Accounts* → Create (e.g. `acl-logger`) → *Keys → Add key → JSON* (downloads a .json).
3. Create a blank Google Sheet → *File → Settings → Time zone = (GMT+05:30) India* →
   **Share** it with the service account's `client_email` as **Editor**.
4. Streamlit Cloud → app → *Settings → Secrets*: add `[activity_log] sheet_id` (from the sheet URL) and
   `[gcp_service_account]` with the fields from the .json (layout in `secrets.toml.example`). Save → app restarts.
5. Log in once; the Sessions / Events / Summary tabs appear in the sheet.

## Structure
| Path | What it does |
|---|---|
| `app.py` | Login + sidebar menu |
| `agents/<agent>.py` | One parser per agent: reads a bill → rows |
| `agents/pcf_common.py` | Shared parser for PCF South (NET) and PCFL East (GROSS) |
| `agents/multi_agent.py` | Process several agents together |
| `utils/schema.py` | The standard output format, CPKG/slab/bill-period, DUP_FLAG, DATA_ISSUE |
| `utils/common.py` | Single copy of slab, airline, bill-period and cleaning rules |
| `utils/page.py` | Shared upload → process → dashboard → download page |
| `utils/activity_log.py` | Google Sheet activity log (logins, duration, events) |
| `utils/exporter.py` | Excel export (single agent / multi-agent with formula Summary) |

## Output columns (all agents)
`INVOICE_NO, BILL_PERIOD, AGENT, TRNSPT_MODE, OD_PAIR, ORIGIN, DEST, AWB_NO, AWB_DATE,
FLIGHT_NO, AIRLINE, PKGS, CHR_WT, RATE, BASIC_FRT, <agent charge columns>, TOTAL_FRT,
ADDON_CHR, ADDON_PER_KG, CPKG, SLAB, LODGE_MODE, DUP_FLAG, DATA_ISSUE, SOURCE_FILE`

- **DUP_FLAG** – same AWB appears on more than one row (rows are kept). Exact repeats
  (same AWB + invoice + date + weight + total) are removed.
- **DATA_ISSUE** – missing/invalid date (BILL_PERIOD left blank), missing weight,
  weight "M", missing total, Basic+Other ≠ Total (SURYA), etc.

## Adding a new agent
Create `agents/<name>.py` with `AGENT, KEY, LABEL, FILE_TYPES, OUTPUT_FILE, EXTRA_COLS`
and `parse(data, name, log) -> DataFrame`, add it to `agents/__init__.py` and to `MENU` in `app.py`.

## Tests
```
pip install reportlab           # only needed to build the fake sample bills
python tests/make_samples.py    # writes tests/samples/
python tests/run_all.py         # runs every parser and prints the output
```
Put real bills in `tests/samples/` (named like the fakes) to check real formats.
