"""
Look & feel helpers: global CSS, header, page titles, chips, tables.
Colours come from .streamlit/config.toml; this file only adds polish.
"""

import html

import streamlit as st

PLANE = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5'
         'S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/></svg>')
NAVY = "#0B2545"
RED = "#C8102E"

CSS = """
<style>
/* ---------- layout ---------- */
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1400px; }
[data-testid="stHeader"] { background: transparent; }

/* ---------- top brand bar ---------- */
.acl-topbar {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  background: linear-gradient(100deg, #0B2545 0%, #13315C 70%, #1D4E89 100%);
  color: #fff; border-radius: 14px; padding: 14px 22px; margin-bottom: 1.4rem;
  box-shadow: 0 6px 18px rgba(11,37,69,.18);
}
.acl-brand { display: flex; align-items: center; gap: 14px; }
.acl-logo {
  width: 42px; height: 42px; border-radius: 11px; background: #C8102E;
  display: flex; align-items: center; justify-content: center; font-size: 22px; flex: none;
}
.acl-brand-name { font-size: 1.35rem; font-weight: 700; letter-spacing: .2px; line-height: 1.1; }
.acl-brand-sub  { font-size: .8rem; opacity: .75; margin-top: 2px; }
.acl-topbar-right { font-size: .82rem; opacity: .85; text-align: right; }

/* ---------- page title ---------- */
.acl-page-title { margin: .2rem 0 1rem; }
.acl-page-title h2 { margin: 0; padding: 0; font-size: 1.55rem; font-weight: 700; color: #14213D; }
.acl-page-title p  { margin: .25rem 0 0; color: #5B6B82; font-size: .9rem; }

/* ---------- chips ---------- */
.acl-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: .2rem 0 .9rem; }
.acl-chip {
  display: inline-flex; align-items: center; gap: 6px; padding: 4px 11px; border-radius: 999px;
  font-size: .8rem; font-weight: 500; border: 1px solid #DDE3EC; background: #fff; color: #33415C;
}
.acl-chip.ok   { background: #E8F6EE; border-color: #BFE5CF; color: #17663A; }
.acl-chip.warn { background: #FFF6E0; border-color: #F5DFA3; color: #8A5A00; }
.acl-chip.bad  { background: #FDECEE; border-color: #F6C3CA; color: #A0102A; }
.acl-chip.info { background: #EAF1FB; border-color: #C9DAF2; color: #1D4E89; }

/* ---------- section label ---------- */
.acl-section { font-size: .78rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
  color: #5B6B82; margin: 1.1rem 0 .5rem; }

/* ---------- metric cards ---------- */
[data-testid="stMetric"] {
  background: #fff; border: 1px solid #DDE3EC; border-radius: 12px; padding: 14px 16px;
  box-shadow: 0 1px 2px rgba(20,33,61,.04);
}
[data-testid="stMetricLabel"] p { font-size: .78rem !important; color: #5B6B82; font-weight: 500; }
[data-testid="stMetricValue"] { font-size: 1.45rem !important; font-weight: 700; color: #14213D; }

/* ---------- slab matrix ---------- */
.acl-table { width: 100%; border-collapse: separate; border-spacing: 0; background: #fff;
  border: 1px solid #DDE3EC; border-radius: 12px; overflow: hidden; font-size: .9rem; }
.acl-table th { background: #F0F3F8; color: #33415C; font-weight: 600; text-align: right;
  padding: 10px 14px; font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; }
.acl-table th:first-child, .acl-table td:first-child { text-align: left; }
.acl-table td { padding: 10px 14px; text-align: right; border-top: 1px solid #EEF1F6;
  font-variant-numeric: tabular-nums; }
.acl-table tr.total td { font-weight: 700; background: #FAFBFD; }
.acl-table .grp { border-left: 1px solid #E6EAF1; }
.acl-muted { color: #8A97AB; }

/* ---------- uploader ---------- */
[data-testid="stFileUploaderDropzone"] { background: #FAFBFD; border: 1.5px dashed #B9C4D6; }

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #DDE3EC; }
.stTabs [data-baseweb="tab"] { padding: 8px 14px; font-weight: 500; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] .acl-side-brand { display: flex; align-items: center; gap: 10px; margin: -.4rem 0 1rem; }
[data-testid="stSidebar"] .acl-side-brand .acl-logo { width: 34px; height: 34px; font-size: 18px; border-radius: 9px; }
[data-testid="stSidebar"] .acl-side-name { font-weight: 700; font-size: 1.05rem; color: #fff; }
[data-testid="stSidebar"] .acl-user {
  background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12); border-radius: 10px;
  padding: 10px 12px; margin-bottom: 1rem; font-size: .85rem; }
[data-testid="stSidebar"] .acl-user b { display: block; font-size: .95rem; color: #fff; }
[data-testid="stSidebar"] .acl-user span { opacity: .7; font-size: .75rem; }
[data-testid="stSidebar"] [role="radiogroup"] { gap: 2px; }
[data-testid="stSidebar"] [role="radiogroup"] label {
  padding: 7px 10px; border-radius: 8px; width: 100%; margin: 0; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255,255,255,.07); }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
  background: rgba(255,90,110,.18); box-shadow: inset 3px 0 0 #FF5A6E; }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p { color: #fff; font-weight: 600; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) {
  display: none; }  /* hide radio dot – rows look like a menu */
.acl-side-label { font-size: .7rem; letter-spacing: .1em; text-transform: uppercase; opacity: .55;
  margin: .4rem 0 .3rem; }

/* ---------- login ---------- */
.acl-login-head { text-align: center; margin: 3vh 0 1.2rem; }
.acl-login-head .acl-logo { width: 56px; height: 56px; font-size: 28px; border-radius: 14px; margin: 0 auto 12px; }
.acl-login-head h1 { font-size: 1.7rem; margin: 0; padding: 0; color: #14213D; }
.acl-login-head p { color: #5B6B82; margin: .3rem 0 0; font-size: .92rem; }
[data-testid="stForm"] { background: #fff; border-radius: 14px; padding: 1.4rem 1.4rem 1rem;
  box-shadow: 0 8px 24px rgba(11,37,69,.08); }
[data-testid="stForm"] [data-testid="stElementContainer"]:has([data-testid="stFormSubmitButton"]),
[data-testid="stForm"] [data-testid="stElementContainer"]:has([data-testid="stFormSubmitButton"]) > div,
[data-testid="stForm"] [data-testid="stFormSubmitButton"] { width: 100% !important; }
[data-testid="stFormSubmitButton"] button {
  width: 100% !important; justify-content: center; background: #C8102E; color: #fff; border: none; font-weight: 600; padding: .55rem 0; }
[data-testid="stFormSubmitButton"] button:hover { background: #A50D26; color: #fff; }
.acl-logo svg { width: 58%; height: 58%; fill: #fff; }
.acl-foot { text-align: center; color: #8A97AB; font-size: .78rem; margin-top: 1.2rem; }

/* ---------- mobile ---------- */
@media (max-width: 640px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 1rem; }
  .acl-topbar { padding: 12px 14px; }
  .acl-topbar-right { display: none; }
  .acl-brand-name { font-size: 1.15rem; }
  [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
  .acl-table { font-size: .8rem; }
  .acl-table th, .acl-table td { padding: 8px 8px; }
}
</style>
"""


def apply_css():
    st.markdown(CSS, unsafe_allow_html=True)


def esc(x):
    return html.escape(str(x))


def topbar(right_text=""):
    st.markdown(
        f"""<div class="acl-topbar">
              <div class="acl-brand">
                <div class="acl-logo">{PLANE}</div>
                <div><div class="acl-brand-name">ACL Dummy</div>
                     <div class="acl-brand-sub">Freight bill processing &amp; CPKG analysis</div></div>
              </div>
              <div class="acl-topbar-right">{esc(right_text)}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def login_header():
    st.markdown(
        f"""<div class="acl-login-head">
             <div class="acl-logo">{PLANE}</div>
             <h1>ACL Dummy</h1>
             <p>Sign in to process agent freight bills</p>
           </div>""",
        unsafe_allow_html=True,
    )


def login_footer():
    st.markdown('<div class="acl-foot">Trouble signing in? Contact the Tariff &amp; Yield team.</div>',
                unsafe_allow_html=True)


def sidebar_brand(name, username):
    st.sidebar.markdown(
        f"""<div class="acl-side-brand"><div class="acl-logo">{PLANE}</div>
              <div class="acl-side-name">ACL Dummy</div></div>
            <div class="acl-user"><span>Signed in as</span><b>{esc(name)}</b><span>@{esc(username)}</span></div>""",
        unsafe_allow_html=True,
    )


def side_label(text):
    st.sidebar.markdown(f'<div class="acl-side-label">{esc(text)}</div>', unsafe_allow_html=True)


def page_title(title, subtitle=""):
    sub = f"<p>{esc(subtitle)}</p>" if subtitle else ""
    st.markdown(f'<div class="acl-page-title"><h2>{esc(title)}</h2>{sub}</div>', unsafe_allow_html=True)


def section(text):
    st.markdown(f'<div class="acl-section">{esc(text)}</div>', unsafe_allow_html=True)


def chips(items):
    """items: list of (text, kind) where kind in ok / warn / bad / info / ''"""
    inner = "".join(f'<span class="acl-chip {k}">{esc(t)}</span>' for t, k in items if t)
    st.markdown(f'<div class="acl-chips">{inner}</div>', unsafe_allow_html=True)


def html_table(headers, rows, total_row=None, group_starts=()):
    """Simple styled table. group_starts: column indexes that get a left divider."""
    def cls(i):
        return ' class="grp"' if i in group_starts else ""

    head = "".join(f"<th{cls(i)}>{h}</th>" for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f"<td{cls(i)}>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows
    )
    if total_row:
        body += '<tr class="total">' + "".join(f"<td{cls(i)}>{c}</td>" for i, c in enumerate(total_row)) + "</tr>"
    st.markdown(f'<table class="acl-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>',
                unsafe_allow_html=True)
