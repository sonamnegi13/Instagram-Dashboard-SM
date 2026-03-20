import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import random as _rnd
from datetime import datetime, timedelta
from data_fetcher import HasDataFetcher, generate_mock_data
from utils import format_number, calculate_engagement_rate, benchmark_er, rate_engagement

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="InstaLens · Analytics",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design tokens ─────────────────────────────────────────────────────────────
# Background layers
BG_BASE   = "#07070f"   # page background
BG_CARD   = "#0f0f1c"   # card fill
BG_CARD2  = "#141428"   # slightly lighter card
BG_RAISED = "#191932"   # elevated surface

# Text
TX_PRIMARY   = "#eeeaf8"   # headings / large numbers
TX_SECONDARY = "#9896b4"   # body / labels
TX_MUTED     = "#5c5a78"   # hints / captions

# Accent
AC_PINK   = "#f72585"
AC_PURPLE = "#7209b7"
AC_VIOLET = "#b5179e"
AC_CYAN   = "#06d6e0"
AC_GREEN  = "#4ade80"
AC_RED    = "#f87171"
AC_AMBER  = "#fbbf24"

# Chart
CHART_BG = "rgba(0,0,0,0)"
GRID_COL = "#1c1c34"
TICK_COL = "#3e3c5a"
FONT_COL = TX_SECONDARY

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Inter:wght@300;400;500;600&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    font-size: 14px;
}}
.stApp {{ background: {BG_BASE}; color: {TX_PRIMARY}; }}
.block-container {{ padding-top: 1.4rem !important; padding-bottom: 2rem !important; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: #0b0b18 !important;
    border-right: 1px solid #1c1c34;
}}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div {{ color: #a8a6c8 !important; }}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea {{
    background: #111124 !important;
    color: {TX_PRIMARY} !important;
    border: 1px solid #282848 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}}
[data-testid="stSidebar"] .stTextInput input:focus,
[data-testid="stSidebar"] .stTextArea textarea:focus {{
    border-color: {AC_PINK} !important;
    box-shadow: 0 0 0 2px rgba(247,37,133,0.15) !important;
}}

/* ── Brand ── */
.brand {{
    font-family: 'Syne', sans-serif;
    font-size: 22px; font-weight: 800;
    background: linear-gradient(135deg, {AC_PINK}, {AC_VIOLET}, {AC_PURPLE});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; letter-spacing: -0.5px;
}}
.brand-sub {{
    font-size: 9px; color: {TX_MUTED};
    letter-spacing: 3px; text-transform: uppercase;
    margin-top: -2px;
}}

/* ── Tabs ── */
div[data-testid="stTabs"] button {{
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    color: {TX_MUTED} !important;
    padding: 8px 16px !important;
}}
div[data-testid="stTabs"] button[aria-selected="true"] {{
    color: {TX_PRIMARY} !important;
    border-bottom-color: {AC_PINK} !important;
}}

/* ── KPI cards ── */
.kpi-wrap {{
    background: {BG_CARD};
    border: 1px solid #1e1e3a;
    border-radius: 14px;
    padding: 16px 18px 14px;
    position: relative;
    overflow: hidden;
    height: 100%;
    min-height: 110px;
}}
.kpi-wrap::after {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, {AC_PINK}, {AC_PURPLE});
}}
.kpi-accent-blue::after  {{ background: linear-gradient(90deg, {AC_CYAN}, #0096c7); }}
.kpi-accent-green::after {{ background: linear-gradient(90deg, {AC_GREEN}, #16a34a); }}
.kpi-accent-amber::after {{ background: linear-gradient(90deg, {AC_AMBER}, #d97706); }}

.kpi-label {{
    font-size: 10px; font-weight: 600;
    letter-spacing: 1.5px; text-transform: uppercase;
    color: {TX_MUTED}; margin-bottom: 8px;
    line-height: 1.3;
}}
.kpi-value {{
    font-family: 'Syne', sans-serif;
    font-size: 26px; font-weight: 800;
    color: {TX_PRIMARY}; line-height: 1.1;
    margin-bottom: 6px;
    word-break: break-word;
    max-width: 100%;
}}
.kpi-value-sm {{
    font-family: 'Syne', sans-serif;
    font-size: 18px; font-weight: 700;
    color: {TX_PRIMARY}; line-height: 1.2;
    margin-bottom: 6px;
    word-break: break-word;
}}
.kpi-delta-pos {{ font-size: 11px; color: {AC_GREEN}; font-weight: 500; }}
.kpi-delta-neg {{ font-size: 11px; color: {AC_RED};   font-weight: 500; }}
.kpi-icon {{
    position: absolute; bottom: 12px; right: 14px;
    font-size: 22px; opacity: 0.10; pointer-events: none;
    line-height: 1;
}}

/* ── Section headings ── */
.sec-head {{
    font-family: 'Syne', sans-serif;
    font-size: 14px; font-weight: 700;
    color: {TX_PRIMARY}; margin: 0 0 2px;
    letter-spacing: -0.1px;
}}
.sec-sub {{
    font-size: 11px; color: {TX_MUTED};
    margin-bottom: 12px; line-height: 1.4;
}}

/* ── Profile hero ── */
.profile-hero {{
    background: linear-gradient(135deg, #0f0f22, #180f30);
    border: 1px solid #28184a;
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 20px;
}}
.profile-name {{
    font-family: 'Syne', sans-serif;
    font-size: 22px; font-weight: 800;
    color: {TX_PRIMARY}; margin-bottom: 4px;
}}
.profile-bio {{
    font-size: 12px; color: {TX_SECONDARY};
    line-height: 1.5; margin-bottom: 12px;
    max-width: 700px;
}}
.pill {{
    display: inline-block;
    background: rgba(114,9,183,0.15);
    border: 1px solid rgba(181,23,158,0.3);
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 11px; font-weight: 500;
    color: #d8b4fe;
    margin-right: 8px; margin-top: 4px;
}}

/* ── Post cards ── */
.post-card {{
    background: {BG_CARD};
    border: 1px solid #1c1c38;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}}
.post-badge {{
    display: inline-block;
    background: linear-gradient(135deg, {AC_PINK}, {AC_PURPLE});
    color: #fff;
    font-size: 9px; font-weight: 700;
    padding: 2px 9px; border-radius: 20px;
    letter-spacing: 1px; text-transform: uppercase;
    width: fit-content;
}}
.post-caption {{
    font-size: 12px; color: {TX_SECONDARY};
    line-height: 1.5;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}}
.post-stats-row {{
    display: flex; gap: 14px; align-items: center; flex-wrap: wrap;
}}
.post-stat {{
    font-size: 11px; color: {TX_MUTED};
    display: flex; align-items: center; gap: 3px;
}}
.post-stat strong {{ color: {TX_PRIMARY}; font-weight: 600; }}
.post-er {{
    font-size: 10px; color: {TX_MUTED};
    margin-top: 2px;
}}

/* ── Tag chips ── */
.tag-chip {{
    display: inline-block;
    background: rgba(99,91,255,0.12);
    border: 1px solid rgba(99,91,255,0.25);
    border-radius: 20px;
    padding: 3px 11px; margin: 3px;
    font-size: 11px; color: #c4b5fd;
}}

/* ── Alert pills ── */
.pill-info {{
    background: rgba(114,9,183,0.1);
    border: 1px solid rgba(114,9,183,0.28);
    border-radius: 8px; padding: 9px 14px;
    font-size: 12px; color: #c4b5fd;
    line-height: 1.5;
}}
.pill-warn {{
    background: rgba(251,191,36,0.08);
    border: 1px solid rgba(251,191,36,0.28);
    border-radius: 8px; padding: 9px 14px;
    font-size: 12px; color: #fde68a;
    line-height: 1.5;
}}
.pill-success {{
    background: rgba(74,222,128,0.08);
    border: 1px solid rgba(74,222,128,0.28);
    border-radius: 8px; padding: 9px 14px;
    font-size: 12px; color: #86efac;
    line-height: 1.5;
}}

/* ── Divider ── */
.hdivider {{
    border: none; border-top: 1px solid #1c1c34;
    margin: 20px 0;
}}

/* ── Bench table ── */
[data-testid="stDataFrame"] {{
    border: 1px solid #1c1c34 !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: {BG_BASE}; }}
::-webkit-scrollbar-thumb {{ background: #2a2a48; border-radius: 4px; }}
</style>
""", unsafe_allow_html=True)


# ── Chart helper ──────────────────────────────────────────────────────────────
def base_layout(h=240, margin=None, hovermode="x unified"):
    """Return a clean Plotly layout dict. hovermode is explicit — never duplicated."""
    m = margin or dict(l=0, r=0, t=10, b=0)
    return dict(
        plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
        font=dict(color=FONT_COL, family="Inter"),
        margin=m, height=h,
        xaxis=dict(showgrid=False, color=TICK_COL, tickfont=dict(size=10), linecolor=GRID_COL),
        yaxis=dict(showgrid=True, gridcolor=GRID_COL, color=TICK_COL, tickfont=dict(size=10)),
        hovermode=hovermode,
    )

def hex_rgb(h):
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)

def rgba(h, a):
    r, g, b = hex_rgb(h)
    return f"rgba({r},{g},{b},{a})"

def kpi_card(label, value, delta=None, icon="", accent="", small=False):
    """Render a consistent KPI card. value must already be a string."""
    delta_html = ""
    if delta is not None:
        dclass = "kpi-delta-pos" if delta >= 0 else "kpi-delta-neg"
        darrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<div class="{dclass}">{darrow} {abs(delta):.1f}% vs prev period</div>'
    val_class = "kpi-value-sm" if small else "kpi-value"
    return f"""
    <div class="kpi-wrap {accent}">
        <div class="kpi-label">{label}</div>
        <div class="{val_class}">{value}</div>
        {delta_html}
        <div class="kpi-icon">{icon}</div>
    </div>"""


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="brand">📸 InstaLens</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Social Analytics Platform</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Data source
    st.markdown("**🔌 Data Source**")
    use_mock = st.toggle("Demo Mode (no API key needed)", value=True)
    if not use_mock:
        api_key = st.text_input("HasData API Key", type="password",
                                placeholder="hd_xxxxxxxxxxxxxxxx",
                                help="Get your key at hasdata.com")
        if api_key:
            st.markdown('<div class="pill-success">✅ API key saved — live data active</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="pill-warn">⚠️ Enter your key to fetch live data</div>', unsafe_allow_html=True)
    else:
        api_key = None
        st.markdown('<div class="pill-info">🎭 Realistic mock data.<br>Disable to go live.</div>', unsafe_allow_html=True)

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # Input mode
    st.markdown("**📥 Input Mode**")
    input_mode = st.radio(
        "Input Mode",
        ["Single Profile", "Competitor Comparison", "Hashtag Tracking"],
        label_visibility="collapsed"
    )

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # Profile inputs
    if input_mode == "Single Profile":
        st.markdown("**👤 Profile**")
        single_user = st.text_input("Username", value="natgeo", placeholder="e.g. natgeo")
        usernames = [single_user.strip().lstrip("@")] if single_user.strip() else ["natgeo"]

    elif input_mode == "Competitor Comparison":
        st.markdown("**⚔️ Profiles (max 3)**")
        profiles_raw = st.text_area("One username per line",
                                    value="natgeo\nbbc\ntime",
                                    height=95, help="No @ needed")
        usernames = [u.strip().lstrip("@") for u in profiles_raw.split("\n") if u.strip()][:3]
        if len(usernames) < 2:
            st.markdown('<div class="pill-warn">⚠️ Add at least 2 profiles.</div>', unsafe_allow_html=True)
        else:
            st.caption(f"{len(usernames)} / 3 profiles loaded.")

    else:  # Hashtag Tracking
        st.markdown("**👤 Profile to analyse**")
        anchor_user = st.text_input("Username", value="natgeo", placeholder="e.g. natgeo")
        usernames = [anchor_user.strip().lstrip("@")] if anchor_user.strip() else ["natgeo"]
        st.markdown('<div class="pill-info">🔍 Hashtags are auto-extracted from post captions.</div>', unsafe_allow_html=True)

    manual_hashtags = None

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # Options
    st.markdown("**📅 Date Range**")
    date_range = st.selectbox("Date Range", ["Last 7 days", "Last 30 days", "Last 90 days"],
                              index=1, label_visibility="collapsed")
    days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}[date_range]

    st.markdown("**🎨 Chart Style**")
    scheme = st.selectbox("Chart Colors", ["Magenta / Violet", "Cyan / Teal", "Amber / Gold"],
                          label_visibility="collapsed")
    COLORS = {
        "Magenta / Violet": [AC_PINK,  "#b5179e", AC_PURPLE, "#560bad", "#3a0ca3"],
        "Cyan / Teal":      [AC_CYAN,  "#00bbf9", "#0096c7", "#0077b6", "#023e8a"],
        "Amber / Gold":     [AC_AMBER, "#fb5607", "#ff006e", "#8338ec", "#3a86ff"],
    }[scheme]

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.button("🚀 Analyse", use_container_width=True, type="primary")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.caption("InstaLens v3.1 · HasData API · Streamlit")


# ══════════════════════════════════════════════════════════════════════════════
#  DATA LOAD
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def load_data(usernames, api_key, days, use_mock, manual_hashtags):
    ht = list(manual_hashtags) if manual_hashtags else None
    if use_mock or not api_key:
        return generate_mock_data(list(usernames), days, ht)
    fetcher = HasDataFetcher(api_key)
    return fetcher.fetch_all(list(usernames), days, ht)

with st.spinner("🔍 Fetching & processing data…"):
    raw = load_data(tuple(usernames), api_key, days, use_mock, tuple(manual_hashtags or []))

profiles_data = raw.get("profiles", {})
hashtags_data = raw.get("hashtags", {})
for u in usernames:
    if u not in profiles_data:
        profiles_data[u] = {}


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
h_left, h_right = st.columns([5, 1])
with h_left:
    icons = {"Single Profile": "👤", "Competitor Comparison": "⚔️", "Hashtag Tracking": "🏷️"}
    st.markdown(
        f"<h1 style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;"
        f"color:{TX_PRIMARY};margin:0;letter-spacing:-0.5px'>"
        f"{icons[input_mode]} {input_mode} Report</h1>",
        unsafe_allow_html=True
    )
    profiles_str = " · ".join(f"@{u}" for u in usernames)
    st.markdown(
        f"<p style='color:{TX_MUTED};font-size:12px;margin-top:4px'>"
        f"{profiles_str} · {date_range} · {datetime.now().strftime('%b %d, %Y %H:%M')}</p>",
        unsafe_allow_html=True
    )
with h_right:
    if not use_mock and api_key:
        st.markdown('<div class="pill-success" style="text-align:center;margin-top:10px">✅ LIVE</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="pill-warn" style="text-align:center;margin-top:10px">🎭 DEMO</div>', unsafe_allow_html=True)

st.markdown("<hr class='hdivider' style='margin:12px 0 18px'>", unsafe_allow_html=True)

# Profile selector
if input_mode == "Competitor Comparison" and len(usernames) > 1:
    selected = st.selectbox("🔍 Deep-dive into:", usernames, format_func=lambda x: f"@{x}")
else:
    selected = usernames[0] if usernames else "natgeo"

pd_main = profiles_data.get(selected, {})


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

    # Profile hero card
    verified = " ✅" if pd_main.get("verified") else ""
    bio      = pd_main.get("bio", "")[:130]
    st.markdown(f"""
    <div class="profile-hero">
        <div class="profile-name">@{selected}{verified}</div>
        <div class="profile-bio">{bio}</div>
        <div>
            <span class="pill">👥 {format_number(pd_main.get("followers",0))} followers</span>
            <span class="pill">➡️ {format_number(pd_main.get("following",0))} following</span>
            <span class="pill">📝 {format_number(pd_main.get("total_posts",0))} posts</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Row 1: Core KPIs ──────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    core_kpis = [
        (c1, "Followers",         format_number(pd_main.get("followers",0)),
             pd_main.get("followers_delta",0), "👥", ""),
        (c2, "Engagement Rate",   f"{pd_main.get('engagement_rate',0):.2f}%",
             pd_main.get("er_delta",0), "💬", ""),
        (c3, "Avg Reach / Post",  format_number(pd_main.get("avg_reach",0)),
             pd_main.get("reach_delta",0), "📡", ""),
        (c4, "Total Impressions", format_number(pd_main.get("total_impressions",0)),
             pd_main.get("imp_delta",0), "👁️", ""),
        (c5, "Avg Likes",         format_number(pd_main.get("avg_likes",0)),
             None, "❤️", ""),
    ]
    for col, label, value, delta, icon, accent in core_kpis:
        with col:
            st.markdown(kpi_card(label, value, delta, icon, accent), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Row 2: Reels KPIs ─────────────────────────────────────────────────────
    st.markdown('<p class="sec-head" style="margin-bottom:10px">🎬 Reels at a Glance</p>', unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4)
    er_bench_str = rate_engagement(pd_main.get("engagement_rate", 0))
    reels_kpis = [
        (r1, "Reel Avg Plays",    format_number(pd_main.get("reel_avg_plays",0)),    None, "▶️",  ""),
        (r2, "Reel Eng. Rate",    f"{pd_main.get('reel_er',0):.2f}%",               None, "🎬",  ""),
        (r3, "Reels This Period", str(pd_main.get("reel_count",0)),                  None, "📽️", ""),
        (r4, "ER Benchmark",      er_bench_str,                                      None, "📊",  ""),
    ]
    for col, label, value, delta, icon, accent in reels_kpis:
        with col:
            # Use smaller font for longer string values
            is_small = len(str(value)) > 8
            st.markdown(kpi_card(label, value, delta, icon, accent, small=is_small),
                        unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Row 3: Stories KPIs ───────────────────────────────────────────────────
    st.markdown('<p class="sec-head" style="margin-bottom:10px">📖 Stories at a Glance</p>', unsafe_allow_html=True)
    followers_val   = max(pd_main.get("followers", 1), 1)
    story_views     = int(followers_val * 0.08)
    story_replies   = int(story_views * 0.012)
    story_exit_rate = min(round(25 + (100 / max(followers_val / 1e6, 0.01)) * 0.5, 1), 65.0)
    story_link_taps = int(story_views * 0.03)

    s1, s2, s3, s4 = st.columns(4)
    stories_kpis = [
        (s1, "Avg Story Views",   format_number(story_views),     None, "📖", "kpi-accent-blue"),
        (s2, "Story Replies",     format_number(story_replies),   None, "💌", "kpi-accent-blue"),
        (s3, "Exit Rate",         f"{story_exit_rate}%",          None, "🚪", "kpi-accent-blue"),
        (s4, "Link Tap-Throughs", format_number(story_link_taps), None, "🔗", "kpi-accent-blue"),
    ]
    for col, label, value, delta, icon, accent in stories_kpis:
        with col:
            st.markdown(kpi_card(label, value, delta, icon, accent), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── ER Benchmark banner ───────────────────────────────────────────────────
    er_val   = pd_main.get("engagement_rate", 0)
    bench    = benchmark_er(followers_val, er_val)
    if "▲" in bench:
        bclass, bcolor = "pill-success", AC_GREEN
    elif "≈" in bench:
        bclass, bcolor = "pill-warn", AC_AMBER
    else:
        bclass, bcolor = "pill-warn", AC_RED
    st.markdown(
        f'<div class="{bclass}">📐 <strong>ER Benchmark:</strong> {bench} &nbsp;·&nbsp; {rate_engagement(er_val)}</div>',
        unsafe_allow_html=True
    )

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # ── Top Posts ─────────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">🏆 Top Posts This Period</p>', unsafe_allow_html=True)
    st.markdown('<p class="sec-sub">Ranked by total likes in the selected period</p>', unsafe_allow_html=True)

    top_posts = pd_main.get("top_posts", [])
    if top_posts:
        pc = st.columns(3)
        for i, post in enumerate(top_posts[:6]):
            with pc[i % 3]:
                caption  = post.get("caption", "No caption available.")
                ptype    = post.get("type", "POST")
                likes    = format_number(post.get("likes", 0))
                comments = format_number(post.get("comments", 0))
                saves    = format_number(post.get("saves", 0))
                er_pct   = f"{post.get('engagement_rate', 0):.2f}%"
                date_str = post.get("date", "")
                url      = post.get("url", "")
                link_html = f'<a href="{url}" target="_blank" style="color:{AC_PURPLE};font-size:10px;text-decoration:none">🔗 View</a>' if url else ""

                # Build post card cleanly — no nested f-strings with quotes
                card_html = (
                    '<div class="post-card">'
                    f'<div class="post-badge">{ptype}</div>'
                    f'<div class="post-caption">{caption}</div>'
                    '<div class="post-stats-row">'
                    f'<span class="post-stat">❤️ <strong>{likes}</strong></span>'
                    f'<span class="post-stat">💬 <strong>{comments}</strong></span>'
                    f'<span class="post-stat">🔖 <strong>{saves}</strong></span>'
                    '</div>'
                    f'<div class="post-er">{date_str} · ER <strong style="color:{COLORS[0]}">{er_pct}</strong> {link_html}</div>'
                    '</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
#  TAB 2 — GROWTH & ENGAGEMENT
# ──────────────────────────────────────────────────────────────────────────────
with tabs[1]:

    # Follower growth + ER side by side
    ga, gb = st.columns([3, 2])
    with ga:
        st.markdown('<p class="sec-head">📈 Follower Growth</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-sub">Daily follower count over the period</p>', unsafe_allow_html=True)
        growth_df = pd.DataFrame(pd_main.get("growth_series", []))
        if not growth_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=growth_df["date"], y=growth_df["followers"],
                mode="lines", line=dict(color=COLORS[0], width=2.5),
                fill="tozeroy", fillcolor=rgba(COLORS[0], .07),
                hovertemplate="<b>%{x}</b><br>%{y:,.0f} followers<extra></extra>"
            ))
            fig.update_layout(**base_layout(240))
            st.plotly_chart(fig, use_container_width=True, key="fig_growth")

    with gb:
        st.markdown('<p class="sec-head">💬 Weekly Engagement Rate</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-sub">Average ER (%) per week</p>', unsafe_allow_html=True)
        er_df = pd.DataFrame(pd_main.get("er_series", []))
        if not er_df.empty:
            fig2 = go.Figure(go.Bar(
                x=er_df["week"], y=er_df["er"],
                marker=dict(
                    color=er_df["er"],
                    colorscale=[[0, COLORS[2]], [.5, COLORS[1]], [1, COLORS[0]]],
                    line=dict(width=0)
                ),
                hovertemplate="<b>%{x}</b><br>ER: %{y:.2f}%<extra></extra>"
            ))
            fig2.update_layout(**base_layout(240))
            st.plotly_chart(fig2, use_container_width=True, key="fig_er")

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # Engagement breakdown
    st.markdown('<p class="sec-head">📊 Engagement Breakdown Over Time</p>', unsafe_allow_html=True)
    st.markdown('<p class="sec-sub">Daily likes, comments, and saves</p>', unsafe_allow_html=True)
    eng_df = pd.DataFrame(pd_main.get("engagement_series", []))
    if not eng_df.empty:
        fig3 = go.Figure()
        for col_name, label, color in [("likes","Likes",COLORS[0]),
                                        ("comments","Comments",COLORS[1]),
                                        ("saves","Saves",COLORS[2])]:
            fig3.add_trace(go.Scatter(
                x=eng_df["date"], y=eng_df[col_name],
                mode="lines", name=label, line=dict(color=color, width=2),
                hovertemplate=f"<b>{label}</b>: %{{y:,.0f}}<extra></extra>"
            ))
        lo3 = base_layout(220)
        lo3["legend"] = dict(orientation="h", y=1.12,
                             font=dict(color=FONT_COL, size=11), bgcolor="rgba(0,0,0,0)")
        fig3.update_layout(**lo3)
        st.plotly_chart(fig3, use_container_width=True, key="fig_eng")

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # ── Reach & Impressions ───────────────────────────────────────────────────
    st.markdown('<p class="sec-head">📡 Reach & Impressions Over Time</p>', unsafe_allow_html=True)
    st.markdown('<p class="sec-sub">Estimated reach and impressions per day (derived from engagement)</p>', unsafe_allow_html=True)

    if not eng_df.empty:
        avg_r    = pd_main.get("avg_reach", int(followers_val * 0.35))
        ri_df    = eng_df.copy()
        _rnd.seed(42)
        ri_df["reach"]       = (ri_df["likes"] / max(ri_df["likes"].mean(), 1) * avg_r).astype(int)
        ri_df["impressions"] = (ri_df["reach"] * 1.45).astype(int)

        fig_ri = go.Figure()
        fig_ri.add_trace(go.Scatter(
            x=ri_df["date"], y=ri_df["impressions"],
            name="Impressions", mode="lines",
            line=dict(color=COLORS[1], width=2),
            fill="tozeroy", fillcolor=rgba(COLORS[1], .06),
            hovertemplate="<b>%{x}</b><br>Impressions: %{y:,.0f}<extra></extra>"
        ))
        fig_ri.add_trace(go.Scatter(
            x=ri_df["date"], y=ri_df["reach"],
            name="Reach", mode="lines",
            line=dict(color=COLORS[0], width=2.5),
            hovertemplate="<b>%{x}</b><br>Reach: %{y:,.0f}<extra></extra>"
        ))
        lo_ri = base_layout(220)
        lo_ri["legend"] = dict(orientation="h", y=1.12,
                               font=dict(color=FONT_COL, size=11), bgcolor="rgba(0,0,0,0)")
        fig_ri.update_layout(**lo_ri)
        st.plotly_chart(fig_ri, use_container_width=True, key="fig_ri")

        # Reach summary pills
        total_reach = int(ri_df["reach"].sum())
        total_imp   = int(ri_df["impressions"].sum())
        avg_freq    = round(total_imp / max(total_reach, 1), 2)
        rc1, rc2, rc3 = st.columns(3)
        for col, label, val, icon in [
            (rc1, "Total Reach",        format_number(total_reach), "📡"),
            (rc2, "Total Impressions",  format_number(total_imp),   "👁️"),
            (rc3, "Avg View Frequency", f"{avg_freq}×",             "🔁"),
        ]:
            with col:
                st.markdown(kpi_card(label, val, None, icon, "kpi-accent-blue"), unsafe_allow_html=True)

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # Heatmap + Frequency
    hc, hd = st.columns([3, 2])
    with hc:
        st.markdown('<p class="sec-head">🕐 Best Posting Times</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-sub">Engagement score by day × hour slot (higher = better)</p>', unsafe_allow_html=True)
        heatmap = pd_main.get("posting_heatmap")
        if heatmap:
            hours        = [f"{h:02d}:00" for h in range(0, 24, 3)]
            days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            # FIX: build layout dict separately to avoid duplicate key error
            lo_hm = base_layout(260, dict(l=0, r=30, t=10, b=0), hovermode="closest")
            lo_hm["xaxis"] = dict(tickfont=dict(size=10), color=TICK_COL, linecolor=GRID_COL)
            lo_hm["yaxis"] = dict(tickfont=dict(size=10), color=TICK_COL)
            fig4 = go.Figure(go.Heatmap(
                z=np.array(heatmap), x=hours, y=days_of_week,
                colorscale=[[0, BG_CARD2], [.4, COLORS[3]], [.7, COLORS[1]], [1, COLORS[0]]],
                showscale=True,
                colorbar=dict(tickfont=dict(color=FONT_COL, size=9), thickness=8, len=0.8),
                hovertemplate="<b>%{y} %{x}</b><br>Score: %{z:.2f}<extra></extra>"
            ))
            fig4.update_layout(**lo_hm)
            st.plotly_chart(fig4, use_container_width=True, key="fig_heatmap")

    with hd:
        st.markdown('<p class="sec-head">📅 Weekly Posting Frequency</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-sub">Posts published per week</p>', unsafe_allow_html=True)
        freq_df = pd.DataFrame(pd_main.get("weekly_frequency", []))
        if not freq_df.empty:
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(
                x=freq_df["week"], y=freq_df["posts"],
                mode="lines+markers",
                line=dict(color=COLORS[1], width=2.5),
                marker=dict(color=COLORS[0], size=8, line=dict(color=BG_BASE, width=2)),
                fill="tozeroy", fillcolor=rgba(COLORS[1], .07),
                hovertemplate="<b>%{x}</b><br>Posts: %{y}<extra></extra>"
            ))
            fig5.update_layout(**base_layout(260))
            st.plotly_chart(fig5, use_container_width=True, key="fig_freq")


# ──────────────────────────────────────────────────────────────────────────────
#  TAB 3 — CONTENT & REELS
# ──────────────────────────────────────────────────────────────────────────────
with tabs[2]:
    ca, cb = st.columns(2)

    with ca:
        st.markdown('<p class="sec-head">🎬 Content Type Mix</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-sub">Share of post formats in this period</p>', unsafe_allow_html=True)
        ct = pd_main.get("content_types", {})
        if ct:
            fig6 = go.Figure(go.Pie(
                labels=list(ct.keys()), values=list(ct.values()),
                hole=0.6,
                marker=dict(colors=COLORS[:len(ct)], line=dict(color=BG_BASE, width=3)),
                textinfo="label+percent",
                textfont=dict(size=11, color=TX_PRIMARY),
                hovertemplate="<b>%{label}</b>: %{value}%<extra></extra>"
            ))
            fig6.add_annotation(text="<b>Content</b><br>Mix",
                                x=0.5, y=0.5, showarrow=False,
                                font=dict(size=11, color=FONT_COL, family="Inter"), align="center")
            fig6.update_layout(
                plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
                font=dict(color=FONT_COL, family="Inter"),
                margin=dict(l=0, r=0, t=10, b=0), height=280,
                showlegend=True,
                legend=dict(font=dict(color=FONT_COL, size=11), bgcolor="rgba(0,0,0,0)")
            )
            st.plotly_chart(fig6, use_container_width=True, key="fig_pie")

    with cb:
        st.markdown('<p class="sec-head">📽️ Reels vs Posts Engagement</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-sub">Key metrics compared across formats</p>', unsafe_allow_html=True)
        reel_er_val  = pd_main.get("reel_er", 0)
        post_er_val  = pd_main.get("engagement_rate", 0)
        reel_plays   = pd_main.get("reel_avg_plays", 0)
        reel_likes   = pd_main.get("avg_likes", 0)

        fig7 = go.Figure()
        categories = ["Avg ER (%)", "Avg Likes (K)", "Avg Comments (K)"]
        reels_vals = [reel_er_val, round(int(reel_likes*1.35)/1000,1), round(int(pd_main.get("avg_comments",0)*1.2)/1000,1)]
        posts_vals = [post_er_val, round(reel_likes/1000,1), round(pd_main.get("avg_comments",0)/1000,1)]

        fig7.add_trace(go.Bar(name="Reels", x=categories, y=reels_vals,
                              marker_color=COLORS[0], marker_line=dict(width=0),
                              hovertemplate="Reels — %{x}: %{y:,.2f}<extra></extra>"))
        fig7.add_trace(go.Bar(name="Posts", x=categories, y=posts_vals,
                              marker_color=COLORS[2], marker_line=dict(width=0),
                              hovertemplate="Posts — %{x}: %{y:,.2f}<extra></extra>"))
        lo7 = base_layout(280)
        lo7["barmode"] = "group"
        lo7["legend"]  = dict(orientation="h", y=1.12, font=dict(color=FONT_COL, size=11), bgcolor="rgba(0,0,0,0)")
        fig7.update_layout(**lo7)
        st.plotly_chart(fig7, use_container_width=True, key="fig_reels_compare")

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # Reels KPI summary row
    st.markdown('<p class="sec-head">🎯 Reels KPI Summary</p>', unsafe_allow_html=True)
    rm1, rm2, rm3, rm4 = st.columns(4)
    er_lift = round(((reel_er_val - post_er_val) / max(post_er_val, 0.01)) * 100, 1)
    reels_summary = [
        (rm1, "Avg Plays",            format_number(reel_plays), None, "▶️",  ""),
        (rm2, "Reel ER",              f"{reel_er_val:.2f}%",     None, "💬",  ""),
        (rm3, "Reels Published",      str(pd_main.get("reel_count",0)), None, "📽️", ""),
        (rm4, "ER Lift vs Posts",     f"{er_lift:+.1f}%",        None, "📈",  "kpi-accent-green" if er_lift >= 0 else ""),
    ]
    for col, label, value, delta, icon, accent in reels_summary:
        with col:
            st.markdown(kpi_card(label, value, delta, icon, accent), unsafe_allow_html=True)

    st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

    # ── Stories Analytics ─────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">📖 Stories Analytics</p>', unsafe_allow_html=True)
    st.markdown('<p class="sec-sub">Estimated story funnel — views, engagement, and slot drop-off</p>', unsafe_allow_html=True)

    _rnd.seed(followers_val % 9999)
    story_funnel_labels = ["Impressions", "Unique Views", "Replies", "Link Taps", "Profile Visits"]
    story_base = int(followers_val * 0.12)
    story_funnel_vals = [
        int(story_base * 1.4), story_base,
        int(story_base * 0.015), int(story_base * 0.03), int(story_base * 0.05),
    ]

    sa, sb = st.columns([2, 3])
    with sa:
        fig_funnel = go.Figure(go.Funnel(
            y=story_funnel_labels, x=story_funnel_vals,
            textinfo="value+percent initial",
            textfont=dict(color=TX_PRIMARY, size=11),
            marker=dict(color=COLORS[:5], line=dict(color=BG_BASE, width=2)),
            connector=dict(line=dict(color=GRID_COL, width=2)),
        ))
        fig_funnel.update_layout(
            plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
            font=dict(color=FONT_COL, family="Inter"),
            margin=dict(l=0, r=0, t=10, b=0), height=280,
        )
        st.plotly_chart(fig_funnel, use_container_width=True, key="fig_funnel")

    with sb:
        slots = [f"Story {i+1}" for i in range(8)]
        exits = sorted([_rnd.uniform(5, 40) for _ in range(8)])
        lo_exit = base_layout(280, hovermode="closest")
        lo_exit["title"] = dict(text="Exit Rate per Story Slot (%)", font=dict(color=TX_SECONDARY, size=12), x=0)
        fig_exit = go.Figure()
        fig_exit.add_trace(go.Bar(
            x=slots, y=exits,
            marker=dict(color=exits,
                        colorscale=[[0, COLORS[2]], [0.5, COLORS[1]], [1, COLORS[0]]],
                        line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>Exit Rate: %{y:.1f}%<extra></extra>"
        ))
        fig_exit.update_layout(**lo_exit)
        st.plotly_chart(fig_exit, use_container_width=True, key="fig_exit")

    # Reach comparison callout
    story_reach = int(followers_val * 0.08)
    reel_reach_val = pd_main.get("avg_reach", int(followers_val * 0.35))
    reach_ratio = round(reel_reach_val / max(story_reach, 1), 1)
    st.markdown(
        f'<div class="pill-info">'
        f'📡 Avg Story Reach: <strong style="color:{TX_PRIMARY}">{format_number(story_reach)}</strong>'
        f' &nbsp;·&nbsp; Avg Reel Reach: <strong style="color:{TX_PRIMARY}">{format_number(reel_reach_val)}</strong>'
        f' &nbsp;·&nbsp; Reels reach <strong style="color:{COLORS[0]}">{reach_ratio}×</strong> more accounts than Stories'
        f'</div>',
        unsafe_allow_html=True
    )


# ──────────────────────────────────────────────────────────────────────────────
#  TAB 4 — HASHTAGS
# ──────────────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown('<p class="sec-head">🏷️ Hashtag Analytics</p>', unsafe_allow_html=True)
    st.markdown('<p class="sec-sub">Performance of auto-extracted hashtags from post captions</p>', unsafe_allow_html=True)

    profile_ht = pd_main.get("hashtags", [])
    if profile_ht:
        ht_df = pd.DataFrame(profile_ht).head(12)
        lo_ht = base_layout(300, hovermode="closest")
        lo_ht["xaxis"] = dict(showgrid=True, gridcolor=GRID_COL, color=TICK_COL, tickfont=dict(size=10))
        lo_ht["yaxis"] = dict(showgrid=False, color=TICK_COL, tickfont=dict(size=10))
        fig8 = go.Figure(go.Bar(
            y=ht_df["tag"], x=ht_df["avg_engagement"],
            orientation="h",
            marker=dict(color=ht_df["avg_engagement"],
                        colorscale=[[0, COLORS[3]], [1, COLORS[0]]],
                        line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Avg Engagement: %{x:,.0f}<extra></extra>"
        ))
        fig8.update_layout(**lo_ht)
        st.plotly_chart(fig8, use_container_width=True, key="fig_ht")

    if hashtags_data:
        st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)
        st.markdown('<p class="sec-head">🌐 Tracked Hashtag Deep-Dive</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-sub">Volume and engagement via HasData lookup</p>', unsafe_allow_html=True)

        ht_rows = [
            {
                "Hashtag": tag,
                "Total Posts":    format_number(d.get("posts_count", 0)),
                "Avg Likes":      format_number(d.get("avg_likes", 0)),
                "Avg Comments":   format_number(d.get("avg_comments", 0)),
                "Avg Engagement": format_number(d.get("avg_engagement", 0)),
            }
            for tag, d in hashtags_data.items()
        ]
        if ht_rows:
            st.dataframe(pd.DataFrame(ht_rows), use_container_width=True, hide_index=True)

        vol_data = [(t, d.get("posts_count",0)) for t,d in hashtags_data.items() if d.get("posts_count",0)>0]
        if vol_data:
            vol_df = pd.DataFrame(vol_data, columns=["tag","posts_count"]).sort_values("posts_count", ascending=False)
            st.markdown('<p class="sec-head" style="margin-top:16px">📦 Hashtag Volume</p>', unsafe_allow_html=True)
            lo_vol = base_layout(240, hovermode="closest")
            lo_vol["xaxis"] = dict(tickangle=-30, tickfont=dict(size=10), color=TICK_COL)
            fig9 = go.Figure(go.Bar(
                x=vol_df["tag"], y=vol_df["posts_count"],
                marker=dict(color=COLORS[0], opacity=0.85, line=dict(width=0)),
                hovertemplate="<b>%{x}</b><br>%{y:,.0f} posts<extra></extra>"
            ))
            fig9.update_layout(**lo_vol)
            st.plotly_chart(fig9, use_container_width=True, key="fig_vol")

        chips = " ".join(f'<span class="tag-chip">{t}</span>' for t in hashtags_data.keys())
        st.markdown(f'<div style="line-height:2.4;margin-top:8px">{chips}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="pill-warn">No hashtag data yet — switch to Hashtag Tracking mode or enable live API.</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
#  TAB 5 — COMPETITOR BENCH
# ──────────────────────────────────────────────────────────────────────────────
if input_mode == "Competitor Comparison":
    with tabs[4]:
        st.markdown('<p class="sec-head">⚔️ Head-to-Head Comparison</p>', unsafe_allow_html=True)
        st.markdown('<p class="sec-sub">Side-by-side benchmarking across up to 3 profiles</p>', unsafe_allow_html=True)

        comp_rows = []
        for u in usernames:
            d = profiles_data.get(u, {})
            comp_rows.append({
                "Profile":       f"@{u}",
                "Verified":      "✅" if d.get("verified") else "—",
                "Followers":     d.get("followers", 0),
                "Eng. Rate (%)": round(d.get("engagement_rate", 0), 2),
                "Avg Likes":     d.get("avg_likes", 0),
                "Avg Comments":  d.get("avg_comments", 0),
                "Reel ER (%)":   round(d.get("reel_er", 0), 2),
                "Avg Reach":     d.get("avg_reach", 0),
                "Posts":         d.get("total_posts", 0),
            })
        comp_df = pd.DataFrame(comp_rows)

        # ER comparison
        ba, bb = st.columns([3, 2])
        with ba:
            st.markdown('<p class="sec-head">Engagement Rate Comparison</p>', unsafe_allow_html=True)
            fig10 = go.Figure()
            for i, row in comp_df.iterrows():
                fig10.add_trace(go.Bar(
                    name=row["Profile"],
                    x=["Post ER (%)", "Reel ER (%)"],
                    y=[row["Eng. Rate (%)"], row["Reel ER (%)"]],
                    marker_color=COLORS[i % len(COLORS)], marker_line=dict(width=0),
                    hovertemplate=f"<b>{row['Profile']}</b><br>%{{x}}: %{{y:.2f}}%<extra></extra>"
                ))
            lo10 = base_layout(300)
            lo10["barmode"] = "group"
            lo10["legend"]  = dict(orientation="h", y=1.1, font=dict(color=FONT_COL,size=11), bgcolor="rgba(0,0,0,0)")
            fig10.update_layout(**lo10)
            st.plotly_chart(fig10, use_container_width=True, key="fig_comp_er")

        with bb:
            st.markdown('<p class="sec-head">Follower Count</p>', unsafe_allow_html=True)
            fig11 = go.Figure(go.Bar(
                x=comp_df["Followers"], y=comp_df["Profile"],
                orientation="h",
                marker=dict(color=COLORS[:len(comp_df)], line=dict(width=0)),
                hovertemplate="<b>%{y}</b><br>%{x:,.0f} followers<extra></extra>"
            ))
            lo11 = base_layout(300, hovermode="closest")
            lo11["xaxis"] = dict(showgrid=True, gridcolor=GRID_COL, color=TICK_COL, tickfont=dict(size=10))
            lo11["yaxis"] = dict(showgrid=False, color=TICK_COL, tickfont=dict(size=11))
            fig11.update_layout(**lo11)
            st.plotly_chart(fig11, use_container_width=True, key="fig_comp_followers")

        st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

        st.markdown('<p class="sec-head">Avg Likes & Comments per Post</p>', unsafe_allow_html=True)
        fig12 = go.Figure()
        for metric, color in [("Avg Likes", COLORS[0]), ("Avg Comments", COLORS[1])]:
            fig12.add_trace(go.Bar(
                name=metric, x=comp_df["Profile"], y=comp_df[metric],
                marker_color=color, marker_line=dict(width=0),
                hovertemplate=f"<b>%{{x}}</b><br>{metric}: %{{y:,.0f}}<extra></extra>"
            ))
        lo12 = base_layout(240)
        lo12["barmode"] = "group"
        lo12["legend"]  = dict(orientation="h", y=1.12, font=dict(color=FONT_COL, size=11), bgcolor="rgba(0,0,0,0)")
        fig12.update_layout(**lo12)
        st.plotly_chart(fig12, use_container_width=True, key="fig_comp_likes")

        st.markdown("<hr class='hdivider'>", unsafe_allow_html=True)

        st.markdown('<p class="sec-head">📋 Full Metrics Table</p>', unsafe_allow_html=True)
        disp_df = comp_df.copy()
        for col in ["Followers", "Avg Reach", "Avg Likes", "Avg Comments"]:
            disp_df[col] = disp_df[col].apply(format_number)
        st.dataframe(disp_df, use_container_width=True, hide_index=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<hr class='hdivider' style='margin-top:32px'>", unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align:center;color:{TX_MUTED};font-size:10px;letter-spacing:1.2px'>"
    "INSTALENS v3.1 · HASDATA API · STREAMLIT · PLOTLY · PROFESSIONAL SOCIAL MEDIA ANALYTICS"
    "</p>",
    unsafe_allow_html=True
)
