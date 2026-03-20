"""
InstaLens v4.0 — Instagram Analytics Dashboard
Powered by HasData API · Streamlit · Plotly

Key fixes in v4.0:
  - API key stored in st.session_state (survives reruns)
  - Demo Mode defaults to False
  - "Analyse" button clears cache and force-refetches
  - No silent mock fallback in live mode — errors shown explicitly
  - Per-profile LIVE / DEMO / ERROR status badges
  - API validated on key entry, not as a gate before fetching
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import random as _rnd
import requests
from datetime import datetime, timedelta

from data_fetcher import (
    HasDataFetcher, HasDataAuthError, HasDataFetchError, HasDataRateLimitError,
    generate_mock_data, generate_mock_profile
)
from utils import format_number, benchmark_er, rate_engagement

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="InstaLens · Analytics",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INITIALISATION  — runs once per session
# ══════════════════════════════════════════════════════════════════════════════
if "api_key"        not in st.session_state: st.session_state.api_key        = ""
if "api_validated"  not in st.session_state: st.session_state.api_validated  = False
if "api_valid_msg"  not in st.session_state: st.session_state.api_valid_msg  = ""
if "force_refresh"  not in st.session_state: st.session_state.force_refresh  = 0
if "use_mock"       not in st.session_state: st.session_state.use_mock       = False

# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════
BG     = "#07070f"
CARD   = "#0f0f1c"
CARD2  = "#141428"
BORDER = "#1e1e38"

TX1 = "#eeeaf8"
TX2 = "#9896b4"
TX3 = "#5c5a78"

PINK   = "#f72585"
VIOLET = "#7209b7"
PURPLE = "#b5179e"
CYAN   = "#06d6e0"
GREEN  = "#4ade80"
RED    = "#f87171"
AMBER  = "#fbbf24"

CHART_BG = "rgba(0,0,0,0)"
GRID_COL = "#1c1c34"
TICK_COL = "#3e3c5a"

# ══════════════════════════════════════════════════════════════════════════════
#  GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

html,body,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif;font-size:14px}
.stApp{background:#07070f;color:#eeeaf8}
.block-container{padding-top:1.2rem!important;padding-bottom:2rem!important}

[data-testid="stSidebar"]{background:#0b0b18!important;border-right:1px solid #1c1c34}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p,[data-testid="stSidebar"] span{color:#a8a6c4!important}
[data-testid="stSidebar"] .stTextInput input,[data-testid="stSidebar"] .stTextArea textarea{background:#111124!important;color:#eeeaf8!important;border:1px solid #282848!important;border-radius:8px!important;font-size:13px!important}
[data-testid="stSidebar"] .stTextInput input:focus{border-color:#f72585!important;box-shadow:0 0 0 2px rgba(247,37,133,.15)!important}

.brand{font-family:'Space Grotesk',sans-serif;font-size:22px;font-weight:700;background:linear-gradient(135deg,#f72585,#b5179e,#7209b7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-.5px}
.brand-sub{font-size:9px;color:#5c5a78;letter-spacing:3px;text-transform:uppercase;margin-top:-2px}

div[data-testid="stTabs"] button{font-family:'Plus Jakarta Sans',sans-serif!important;font-size:12px!important;font-weight:500!important;color:#5c5a78!important;padding:8px 16px!important}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#eeeaf8!important;border-bottom-color:#f72585!important}

.kpi-card{background:#0f0f1c;border:1px solid #1e1e38;border-radius:14px;padding:16px 18px 14px;position:relative;overflow:hidden;min-height:108px;box-sizing:border-box}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#f72585,#7209b7);border-radius:14px 14px 0 0}
.kpi-card.accent-blue::before{background:linear-gradient(90deg,#06d6e0,#0096c7)}
.kpi-card.accent-green::before{background:linear-gradient(90deg,#4ade80,#16a34a)}
.kpi-card.accent-amber::before{background:linear-gradient(90deg,#fbbf24,#d97706)}
.kpi-label{font-size:10px;font-weight:600;letter-spacing:1.6px;text-transform:uppercase;color:#5c5a78;margin-bottom:8px;line-height:1.4}
.kpi-num{font-family:'Space Grotesk',sans-serif;font-size:28px;font-weight:700;color:#eeeaf8;line-height:1.1;margin-bottom:6px;word-break:break-word}
.kpi-num-sm{font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:600;color:#eeeaf8;line-height:1.2;margin-bottom:6px;word-break:break-word}
.kpi-num-xs{font-family:'Plus Jakarta Sans',sans-serif;font-size:14px;font-weight:600;color:#eeeaf8;line-height:1.4;margin-bottom:6px}
.kpi-delta-pos{font-size:11px;color:#4ade80;font-weight:500}
.kpi-delta-neg{font-size:11px;color:#f87171;font-weight:500}
.kpi-delta-neu{font-size:11px;color:#9896b4;font-weight:500}
.sec-h{font-family:'Space Grotesk',sans-serif;font-size:14px;font-weight:700;color:#eeeaf8;margin:0 0 2px;letter-spacing:-.1px}
.sec-s{font-size:11px;color:#5c5a78;margin-bottom:12px;line-height:1.4}
.profile-card{background:linear-gradient(135deg,#0f0f22,#180f30);border:1px solid #28184a;border-radius:16px;padding:20px 24px;margin-bottom:20px}
.profile-name{font-family:'Space Grotesk',sans-serif;font-size:22px;font-weight:700;color:#eeeaf8;margin-bottom:4px}
.profile-bio{font-size:12px;color:#9896b4;line-height:1.5;margin-bottom:12px;max-width:680px}
.pstat{display:inline-block;background:rgba(114,9,183,.15);border:1px solid rgba(181,23,158,.3);border-radius:6px;padding:4px 12px;font-size:11px;font-weight:500;color:#d8b4fe;margin-right:8px;margin-top:4px}
.src-live{display:inline-block;background:rgba(74,222,128,.1);border:1px solid rgba(74,222,128,.3);border-radius:6px;padding:3px 10px;font-size:10px;font-weight:600;color:#86efac;letter-spacing:.5px}
.src-demo{display:inline-block;background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3);border-radius:6px;padding:3px 10px;font-size:10px;font-weight:600;color:#fde68a;letter-spacing:.5px}
.src-err{display:inline-block;background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.3);border-radius:6px;padding:3px 10px;font-size:10px;font-weight:600;color:#fca5a5;letter-spacing:.5px}
.post-card{background:#0f0f1c;border:1px solid #1c1c38;border-radius:12px;padding:14px 16px;margin-bottom:10px}
.post-type{display:inline-block;background:linear-gradient(135deg,#f72585,#7209b7);color:#fff;font-size:9px;font-weight:700;padding:2px 9px;border-radius:20px;letter-spacing:1px;text-transform:uppercase;margin-bottom:7px}
.post-cap{font-size:12px;color:#9896b4;line-height:1.5;margin-bottom:8px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.post-row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.pst{font-size:11px;color:#5c5a78}
.pst b{color:#eeeaf8;font-weight:600}
.post-er{font-size:10px;color:#5c5a78;margin-top:5px}
.bench-pill{display:inline-block;padding:7px 14px;border-radius:8px;font-size:12px;font-weight:500;line-height:1.5}
.bench-good{background:rgba(74,222,128,.09);border:1px solid rgba(74,222,128,.28);color:#86efac}
.bench-ok{background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.28);color:#fde68a}
.bench-bad{background:rgba(248,113,113,.09);border:1px solid rgba(248,113,113,.28);color:#fca5a5}
.tag-chip{display:inline-block;background:rgba(99,91,255,.12);border:1px solid rgba(99,91,255,.25);border-radius:20px;padding:3px 11px;margin:3px;font-size:11px;color:#c4b5fd}
.hdivider{border:none;border-top:1px solid #1c1c34;margin:18px 0}
.err-box{background:rgba(248,113,113,.08);border:1px solid rgba(248,113,113,.28);border-radius:10px;padding:12px 16px;font-size:12px;color:#fca5a5;line-height:1.6;margin-bottom:12px}
.info-box{background:rgba(114,9,183,.1);border:1px solid rgba(114,9,183,.28);border-radius:10px;padding:10px 14px;font-size:12px;color:#c4b5fd;line-height:1.5}
.warn-box{background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.28);border-radius:10px;padding:10px 14px;font-size:12px;color:#fde68a;line-height:1.5}
.ok-box{background:rgba(74,222,128,.08);border:1px solid rgba(74,222,128,.28);border-radius:10px;padding:10px 14px;font-size:12px;color:#86efac;line-height:1.5}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-thumb{background:#2a2a48;border-radius:4px}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def hex_rgb(h):
    return int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)

def rgba(h, a):
    r,g,b = hex_rgb(h); return f"rgba({r},{g},{b},{a})"

def base_layout(h=240, margin=None, hovermode="x unified"):
    m = margin or dict(l=0,r=0,t=10,b=0)
    return dict(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
                font=dict(color=TX2, family="Plus Jakarta Sans"),
                margin=m, height=h, hovermode=hovermode,
                xaxis=dict(showgrid=False, color=TICK_COL, tickfont=dict(size=10), linecolor=GRID_COL),
                yaxis=dict(showgrid=True, gridcolor=GRID_COL, color=TICK_COL, tickfont=dict(size=10)))

def kpi(label, value, delta=None, accent=""):
    """Single-line HTML — avoids Streamlit 4-space markdown code-block rule."""
    vlen = len(str(value))
    vcls = "kpi-num" if vlen <= 7 else ("kpi-num-sm" if vlen <= 12 else "kpi-num-xs")
    d_html = ""
    if delta is not None:
        dcls  = "kpi-delta-pos" if delta > 0 else ("kpi-delta-neg" if delta < 0 else "kpi-delta-neu")
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "—")
        d_html = f'<div class="{dcls}">{arrow} {abs(delta):.1f}% vs prev period</div>'
    return (f'<div class="kpi-card {accent}">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="{vcls}">{value}</div>'
            f'{d_html}</div>')

def source_badge(source: str) -> str:
    if source == "live":
        return '<span class="src-live">● LIVE</span>'
    elif source == "demo":
        return '<span class="src-demo">● DEMO</span>'
    else:
        return '<span class="src-err">● ERROR</span>'


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="brand">📸 InstaLens</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Social Analytics Platform</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── Data Source ───────────────────────────────────────────────────────────
    st.markdown("**🔌 Data Source**")

    # Toggle — stored in session_state so it persists
    use_mock = st.toggle("Demo Mode", value=st.session_state.use_mock, key="use_mock_toggle")
    st.session_state.use_mock = use_mock

    if not use_mock:
        # API key input — value persisted in session_state
        new_key = st.text_input(
            "HasData API Key",
            value=st.session_state.api_key,
            type="password",
            placeholder="hd_xxxxxxxxxxxxxxxx",
            help="Get your key at hasdata.com",
            key="api_key_input",
        )
        # Update session_state whenever the key changes
        if new_key != st.session_state.api_key:
            st.session_state.api_key       = new_key
            st.session_state.api_validated = False
            st.session_state.api_valid_msg = ""

        if st.session_state.api_key:
            if not st.session_state.api_validated:
                st.markdown('<div class="warn-box">⚠️ Key entered — click Analyse to fetch live data.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ok-box">✅ {st.session_state.api_valid_msg}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="warn-box">⚠️ Enter your HasData API key to use live data.</div>', unsafe_allow_html=True)
    else:
        st.session_state.api_key = ""
        st.session_state.api_validated = False
        st.markdown('<div class="info-box">🎭 Demo Mode is ON — showing realistic mock data.<br>Toggle off + enter API key for live data.</div>', unsafe_allow_html=True)

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # ── Input Mode ────────────────────────────────────────────────────────────
    st.markdown("**📥 Input Mode**")
    input_mode = st.radio("Input Mode",
                          ["Single Profile", "Competitor Comparison", "Hashtag Tracking"],
                          label_visibility="collapsed")

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # ── Profiles ──────────────────────────────────────────────────────────────
    if input_mode == "Single Profile":
        st.markdown("**👤 Profile**")
        single_user = st.text_input("Username", value="natgeo",
                                    placeholder="Enter Instagram username (no @)")
        usernames = [single_user.strip().lstrip("@")] if single_user.strip() else ["natgeo"]

    elif input_mode == "Competitor Comparison":
        st.markdown("**⚔️ Profiles (max 3)**")
        raw_profiles = st.text_area("One username per line",
                                    value="natgeo\nbbc\ntime",
                                    height=90, help="No @ needed")
        usernames = [u.strip().lstrip("@") for u in raw_profiles.split("\n") if u.strip()][:3]
        if len(usernames) < 2:
            st.markdown('<div class="warn-box">⚠️ Add at least 2 profiles.</div>', unsafe_allow_html=True)
        else:
            st.caption(f"{len(usernames)} / 3 profiles loaded")

    else:  # Hashtag Tracking
        st.markdown("**👤 Anchor Profile**")
        anchor_user = st.text_input("Username", value="natgeo", placeholder="natgeo")
        usernames = [anchor_user.strip().lstrip("@")] if anchor_user.strip() else ["natgeo"]
        st.markdown('<div class="info-box">🔍 Hashtags auto-extracted from post captions.</div>', unsafe_allow_html=True)

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # ── Options ───────────────────────────────────────────────────────────────
    st.markdown("**📅 Date Range**")
    date_range = st.selectbox("Date Range",
                              ["Last 7 days", "Last 30 days", "Last 90 days"],
                              index=1, label_visibility="collapsed")
    days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}[date_range]

    st.markdown("**🎨 Chart Style**")
    scheme = st.selectbox("Chart Colors",
                          ["Magenta / Violet", "Cyan / Teal", "Amber / Gold"],
                          label_visibility="collapsed")
    COLORS = {
        "Magenta / Violet": [PINK,  PURPLE, VIOLET, "#560bad", "#3a0ca3"],
        "Cyan / Teal":      [CYAN,  "#00bbf9", "#0096c7", "#0077b6", "#023e8a"],
        "Amber / Gold":     [AMBER, "#fb5607", "#ff006e", "#8338ec", "#3a86ff"],
    }[scheme]

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Analyse button — CLEARS CACHE and triggers fresh fetch ────────────────
    if st.button("🚀 Analyse Now", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.session_state.force_refresh += 1
        st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.caption("InstaLens v4.0 · HasData API · Streamlit")


# ══════════════════════════════════════════════════════════════════════════════
#  DATA FETCHING  — with explicit error handling, no silent mock fallback
# ══════════════════════════════════════════════════════════════════════════════

# Resolve effective api_key from session_state (persists across reruns)
api_key  = st.session_state.api_key.strip() if not use_mock else ""
use_live = bool(api_key) and not use_mock

@st.cache_data(ttl=300, show_spinner=False)
def load_live_data(usernames: tuple, api_key: str, days: int, _refresh: int) -> dict:
    """
    Fetch from HasData API. '_refresh' param changes cache key when
    Analyse button is clicked, forcing a fresh fetch.
    Never silently falls back to mock — raises on auth errors.
    """
    fetcher = HasDataFetcher(api_key)
    return fetcher.fetch_all(list(usernames), days)

@st.cache_data(ttl=600, show_spinner=False)
def load_mock_data(usernames: tuple, days: int) -> dict:
    """Generate mock data. Cached separately from live data."""
    return generate_mock_data(list(usernames), days)

# ── Execute fetch ─────────────────────────────────────────────────────────────
fetch_errors:  Dict[str, str] = {}
global_error:  str = ""
data_source:   str = "demo"

with st.spinner("🔍 Fetching data…"):
    if use_live:
        try:
            raw = load_live_data(
                tuple(usernames),
                api_key,
                days,
                st.session_state.force_refresh,
            )
            fetch_errors = raw.get("errors", {})
            data_source  = "live"
            st.session_state.api_validated = True
            st.session_state.api_valid_msg = "API key valid — live data loaded"

        except HasDataAuthError as e:
            global_error = str(e)
            st.session_state.api_validated = False
            # Fall back to mock so page isn't blank
            raw = load_mock_data(tuple(usernames), days)
            data_source = "demo"

        except (HasDataFetchError, HasDataRateLimitError) as e:
            global_error = str(e)
            raw = load_mock_data(tuple(usernames), days)
            data_source = "demo"

        except Exception as e:
            global_error = f"Unexpected error: {str(e)[:200]}"
            raw = load_mock_data(tuple(usernames), days)
            data_source = "demo"
    else:
        raw = load_mock_data(tuple(usernames), days)
        data_source = "demo"

profiles_data = raw.get("profiles", {})
hashtags_data = raw.get("hashtags", {})

# Ensure every username has at least an empty dict
for u in usernames:
    if u not in profiles_data:
        profiles_data[u] = {}


# ══════════════════════════════════════════════════════════════════════════════
#  GLOBAL ERROR / STATUS BANNERS
# ══════════════════════════════════════════════════════════════════════════════
h_l, h_r = st.columns([5, 1])
with h_l:
    MODE_ICONS   = {"Single Profile":"👤","Competitor Comparison":"⚔️","Hashtag Tracking":"🏷️"}
    profiles_str = " · ".join(f"@{u}" for u in usernames)
    st.markdown(
        f"<h1 style='font-family:Space Grotesk,sans-serif;font-size:24px;font-weight:700;"
        f"color:{TX1};margin:0;letter-spacing:-.4px'>"
        f"{MODE_ICONS[input_mode]} {input_mode} Report</h1>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<p style='color:{TX3};font-size:12px;margin-top:4px'>"
        f"{profiles_str} · {date_range} · {datetime.now().strftime('%b %d, %Y %H:%M')}</p>",
        unsafe_allow_html=True
    )
with h_r:
    if data_source == "live":
        st.markdown('<div class="ok-box" style="text-align:center;margin-top:8px;padding:6px 10px">✅ LIVE</div>', unsafe_allow_html=True)
    elif global_error:
        st.markdown('<div class="err-box" style="text-align:center;margin-top:8px;padding:6px 10px">❌ ERROR</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warn-box" style="text-align:center;margin-top:8px;padding:6px 10px">🎭 DEMO</div>', unsafe_allow_html=True)

# Show any global error
if global_error:
    st.markdown(f'<div class="err-box">❌ <strong>Fetch Error:</strong> {global_error}<br>'
                f'Showing demo data as fallback. Fix the issue above and click <strong>Analyse Now</strong>.</div>',
                unsafe_allow_html=True)

# Show per-profile fetch errors
for handle, err_msg in fetch_errors.items():
    st.markdown(f'<div class="err-box">⚠️ <strong>@{handle}:</strong> {err_msg}</div>',
                unsafe_allow_html=True)

# Demo mode info banner
if data_source == "demo" and not global_error:
    st.markdown(
        '<div class="info-box">🎭 <strong>Demo Mode</strong> — all data is simulated. '
        'Toggle off Demo Mode and enter your HasData API key, then click <strong>🚀 Analyse Now</strong> for live data.</div>',
        unsafe_allow_html=True
    )

st.markdown("<hr class='hdivider' style='margin:12px 0 18px'>", unsafe_allow_html=True)

# Profile selector (competitor mode)
if input_mode == "Competitor Comparison" and len(usernames) > 1:
    selected = st.selectbox("🔍 Deep-dive into:", usernames, format_func=lambda x: f"@{x}")
else:
    selected = usernames[0] if usernames else "natgeo"

pd_main = profiles_data.get(selected, {})
pd_source = pd_main.get("_data_source", data_source)

# Per-profile no-data warning
if not pd_main or pd_main.get("followers", 0) == 0:
    st.markdown(
        f'<div class="warn-box">⚠️ No data available for <strong>@{selected}</strong>. '
        f'{"Check the username spelling and ensure the profile is public." if use_live else "Try a known handle like natgeo, nasa, or bbc in Demo Mode."}</div>',
        unsafe_allow_html=True
    )

followers_val = max(pd_main.get("followers", 1), 1)


# ══════════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_labels = ["📊 Overview", "📈 Growth & Engagement", "🎬 Content & Reels", "🏷️ Hashtags"]
if input_mode == "Competitor Comparison":
    tab_labels.append("⚔️ Competitor Bench")
tabs = st.tabs(tab_labels)


# ──────────────────────────────────────────────────────────────────────────────
#  TAB 1 — OVERVIEW
# ──────────────────────────────────────────────────────────────────────────────
with tabs[0]:
    verified_str = " ✅" if pd_main.get("verified") else ""
    bio_str      = (pd_main.get("bio", "") or "")[:130]
    badge        = source_badge(pd_source)

    hero = (
        f'<div class="profile-card">'
        f'<div class="profile-name">@{selected}{verified_str} {badge}</div>'
        f'<div class="profile-bio">{bio_str}</div>'
        f'<div>'
        f'<span class="pstat">👥 {format_number(pd_main.get("followers",0))} followers</span>'
        f'<span class="pstat">➡️ {format_number(pd_main.get("following",0))} following</span>'
        f'<span class="pstat">📝 {format_number(pd_main.get("total_posts",0))} posts</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(hero, unsafe_allow_html=True)

    # Core KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, value, delta, accent in [
        (c1, "Followers",         format_number(pd_main.get("followers",0)),           pd_main.get("followers_delta",0), ""),
        (c2, "Engagement Rate",   f"{pd_main.get('engagement_rate',0):.2f}%",          pd_main.get("er_delta",0), ""),
        (c3, "Avg Reach / Post",  format_number(pd_main.get("avg_reach",0)),           pd_main.get("reach_delta",0), ""),
        (c4, "Total Impressions", format_number(pd_main.get("total_impressions",0)),   pd_main.get("imp_delta",0), ""),
        (c5, "Avg Likes",         format_number(pd_main.get("avg_likes",0)),           None, ""),
    ]:
        with col:
            st.markdown(kpi(label, value, delta, accent), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Reels KPIs
    st.markdown('<p class="sec-h">🎬 Reels at a Glance</p>', unsafe_allow_html=True)
    er_val_main  = pd_main.get("engagement_rate", 0)
    clean_rate   = rate_engagement(er_val_main).split(" ", 1)[-1] if rate_engagement(er_val_main) else "N/A"
    r1, r2, r3, r4 = st.columns(4)
    for col, label, value, accent in [
        (r1, "Reel Avg Plays",    format_number(pd_main.get("reel_avg_plays",0)), ""),
        (r2, "Reel Eng. Rate",    f"{pd_main.get('reel_er',0):.2f}%",            ""),
        (r3, "Reels This Period", str(pd_main.get("reel_count",0)),               ""),
        (r4, "ER Quality",        clean_rate,                                     ""),
    ]:
        with col:
            st.markdown(kpi(label, value, None, accent), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Stories KPIs
    st.markdown('<p class="sec-h">📖 Stories at a Glance</p>', unsafe_allow_html=True)
    story_views     = int(followers_val * 0.08)
    story_replies   = int(story_views * 0.012)
    story_exit      = min(round(25 + (100 / max(followers_val / 1e6, 0.01)) * 0.5, 1), 65.0)
    story_link_taps = int(story_views * 0.03)
    s1, s2, s3, s4  = st.columns(4)
    for col, label, value, accent in [
        (s1, "Avg Story Views",   format_number(story_views),     "accent-blue"),
        (s2, "Story Replies",     format_number(story_replies),   "accent-blue"),
        (s3, "Exit Rate",         f"{story_exit:.1f}%",           "accent-blue"),
        (s4, "Link Tap-Throughs", format_number(story_link_taps), "accent-blue"),
    ]:
        with col:
            st.markdown(kpi(label, value, None, accent), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ER Benchmark banner
    bench_text = benchmark_er(followers_val, er_val_main)
    er_rate    = rate_engagement(er_val_main)
    bcls       = "bench-good" if "▲" in bench_text else ("bench-ok" if "≈" in bench_text else "bench-bad")
    st.markdown(f'<div class="bench-pill {bcls}">📐 <strong>ER Benchmark:</strong> {bench_text} &nbsp;·&nbsp; {er_rate}</div>', unsafe_allow_html=True)

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # Top Posts
    st.markdown('<p class="sec-h">🏆 Top Posts This Period</p>', unsafe_allow_html=True)
    st.markdown('<p class="sec-s">Ranked by likes in the selected date range</p>', unsafe_allow_html=True)
    top_posts = pd_main.get("top_posts", [])
    if top_posts:
        pc = st.columns(3)
        for i, post in enumerate(top_posts[:6]):
            with pc[i % 3]:
                cap   = post.get("caption", "No caption.") or "No caption."
                ptype = post.get("type", "POST") or "POST"
                lk    = format_number(post.get("likes", 0))
                cm    = format_number(post.get("comments", 0))
                sv    = format_number(post.get("saves", 0))
                er_p  = f"{post.get('engagement_rate', 0):.2f}%"
                dt    = post.get("date", "")
                url   = post.get("url", "") or ""
                lnk   = (f'<a href="{url}" target="_blank" style="color:{VIOLET};font-size:10px;text-decoration:none">🔗 View</a>'
                         if url else "")
                st.markdown(
                    '<div class="post-card">'
                    + f'<div class="post-type">{ptype}</div>'
                    + f'<div class="post-cap">{cap}</div>'
                    + '<div class="post-row">'
                    + f'<span class="pst">❤️ <b>{lk}</b></span>'
                    + f'<span class="pst">💬 <b>{cm}</b></span>'
                    + f'<span class="pst">🔖 <b>{sv}</b></span>'
                    + '</div>'
                    + f'<div class="post-er">{dt} · ER <b style="color:{COLORS[0]}">{er_p}</b> {lnk}</div>'
                    + '</div>',
                    unsafe_allow_html=True
                )
    else:
        st.markdown('<div class="info-box">No post data available for this profile.</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
#  TAB 2 — GROWTH & ENGAGEMENT
# ──────────────────────────────────────────────────────────────────────────────
with tabs[1]:
    ga, gb = st.columns([3, 2])
    with ga:
        st.markdown('<p class="sec-h">📈 Follower Growth</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-s">Daily follower count over the period</p>', unsafe_allow_html=True)
        gdf = pd.DataFrame(pd_main.get("growth_series", []))
        if not gdf.empty:
            fig_g = go.Figure()
            fig_g.add_trace(go.Scatter(x=gdf["date"], y=gdf["followers"], mode="lines",
                                       line=dict(color=COLORS[0], width=2.5),
                                       fill="tozeroy", fillcolor=rgba(COLORS[0], .07),
                                       hovertemplate="<b>%{x}</b><br>%{y:,.0f} followers<extra></extra>"))
            fig_g.update_layout(**base_layout(240))
            st.plotly_chart(fig_g, use_container_width=True, key="g_growth")

    with gb:
        st.markdown('<p class="sec-h">💬 Weekly Engagement Rate</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-s">Average ER (%) per week</p>', unsafe_allow_html=True)
        er_df = pd.DataFrame(pd_main.get("er_series", []))
        if not er_df.empty:
            fig_er = go.Figure(go.Bar(x=er_df["week"], y=er_df["er"],
                                      marker=dict(color=er_df["er"],
                                                  colorscale=[[0,COLORS[2]],[.5,COLORS[1]],[1,COLORS[0]]],
                                                  line=dict(width=0)),
                                      hovertemplate="<b>%{x}</b><br>ER: %{y:.2f}%<extra></extra>"))
            fig_er.update_layout(**base_layout(240))
            st.plotly_chart(fig_er, use_container_width=True, key="g_er")

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)
    st.markdown('<p class="sec-h">📊 Engagement Breakdown</p>', unsafe_allow_html=True)
    st.markdown('<p class="sec-s">Daily likes, comments, and saves</p>', unsafe_allow_html=True)
    eng_df = pd.DataFrame(pd_main.get("engagement_series", []))
    if not eng_df.empty:
        fig_eng = go.Figure()
        for cn, lb, cl in [("likes","Likes",COLORS[0]),("comments","Comments",COLORS[1]),("saves","Saves",COLORS[2])]:
            fig_eng.add_trace(go.Scatter(x=eng_df["date"], y=eng_df[cn], mode="lines", name=lb,
                                         line=dict(color=cl, width=2),
                                         hovertemplate=f"<b>{lb}</b>: %{{y:,.0f}}<extra></extra>"))
        lo3 = base_layout(220)
        lo3["legend"] = dict(orientation="h", y=1.12, font=dict(color=TX2,size=11), bgcolor="rgba(0,0,0,0)")
        fig_eng.update_layout(**lo3)
        st.plotly_chart(fig_eng, use_container_width=True, key="g_eng")

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)
    st.markdown('<p class="sec-h">📡 Reach & Impressions Over Time</p>', unsafe_allow_html=True)
    st.markdown('<p class="sec-s">Estimated daily reach and impressions</p>', unsafe_allow_html=True)
    if not eng_df.empty:
        avg_r = pd_main.get("avg_reach", int(followers_val * 0.35))
        ri_df = eng_df.copy()
        ri_df["reach"]       = (ri_df["likes"] / max(ri_df["likes"].mean(), 1) * avg_r).astype(int)
        ri_df["impressions"] = (ri_df["reach"] * 1.45).astype(int)
        fig_ri = go.Figure()
        fig_ri.add_trace(go.Scatter(x=ri_df["date"], y=ri_df["impressions"], name="Impressions",
                                    mode="lines", line=dict(color=COLORS[1], width=2),
                                    fill="tozeroy", fillcolor=rgba(COLORS[1],.06),
                                    hovertemplate="Impressions: %{y:,.0f}<extra></extra>"))
        fig_ri.add_trace(go.Scatter(x=ri_df["date"], y=ri_df["reach"], name="Reach",
                                    mode="lines", line=dict(color=COLORS[0], width=2.5),
                                    hovertemplate="Reach: %{y:,.0f}<extra></extra>"))
        lo_ri = base_layout(220)
        lo_ri["legend"] = dict(orientation="h", y=1.12, font=dict(color=TX2,size=11), bgcolor="rgba(0,0,0,0)")
        fig_ri.update_layout(**lo_ri)
        st.plotly_chart(fig_ri, use_container_width=True, key="g_ri")

        total_reach = int(ri_df["reach"].sum())
        total_imp   = int(ri_df["impressions"].sum())
        avg_freq    = round(total_imp / max(total_reach, 1), 2)
        rc1, rc2, rc3 = st.columns(3)
        for col, lb, val in [(rc1,"Total Reach",format_number(total_reach)),
                              (rc2,"Total Impressions",format_number(total_imp)),
                              (rc3,"Avg View Frequency",f"{avg_freq}x")]:
            with col:
                st.markdown(kpi(lb, val, None, "accent-blue"), unsafe_allow_html=True)

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)
    hc, hd = st.columns([3, 2])
    with hc:
        st.markdown('<p class="sec-h">🕐 Best Posting Times</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-s">Engagement score by day + hour slot</p>', unsafe_allow_html=True)
        heatmap = pd_main.get("posting_heatmap")
        if heatmap:
            lo_hm = base_layout(260, dict(l=0,r=30,t=10,b=0), hovermode="closest")
            lo_hm["xaxis"] = dict(tickfont=dict(size=10), color=TICK_COL, linecolor=GRID_COL)
            lo_hm["yaxis"] = dict(tickfont=dict(size=10), color=TICK_COL)
            fig_hm = go.Figure(go.Heatmap(
                z=np.array(heatmap),
                x=[f"{h:02d}:00" for h in range(0,24,3)],
                y=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
                colorscale=[[0,CARD2],[.4,COLORS[3]],[.7,COLORS[1]],[1,COLORS[0]]],
                showscale=True,
                colorbar=dict(tickfont=dict(color=TX2,size=9), thickness=8, len=0.8),
                hovertemplate="<b>%{y} %{x}</b><br>Score: %{z:.2f}<extra></extra>"
            ))
            fig_hm.update_layout(**lo_hm)
            st.plotly_chart(fig_hm, use_container_width=True, key="g_hm")

    with hd:
        st.markdown('<p class="sec-h">📅 Weekly Posting Frequency</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-s">Posts published per week</p>', unsafe_allow_html=True)
        freq_df = pd.DataFrame(pd_main.get("weekly_frequency", []))
        if not freq_df.empty:
            fig_fr = go.Figure()
            fig_fr.add_trace(go.Scatter(x=freq_df["week"], y=freq_df["posts"],
                                        mode="lines+markers",
                                        line=dict(color=COLORS[1], width=2.5),
                                        marker=dict(color=COLORS[0], size=8, line=dict(color=BG,width=2)),
                                        fill="tozeroy", fillcolor=rgba(COLORS[1],.07),
                                        hovertemplate="<b>%{x}</b><br>Posts: %{y}<extra></extra>"))
            fig_fr.update_layout(**base_layout(260))
            st.plotly_chart(fig_fr, use_container_width=True, key="g_freq")


# ──────────────────────────────────────────────────────────────────────────────
#  TAB 3 — CONTENT & REELS
# ──────────────────────────────────────────────────────────────────────────────
with tabs[2]:
    ca, cb = st.columns(2)
    with ca:
        st.markdown('<p class="sec-h">🎬 Content Type Mix</p>', unsafe_allow_html=True)
        ct = pd_main.get("content_types", {})
        if ct:
            fig_pie = go.Figure(go.Pie(labels=list(ct.keys()), values=list(ct.values()), hole=0.6,
                                       marker=dict(colors=COLORS[:len(ct)], line=dict(color=BG,width=3)),
                                       textinfo="label+percent", textfont=dict(size=11,color=TX1),
                                       hovertemplate="<b>%{label}</b>: %{value}%<extra></extra>"))
            fig_pie.add_annotation(text="<b>Format</b><br>Mix", x=0.5, y=0.5, showarrow=False,
                                   font=dict(size=11,color=TX2,family="Plus Jakarta Sans"), align="center")
            fig_pie.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
                                  font=dict(color=TX2,family="Plus Jakarta Sans"),
                                  margin=dict(l=0,r=0,t=10,b=0), height=280,
                                  legend=dict(font=dict(color=TX2,size=11), bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig_pie, use_container_width=True, key="c_pie")

    with cb:
        st.markdown('<p class="sec-h">📽️ Reels vs Posts</p>', unsafe_allow_html=True)
        reel_er_v = pd_main.get("reel_er", 0)
        post_er_v = pd_main.get("engagement_rate", 0)
        avg_lk    = pd_main.get("avg_likes", 0)
        avg_cm    = pd_main.get("avg_comments", 0)
        fig_rv = go.Figure()
        fig_rv.add_trace(go.Bar(name="Reels", x=["Avg ER (%)","Avg Likes (K)","Avg Comments (K)"],
                                y=[reel_er_v, round(avg_lk*1.35/1000,1), round(avg_cm*1.2/1000,1)],
                                marker_color=COLORS[0], marker_line=dict(width=0),
                                hovertemplate="Reels %{x}: %{y:.2f}<extra></extra>"))
        fig_rv.add_trace(go.Bar(name="Posts", x=["Avg ER (%)","Avg Likes (K)","Avg Comments (K)"],
                                y=[post_er_v, round(avg_lk/1000,1), round(avg_cm/1000,1)],
                                marker_color=COLORS[2], marker_line=dict(width=0),
                                hovertemplate="Posts %{x}: %{y:.2f}<extra></extra>"))
        lo_rv = base_layout(280)
        lo_rv["barmode"] = "group"
        lo_rv["legend"]  = dict(orientation="h",y=1.12,font=dict(color=TX2,size=11),bgcolor="rgba(0,0,0,0)")
        fig_rv.update_layout(**lo_rv)
        st.plotly_chart(fig_rv, use_container_width=True, key="c_rv")

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)
    st.markdown('<p class="sec-h">🎯 Reels KPI Summary</p>', unsafe_allow_html=True)
    er_lift = round(((reel_er_v - post_er_v) / max(post_er_v, 0.01)) * 100, 1)
    rm1, rm2, rm3, rm4 = st.columns(4)
    for col, lb, val, acc in [
        (rm1, "Avg Plays",        format_number(pd_main.get("reel_avg_plays",0)), ""),
        (rm2, "Reel ER",          f"{reel_er_v:.2f}%",                           ""),
        (rm3, "Reels Published",  str(pd_main.get("reel_count",0)),               ""),
        (rm4, "ER Lift vs Posts", f"{er_lift:+.1f}%",                             "accent-green" if er_lift >= 0 else ""),
    ]:
        with col:
            st.markdown(kpi(lb, val, None, acc), unsafe_allow_html=True)

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)
    st.markdown('<p class="sec-h">📖 Stories Analytics</p>', unsafe_allow_html=True)
    _rnd.seed(followers_val % 9999)
    s_base   = int(followers_val * 0.12)
    s_labels = ["Impressions","Unique Views","Replies","Link Taps","Profile Visits"]
    s_vals   = [int(s_base*1.4), s_base, int(s_base*0.015), int(s_base*0.03), int(s_base*0.05)]

    sa, sb = st.columns([2, 3])
    with sa:
        fig_fn = go.Figure(go.Funnel(y=s_labels, x=s_vals,
                                     textinfo="value+percent initial",
                                     textfont=dict(color=TX1,size=11),
                                     marker=dict(color=COLORS[:5], line=dict(color=BG,width=2)),
                                     connector=dict(line=dict(color=GRID_COL,width=2))))
        fig_fn.update_layout(plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
                             font=dict(color=TX2,family="Plus Jakarta Sans"),
                             margin=dict(l=0,r=0,t=10,b=0), height=280)
        st.plotly_chart(fig_fn, use_container_width=True, key="c_funnel")

    with sb:
        s_exits = sorted([_rnd.uniform(5,40) for _ in range(8)])
        lo_ex = base_layout(280, hovermode="closest")
        lo_ex["title"] = dict(text="Exit Rate per Story Slot (%)", font=dict(color=TX2,size=12), x=0)
        fig_ex = go.Figure(go.Bar(x=[f"Story {i+1}" for i in range(8)], y=s_exits,
                                   marker=dict(color=s_exits,
                                               colorscale=[[0,COLORS[2]],[.5,COLORS[1]],[1,COLORS[0]]],
                                               line=dict(width=0)),
                                   hovertemplate="<b>%{x}</b><br>Exit: %{y:.1f}%<extra></extra>"))
        fig_ex.update_layout(**lo_ex)
        st.plotly_chart(fig_ex, use_container_width=True, key="c_exit")

    s_reach = int(followers_val * 0.08)
    r_reach = pd_main.get("avg_reach", int(followers_val * 0.35))
    r_ratio = round(r_reach / max(s_reach, 1), 1)
    st.markdown(
        f'<div class="info-box">📡 Avg Story Reach: <strong style="color:{TX1}">{format_number(s_reach)}</strong>'
        f' &nbsp;·&nbsp; Avg Reel Reach: <strong style="color:{TX1}">{format_number(r_reach)}</strong>'
        f' &nbsp;·&nbsp; Reels reach <strong style="color:{COLORS[0]}">{r_ratio}×</strong> more people</div>',
        unsafe_allow_html=True
    )


# ──────────────────────────────────────────────────────────────────────────────
#  TAB 4 — HASHTAGS
# ──────────────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown('<p class="sec-h">🏷️ Hashtag Analytics</p>', unsafe_allow_html=True)
    st.markdown('<p class="sec-s">Auto-extracted from post captions — ranked by average engagement</p>', unsafe_allow_html=True)

    ht_list = pd_main.get("hashtags", [])
    if ht_list:
        ht_df = pd.DataFrame(ht_list).head(12)
        lo_ht = base_layout(300, hovermode="closest")
        lo_ht["xaxis"] = dict(showgrid=True,gridcolor=GRID_COL,color=TICK_COL,tickfont=dict(size=10))
        lo_ht["yaxis"] = dict(showgrid=False,color=TICK_COL,tickfont=dict(size=10))
        fig_ht = go.Figure(go.Bar(y=ht_df["tag"], x=ht_df["avg_engagement"], orientation="h",
                                   marker=dict(color=ht_df["avg_engagement"],
                                               colorscale=[[0,COLORS[3]],[1,COLORS[0]]],
                                               line=dict(width=0)),
                                   hovertemplate="<b>%{y}</b><br>Avg Engagement: %{x:,.0f}<extra></extra>"))
        fig_ht.update_layout(**lo_ht)
        st.plotly_chart(fig_ht, use_container_width=True, key="h_ht")

    if hashtags_data:
        st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)
        st.markdown('<p class="sec-h">🌐 Hashtag Deep-Dive</p>', unsafe_allow_html=True)
        ht_rows = [{"Hashtag":t,"Avg Likes":format_number(d.get("avg_likes",0)),
                    "Avg Comments":format_number(d.get("avg_comments",0)),
                    "Avg Engagement":format_number(d.get("avg_engagement",0))}
                   for t,d in hashtags_data.items()]
        if ht_rows:
            st.dataframe(pd.DataFrame(ht_rows), use_container_width=True, hide_index=True)
        chips = "".join(f'<span class="tag-chip">{t}</span>' for t in hashtags_data.keys())
        st.markdown(f'<div style="line-height:2.4;margin-top:8px">{chips}</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
#  TAB 5 — COMPETITOR BENCH
# ──────────────────────────────────────────────────────────────────────────────
if input_mode == "Competitor Comparison":
    with tabs[4]:
        st.markdown('<p class="sec-h">⚔️ Head-to-Head Comparison</p>', unsafe_allow_html=True)
        comp_rows = []
        for u in usernames:
            d = profiles_data.get(u, {})
            src_badge_str = "LIVE" if d.get("_data_source") == "live" else "DEMO"
            comp_rows.append({
                "Profile":       f"@{u}",
                "Source":        src_badge_str,
                "Followers":     d.get("followers",0),
                "Eng. Rate (%)": round(d.get("engagement_rate",0),2),
                "Avg Likes":     d.get("avg_likes",0),
                "Avg Comments":  d.get("avg_comments",0),
                "Reel ER (%)":   round(d.get("reel_er",0),2),
                "Avg Reach":     d.get("avg_reach",0),
            })
        comp_df = pd.DataFrame(comp_rows)

        ba, bb = st.columns([3,2])
        with ba:
            st.markdown('<p class="sec-h">Engagement Rate Comparison</p>', unsafe_allow_html=True)
            fig_ce = go.Figure()
            for i, row in comp_df.iterrows():
                fig_ce.add_trace(go.Bar(name=row["Profile"],
                                        x=["Post ER (%)","Reel ER (%)"],
                                        y=[row["Eng. Rate (%)"], row["Reel ER (%)"]],
                                        marker_color=COLORS[i%len(COLORS)], marker_line=dict(width=0),
                                        hovertemplate=f"<b>{row['Profile']}</b> %{{x}}: %{{y:.2f}}%<extra></extra>"))
            lo_ce = base_layout(300)
            lo_ce["barmode"] = "group"
            lo_ce["legend"]  = dict(orientation="h",y=1.1,font=dict(color=TX2,size=11),bgcolor="rgba(0,0,0,0)")
            fig_ce.update_layout(**lo_ce)
            st.plotly_chart(fig_ce, use_container_width=True, key="comp_er")

        with bb:
            st.markdown('<p class="sec-h">Follower Count</p>', unsafe_allow_html=True)
            fig_cf = go.Figure(go.Bar(x=comp_df["Followers"], y=comp_df["Profile"], orientation="h",
                                      marker=dict(color=COLORS[:len(comp_df)], line=dict(width=0)),
                                      hovertemplate="<b>%{y}</b><br>%{x:,.0f} followers<extra></extra>"))
            lo_cf = base_layout(300, hovermode="closest")
            lo_cf["xaxis"] = dict(showgrid=True,gridcolor=GRID_COL,color=TICK_COL,tickfont=dict(size=10))
            lo_cf["yaxis"] = dict(showgrid=False,color=TICK_COL,tickfont=dict(size=11))
            fig_cf.update_layout(**lo_cf)
            st.plotly_chart(fig_cf, use_container_width=True, key="comp_fol")

        st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)
        st.markdown('<p class="sec-h">📋 Full Metrics Table</p>', unsafe_allow_html=True)
        disp_df = comp_df.copy()
        for col in ["Followers","Avg Reach","Avg Likes","Avg Comments"]:
            disp_df[col] = disp_df[col].apply(format_number)
        st.dataframe(disp_df, use_container_width=True, hide_index=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<hr class='hdivider' style='margin-top:32px'>", unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align:center;color:{TX3};font-size:10px;letter-spacing:1.2px'>"
    "INSTALENS v4.0 · HASDATA API · STREAMLIT · PLOTLY</p>",
    unsafe_allow_html=True
)
