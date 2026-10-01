"""
Activity log -> Google Sheet.

Tabs (created automatically on first use):
  Sessions : one row per visit – login time, last seen, logout time,
             DURATION_MIN and STATUS are Sheet formulas.
  Events   : every login / failed login / logout / agent opened /
             files processed / download.
  Summary  : per user – visits, total minutes, last login (formulas).

How duration works: while a user has the app open, a heartbeat updates
LAST_SEEN every minute. If they log out, LOGOUT_TIME is filled. If they
just close the tab, the heartbeat stops and duration = last seen - login.

Needs two sections in Streamlit Secrets:  [activity_log] sheet_id = "..."
and [gcp_service_account] (the service-account JSON key). If they are
missing, logging is silently switched off and the app works as normal.

All writes go through one background thread so the app never waits on
Google and a Google error can never break the app.
"""

import queue
import threading
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

IST = ZoneInfo("Asia/Kolkata")
HEARTBEAT_SECONDS = 60
CLOSED_AFTER_MIN = 3  # no heartbeat for this long -> STATUS "Closed"

SESSION_HEADERS = ["SESSION_ID", "USERNAME", "NAME", "LOGIN_TIME", "LAST_SEEN",
                   "LOGOUT_TIME", "LOGIN_METHOD", "DURATION_MIN", "STATUS"]
EVENT_HEADERS = ["TIME", "USERNAME", "NAME", "EVENT", "DETAIL", "SESSION_ID"]


def now_ist():
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


# =====================================================
# SHEET WRITER (one per app process)
# =====================================================

class SheetLogger:
    def __init__(self, open_spreadsheet):
        self._open = open_spreadsheet     # callable -> gspread Spreadsheet
        self._q = queue.Queue()
        self._ready = False
        self.sessions = self.events = None
        self.next_session_row = 2
        self.session_rows = {}            # session_id -> row number
        threading.Thread(target=self._worker, daemon=True).start()

    # ---------- setup ----------
    def _setup(self):
        book = self._open()
        titles = [ws.title for ws in book.worksheets()]

        def tab(name, headers, cols):
            if name in titles:
                return book.worksheet(name)
            ws = book.add_worksheet(title=name, rows=1000, cols=cols)
            ws.update(range_name="A1", values=[headers])
            ws.freeze(rows=1)
            return ws

        self.sessions = tab("Sessions", SESSION_HEADERS, len(SESSION_HEADERS))
        self.events = tab("Events", EVENT_HEADERS, len(EVENT_HEADERS))

        if "Summary" not in titles:
            ws = book.add_worksheet(title="Summary", rows=200, cols=4)
            ws.update(
                range_name="A1",
                values=[
                    ["USERNAME", "VISITS", "TOTAL_MINUTES", "LAST_LOGIN"],
                    [
                        "=SORT(UNIQUE(FILTER(Sessions!B2:B,Sessions!B2:B<>\"\")))",
                        "=ARRAYFORMULA(IF(A2:A=\"\",\"\",COUNTIF(Sessions!B2:B,A2:A)))",
                        "=ARRAYFORMULA(IF(A2:A=\"\",\"\",SUMIF(Sessions!B2:B,A2:A,Sessions!H2:H)))",
                        "=ARRAYFORMULA(IF(A2:A=\"\",\"\",IFERROR(VLOOKUP(A2:A,SORT({Sessions!B2:B,Sessions!D2:D},2,FALSE),2,FALSE))))",
                    ],
                ],
                value_input_option="USER_ENTERED",
            )
            ws.freeze(rows=1)

        # continue after the last used row
        self.next_session_row = len(self.sessions.col_values(1)) + 1
        self._ready = True

    # ---------- worker ----------
    def _worker(self):
        while True:
            job = self._q.get()
            for attempt in range(3):
                try:
                    if not self._ready:
                        self._setup()
                    job()
                    break
                except Exception as e:  # network / quota – retry, then drop
                    print(f"[activity_log] write failed (try {attempt + 1}): {e}")
                    self._ready = False
                    time.sleep(2 * (attempt + 1))

    def submit(self, fn):
        self._q.put(fn)

    # ---------- operations ----------
    def start_session(self, sid, username, name, method):
        t = now_ist()

        def job():
            r = self.next_session_row
            self.next_session_row += 1
            self.session_rows[sid] = r
            self.sessions.update(
                range_name=f"A{r}:I{r}",
                values=[[
                    sid, username, name, t, t, "", method,
                    f'=ROUND((IF(F{r}<>"",F{r},E{r})-D{r})*1440,1)',
                    f'=IF(F{r}<>"","Logged out",IF((NOW()-E{r})*1440>{CLOSED_AFTER_MIN},"Closed","Active"))',
                ]],
                value_input_option="USER_ENTERED",
            )
        self.submit(job)

    def _session_row(self, sid):
        r = self.session_rows.get(sid)
        if r is None:  # e.g. app restarted since login
            cell = self.sessions.find(sid, in_column=1)
            r = cell.row if cell else None
            if r:
                self.session_rows[sid] = r
        return r

    def heartbeat(self, sid):
        t = now_ist()

        def job():
            r = self._session_row(sid)
            if r:
                self.sessions.update(range_name=f"E{r}", values=[[t]], value_input_option="USER_ENTERED")
        self.submit(job)

    def end_session(self, sid):
        t = now_ist()

        def job():
            r = self._session_row(sid)
            if r:
                self.sessions.update(range_name=f"E{r}:F{r}", values=[[t, t]], value_input_option="USER_ENTERED")
        self.submit(job)

    def event(self, username, name, event, detail="", sid=""):
        row = [now_ist(), username or "", name or "", event, str(detail)[:1000], sid or ""]
        self.submit(lambda: self.events.append_row(row, value_input_option="USER_ENTERED", table_range="A1"))


@st.cache_resource(show_spinner=False)
def _get_logger():
    if "activity_log" not in st.secrets or "gcp_service_account" not in st.secrets:
        print("[activity_log] not configured – logging disabled")
        return None
    import gspread

    info = {k: v for k, v in st.secrets["gcp_service_account"].items()}
    sheet_id = st.secrets["activity_log"]["sheet_id"]

    def open_spreadsheet():
        return gspread.service_account_from_dict(info).open_by_key(sheet_id)

    return SheetLogger(open_spreadsheet)


def _logger():
    try:
        return _get_logger()
    except Exception as e:
        print(f"[activity_log] disabled: {e}")
        return None


# =====================================================
# API USED BY THE APP
# =====================================================

def _user():
    ss = st.session_state
    return ss.get("username"), ss.get("name"), ss.get("log_session_id")


def log_event(event, detail=""):
    u, n, sid = _user()
    if not u:
        return
    lg = _logger()
    if lg:
        lg.event(u, n, event, detail, sid)


def attach_to_authenticator(authenticator):
    """
    Wraps the authenticator's login check so every successful login,
    remembered-cookie login and failed attempt is logged.
    (Relies on streamlit-authenticator 0.4.x internals – version is pinned.)
    """
    try:
        model = authenticator.authentication_controller.authentication_model
    except AttributeError:
        print("[activity_log] authenticator internals changed – login logging off")
        return
    if getattr(model, "_logged", False):
        return
    original = model.login

    def login(username=None, password=None, *args, **kwargs):
        ok = original(username, password, *args, **kwargs)
        lg = _logger()
        if lg is None:
            return ok
        if ok:
            sid = uuid.uuid4().hex[:12]
            st.session_state["log_session_id"] = sid
            st.session_state["log_last_beat"] = time.time()
            method = "Password" if username else "Remembered (cookie)"
            u, n = st.session_state.get("username"), st.session_state.get("name")
            lg.start_session(sid, u, n, method)
            lg.event(u, n, "LOGIN", method, sid)
        elif ok is False and username:
            lg.event(username, "", "LOGIN_FAILED", "Wrong username or password")
        return ok

    model.login = login
    model._logged = True


def on_logout(_info=None):
    """Pass as callback to authenticator.logout()."""
    lg = _logger()
    u, n, sid = _user()
    if lg and sid:
        lg.end_session(sid)
        lg.event(u, n, "LOGOUT", "", sid)
    st.session_state.pop("log_session_id", None)
    st.session_state.pop("log_last_agent", None)


@st.fragment(run_every=HEARTBEAT_SECONDS)
def heartbeat():
    """Invisible; keeps LAST_SEEN current while the app is open."""
    lg = _logger()
    sid = st.session_state.get("log_session_id")
    if not (lg and sid):
        return
    last = st.session_state.get("log_last_beat", 0)
    if time.time() - last >= HEARTBEAT_SECONDS - 5:
        st.session_state["log_last_beat"] = time.time()
        lg.heartbeat(sid)


def log_agent_opened(choice):
    if st.session_state.get("log_last_agent") != choice:
        st.session_state["log_last_agent"] = choice
        log_event("OPEN_AGENT", choice)
