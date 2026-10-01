import copy
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit_authenticator as stauth

from agents import bhagwati, eds, fdc, index, multi_agent, pcf_south, pcfl_east, pobc, surya
from utils.activity_log import attach_to_authenticator, heartbeat, log_agent_opened, on_logout
from utils.page import run_agent_page
from utils.ui import apply_css, login_footer, login_header, side_label, sidebar_brand, topbar

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
