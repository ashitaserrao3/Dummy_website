import copy
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit_authenticator as stauth

# =====================================================
# STARTUP CHECK – if a file/folder didn't reach the repo, say exactly which
# (Streamlit Cloud hides the real error message otherwise)
# =====================================================

from pathlib import Path

_ROOT = Path(__file__).parent
_REQUIRED = [
    "agents/__init__.py", "agents/index.py", "agents/pobc.py", "agents/pcf_common.py",
    "agents/pcf_south.py", "agents/pcfl_east.py", "agents/surya.py", "agents/bhagwati.py",
    "agents/fdc.py", "agents/eds.py", "agents/multi_agent.py",
    "utils/__init__.py", "utils/common.py", "utils/schema.py", "utils/page.py", "utils/dashboard.py",
    "utils/exporter.py", "utils/excel_utils.py", "utils/ui.py", "utils/activity_log.py",
]
_missing = [f for f in _REQUIRED if not (_ROOT / f).is_file()]
if _missing:
    st.error(
        "Some app files are missing from the GitHub repo, so the app can't start.\n\n"
        "Upload these (keeping the folder names) and the app will restart by itself:\n\n"
        + "\n".join(f"- `{f}`" for f in _missing)
    )
    st.stop()

try:
    from agents import bhagwati, eds, fdc, index, multi_agent, pcf_south, pcfl_east, pobc, surya
    from utils.activity_log import attach_to_authenticator, heartbeat, log_agent_opened, on_logout
    from utils.page import run_agent_page
    from utils.ui import apply_css, login_footer, login_header, side_label, sidebar_brand, topbar
except ModuleNotFoundError as e:
    # Show the real missing name (Streamlit Cloud otherwise hides it)
    ours = str(e.name or "").split(".")[0] in ("agents", "utils")
    st.error(
        f"The app can't start: module **`{e.name}`** was not found.\n\n"
        + ("This is one of the app's own files – check it is in the GitHub repo inside the right folder "
           "(e.g. `utils/common.py`, `agents/index.py`)."
           if ours else
           "This is a Python package – check `requirements.txt` is in the top level of the repo and lists it, "
           "then use **Manage app → Reboot app**.")
    )
    st.stop()

# =====================================================
# PAGE CONFIG  (only place set_page_config is called)
# =====================================================

st.set_page_config(page_title="ACL Dummy", page_icon="✈️", layout="wide")
apply_css()

# =====================================================
# AUTHENTICATION
# Users + cookie key live in Streamlit Secrets, never in the repo.
#   Community Cloud : App settings -> Secrets
#   Local run       : .streamlit/secrets.toml (git-ignored)
# =====================================================


def _to_dict(obj):
    """st.secrets is read-only; the authenticator needs a normal dict."""
    if hasattr(obj, "items"):
        return {k: _to_dict(v) for k, v in obj.items()}
    return copy.deepcopy(obj)


if "credentials" not in st.secrets or "cookie" not in st.secrets:
    st.error(
        "Login settings are missing. Add the [credentials] and [cookie] sections "
        "to Streamlit Secrets (see secrets.toml.example)."
    )
    st.stop()

credentials = _to_dict(st.secrets["credentials"])
cookie = _to_dict(st.secrets["cookie"])

authenticator = stauth.Authenticate(
    credentials,
    cookie["name"],
    cookie["key"],
    float(cookie.get("expiry_days", 30)),
    auto_hash=False,  # passwords in secrets are already bcrypt hashes
)

attach_to_authenticator(authenticator)  # records logins / failed logins to the Google Sheet

# =====================================================
# LOGIN SCREEN
# =====================================================

if not st.session_state.get("authentication_status"):
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        login_header()
        try:
            authenticator.login(
                fields={"Form name": "Sign in", "Username": "Username",
                        "Password": "Password", "Login": "Sign in"},
            )
        except Exception as e:
            st.error(e)
        if st.session_state.get("authentication_status") is False:
            st.error("Username or password is incorrect", icon="🔒")
        login_footer()

    if st.session_state.get("authentication_status"):
        st.rerun()  # signed in (or remembered) -> draw the main app
    st.stop()

# =====================================================
# MAIN APP
# =====================================================

MENU = {
    "INDEX": index,
    "POBC": pobc,
    "PCF(South)": pcf_south,
    "PCFL(East)": pcfl_east,
    "SURYA": surya,
    "BHAGWATI": bhagwati,
    "FDC": fdc,
    "EDS": eds,
    "MULTI - AGENT": None,
}
ICONS = {"FDC": "🚚", "MULTI - AGENT": "🧩"}
NAMES = {"MULTI - AGENT": "All agents (combined)"}

heartbeat()  # keeps session duration up to date while the app is open

with st.sidebar:
    sidebar_brand(st.session_state.get("name"), st.session_state.get("username"))
    side_label("Agent")
    choice = st.radio(
        "Agent",
        list(MENU.keys()),
        format_func=lambda k: f"{ICONS.get(k, '✈')}  {NAMES.get(k, k)}",
        label_visibility="collapsed",
        key="nav",
    )
    st.divider()
    authenticator.logout("Sign out", location="sidebar", callback=on_logout, use_container_width=True)
    if not st.session_state.get("authentication_status"):
        st.rerun()  # just signed out -> back to the login screen

log_agent_opened(choice)
topbar(datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%a, %d %b %Y"))

if MENU[choice] is None:
    multi_agent.run()
else:
    run_agent_page(MENU[choice])
