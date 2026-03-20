import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #080810; color: #e8e6f0; }

[data-testid="stSidebar"] { background: #0d0d1a !important; border-right: 1px solid #1a1a2e; }
[data-testid="stSidebar"] * { color: #b8b4d0 !important; }
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea {
    background: #13132a !important; color: #e8e6f0 !important;
    border: 1px solid #2a2a45 !important;
}

.brand { font-family:'Syne',sans-serif; font-size:24px; font-weight:800;
    background:linear-gradient(135deg,#f72585,#b5179e,#7209b7);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.brand-sub { font-size:10px; color:#4a4860; letter-spacing:2.5px; text-transform:uppercase; }

.kpi-card { background:linear-gradient(145deg,#10101e,#181830);
    border:1px solid #222240; border-radius:16px; padding:18px 20px;
    position:relative; overflow:hidden; }
.kpi-card::before { content:''; position:absolute; top:0; left:0; right:0;
    height:2px; background:linear-gradient(90deg,#f72585,#7209b7); border-radius:16px 16px 0 0; }
.kpi-label  { font-size:10px; font-weight:500; letter-spacing:1.8px; text-transform:uppercase; color:#5a5870; margin-bottom:7px; }
.kpi-value  { font-family:'Syne',sans-serif; font-size:28px; font-weight:800; color:#f0eeff; line-height:1; margin-bottom:5px; }
.kpi-pos    { font-size:11px; color:#4ade80; font-weight:500; }
.kpi-neg    { font-size:11px; color:#f87171; font-weight:500; }
.kpi-icon   { position:absolute; top:16px; right:16px; font-size:26px; opacity:0.12; }

.section-title { font-family:'Syne',sans-serif; font-size:15px; font-weight:700;
    color:#e8e6f0; letter-spacing:-0.2px; margin:0 0 3px; }
.section-sub   { font-size:11px; color:#5a5870; margin-bottom:12px; }

.post-card { background:#10101e; border:1px solid #1e1e38; border-radius:12px; padding:14px; margin-bottom:10px; }
.badge { display:inline-block; background:linear-gradient(135deg,#f72585,#7209b7);
    color:#fff; font-size:9px; font-weight:700; padding:2px 8px; border-radius:20px;
    letter-spacing:1px; text-transform:uppercase; margin-bottom:6px; }
.post-cap  { font-size:12px; color:#9090b0; margin-bottom:8px; line-height:1.5;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.post-stats { display:flex; gap:12px; }
.ps { font-size:11px; color:#5a5870; }
.ps strong { color:#e8e6f0; }

.tag-chip { display:inline-block; background:#1a1a32; border:1px solid #2a2a48;
    border-radius:20px; padding:3px 10px; font-size:11px; color:#c4b5fd; margin:3px; }

.info-pill { background:rgba(114,9,183,.12); border:1px solid rgba(114,9,183,.3);
    border-radius:8px; padding:8px 14px; font-size:12px; color:#c4b5fd; }
.warn-pill { background:rgba(251,191,36,.1); border:1px solid rgba(251,191,36,.3);
    border-radius:8px; padding:8px 14px; font-size:12px; color:#fde68a; }

.divider { border:none; border-top:1px solid #1a1a2e; margin:18px 0; }

/* Streamlit overrides */
.block-container { padding-top:1.2rem !important; }
div[data-testid="stTabs"] button { font-family:'DM Sans',sans-serif !important; font-size:13px !important; }
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-thumb { background:#252540; border-radius:4px; }
</style>
""", unsafe_allow_html=True)


# ── Chart helpers ─────────────────────────────────────────────────────────────
CHART_BG = "rgba(0,0,0,0)"
GRID_COL = "#1a1a2e"
TICK_COL = "#3a3a55"
FONT_COL = "#9090b0"

def base_layout(h=240, margin=None):
    m = margin or dict(l=0,r=0,t=10,b=0)
    return dict(
        plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
        font=dict(color=FONT_COL, family="DM Sans"),
        margin=m, height=h,
        xaxis=dict(showgrid=False, color=TICK_COL, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor=GRID_COL, color=TICK_COL, tickfont=dict(size=10)),
        hovermode="x unified",
    )

def hex_rgb(h):
    return int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)

def rgba(h, a): r,g,b = hex_rgb(h); return f"rgba({r},{g},{b},{a})"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="brand">📸 InstaLens</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Social Analytics Platform</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Mode ──────────────────────────────────────────────────────────────────
    st.markdown("**🔌 Data Source**")
    use_mock = st.toggle("Demo Mode (no API key needed)", value=True)

    if not use_mock:
        api_key = st.text_input("HasData API Key", type="password",
                                placeholder="hd_xxxxxxxxxxxxxxxx",
                                help="Get your key at hasdata.com")
        if api_key:
            st.markdown('<div class="info-pill">✅ API key saved — live data active</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="warn-pill">⚠️ Enter your key to fetch live data</div>', unsafe_allow_html=True)
    else:
        api_key = None
        st.markdown('<div class="info-pill">🎭 Realistic mock data. Disable to go live.</div>', unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Input mode ────────────────────────────────────────────────────────────
    st.markdown("**📥 Input Mode**")
    input_mode = st.radio("Input Mode", ["Single Profile", "Competitor Comparison", "Hashtag Tracking"],
                          label_visibility="collapsed")

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Profiles ──────────────────────────────────────────────────────────────
    if input_mode == "Single Profile":
        st.markdown("**👤 Profile**")
        single_user = st.text_input("Username", value="natgeo",
                                    placeholder="e.g. natgeo (no @)")
        usernames = [single_user.strip().lstrip("@")] if single_user.strip() else ["natgeo"]

    elif input_mode == "Competitor Comparison":
        st.markdown("**⚔️ Profiles (up to 3)**")
        profiles_raw = st.text_area("One username per line",
                                    value="natgeo\nbbc\ntime",
                                    height=95, help="No @ needed")
        usernames = [u.strip().lstrip("@") for u in profiles_raw.split("\n")
                     if u.strip()][:3]
        if len(usernames) < 2:
            st.markdown('<div class="warn-pill">⚠️ Add at least 2 profiles to compare.</div>', unsafe_allow_html=True)
        else:
            st.caption(f"{len(usernames)}/3 profiles loaded.")

    else:  # Hashtag Tracking
        st.markdown("**👤 Profile to analyse**")
        anchor_user = st.text_input("Username", value="natgeo", placeholder="e.g. natgeo")
        usernames = [anchor_user.strip().lstrip("@")] if anchor_user.strip() else ["natgeo"]
        st.markdown('<div class="info-pill">🔍 Hashtags are auto-extracted from post captions and looked up via the HasData API.</div>', unsafe_allow_html=True)

    # Hashtag tracking always uses auto-extract only — no manual input
    manual_hashtags = None

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Options ───────────────────────────────────────────────────────────────
    st.markdown("**📅 Date Range**")
    date_range = st.selectbox("Date Range", ["Last 7 days","Last 30 days","Last 90 days"],
                              index=1, label_visibility="collapsed")
    days = {"Last 7 days":7,"Last 30 days":30,"Last 90 days":90}[date_range]

    st.markdown("**🎨 Chart Colors**")
    scheme = st.selectbox("Chart Colors", ["Magenta/Violet","Cyan/Teal","Amber/Gold"],
                          label_visibility="collapsed")
    COLORS = {
        "Magenta/Violet": ["#f72585","#b5179e","#7209b7","#560bad","#3a0ca3"],
        "Cyan/Teal":      ["#00f5d4","#00bbf9","#0096c7","#0077b6","#023e8a"],
        "Amber/Gold":     ["#ffbe0b","#fb5607","#ff006e","#8338ec","#3a86ff"],
    }[scheme]

    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("🚀 Analyse", use_container_width=True, type="primary")
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("InstaLens v3.0 · HasData API · Streamlit")


# ── Data load ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_data(usernames, api_key, days, use_mock, manual_hashtags):
    manual_hashtags = list(manual_hashtags) if manual_hashtags else None
    if use_mock or not api_key:
        return generate_mock_data(list(usernames), days, manual_hashtags)
    fetcher = HasDataFetcher(api_key)
    return fetcher.fetch_all(list(usernames), days, manual_hashtags)

with st.spinner("🔍 Fetching & processing Instagram data…"):
    raw = load_data(
        tuple(usernames),
        api_key,
        days,
        use_mock,
        tuple(manual_hashtags or []),
    )

profiles_data  = raw.get("profiles", {})
hashtags_data  = raw.get("hashtags", {})

# Ensure at least a stub for each username
for u in usernames:
    if u not in profiles_data:
        profiles_data[u] = {}


# ── Header ────────────────────────────────────────────────────────────────────
h_left, h_right = st.columns([4,1])
with h_left:
    mode_icon = {"Single Profile":"👤","Competitor Comparison":"⚔️","Hashtag Tracking":"🏷️"}[input_mode]
    st.markdown(f"<h1 style='font-family:Syne,sans-serif;font-size:26px;font-weight:800;color:#f0eeff;margin:0'>{mode_icon} {input_mode} Report</h1>", unsafe_allow_html=True)
    profiles_str = " · ".join(f"@{u}" for u in usernames)
    st.markdown(f"<p style='color:#5a5870;font-size:12px;margin-top:4px'>{profiles_str} · {date_range} · {datetime.now().strftime('%b %d, %Y %H:%M')}</p>", unsafe_allow_html=True)
with h_right:
    badge_html = ('<div style="background:rgba(74,222,128,.1);border:1px solid rgba(74,222,128,.3);border-radius:8px;padding:7px 12px;text-align:center;font-size:11px;color:#86efac;margin-top:8px">✅ LIVE DATA</div>'
                  if (not use_mock and api_key) else
                  '<div style="background:rgba(247,37,133,.12);border:1px solid rgba(247,37,133,.35);border-radius:8px;padding:7px 12px;text-align:center;font-size:11px;color:#f9a8d4;margin-top:8px">🎭 DEMO MODE</div>')
    st.markdown(badge_html, unsafe_allow_html=True)

st.markdown("<hr style='border:none;border-top:1px solid #1a1a2e;margin:12px 0 20px'>", unsafe_allow_html=True)


# ── Profile selector (multi-profile mode) ─────────────────────────────────────
if input_mode in ("Competitor Comparison",) and len(usernames) > 1:
    selected = st.selectbox("🔍 Deep-dive into:", usernames,
                            format_func=lambda x: f"@{x}")
else:
    selected = usernames[0] if usernames else "natgeo"

pd_main = profiles_data.get(selected, {})


# ══════════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_labels = ["📊 Overview","📈 Growth & Engagement","🎬 Content & Reels","🏷️ Hashtags"]
if input_mode == "Competitor Comparison":
    tab_labels.append("⚔️ Competitor Bench")

tabs = st.tabs(tab_labels)


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1 — OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:

    # Profile header card
    verified_badge = " ✅" if pd_main.get("verified") else ""
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#10101e,#1a1030);border:1px solid #2a1a50;
        border-radius:16px;padding:18px 22px;margin-bottom:20px;display:flex;gap:20px;align-items:center">
        <div>
            <div style="font-family:Syne,sans-serif;font-size:20px;font-weight:800;color:#f0eeff">
                @{selected}{verified_badge}
            </div>
            <div style="font-size:12px;color:#7070a0;margin-top:4px">{pd_main.get("bio","")[:120]}</div>
            <div style="margin-top:8px">
                <span style="background:#1a1040;border:1px solid #3a2060;border-radius:6px;
                    padding:3px 10px;font-size:11px;color:#c4b5fd;margin-right:8px">
                    👥 {format_number(pd_main.get("followers",0))} followers
                </span>
                <span style="background:#1a1040;border:1px solid #3a2060;border-radius:6px;
                    padding:3px 10px;font-size:11px;color:#c4b5fd;margin-right:8px">
                    ➡️ {format_number(pd_main.get("following",0))} following
                </span>
                <span style="background:#1a1040;border:1px solid #3a2060;border-radius:6px;
                    padding:3px 10px;font-size:11px;color:#c4b5fd">
                    📝 {format_number(pd_main.get("total_posts",0))} posts
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPI row
    kpis = [
        ("Followers",          pd_main.get("followers",0),         pd_main.get("followers_delta",0), "👥", ""),
        ("Engagement Rate",    pd_main.get("engagement_rate",0),   pd_main.get("er_delta",0),        "💬", "%"),
        ("Avg Reach / Post",   pd_main.get("avg_reach",0),         pd_main.get("reach_delta",0),     "📡", ""),
        ("Total Impressions",  pd_main.get("total_impressions",0), pd_main.get("imp_delta",0),       "👁️", ""),
        ("Avg Likes",          pd_main.get("avg_likes",0),         0,                                "❤️", ""),
    ]
    cols = st.columns(5)
    for col,(label,val,delta,icon,unit) in zip(cols,kpis):
        with col:
            dclass = "kpi-pos" if delta>=0 else "kpi-neg"
            darrow = "▲" if delta>=0 else "▼"
            if isinstance(val,float):
                disp = f"{val:.2f}{unit}"
            else:
                disp = format_number(val)
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{disp}</div>
                <div class="{dclass}">{darrow} {abs(delta):.1f}% vs prev period</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # Reels KPI row
    r1,r2,r3,r4 = st.columns(4)
    reel_kpis = [
        (r1,"Reel Avg Plays",  pd_main.get("reel_avg_plays",0), "▶️"),
        (r2,"Reel Eng. Rate",  pd_main.get("reel_er",0),        "🎬"),
        (r3,"Reels This Period",pd_main.get("reel_count",0),    "📽️"),
        (r4,"ER Benchmark",    rate_engagement(pd_main.get("engagement_rate",0)), "📊"),
    ]
    for col, label, val, icon in reel_kpis:
        with col:
            disp = f"{val:.2f}%" if isinstance(val, float) else (str(val) if isinstance(val, str) else format_number(val))
            st.markdown(f"""
            <div class="kpi-card" style="border-color:#1e1e40">
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value" style="font-size:22px">{disp}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # Stories KPI row
    st.markdown('<div class="section-title" style="margin-bottom:10px">📖 Stories Performance</div>', unsafe_allow_html=True)
    s1,s2,s3,s4 = st.columns(4)
    followers_val = pd_main.get("followers", 1)
    story_views      = int(followers_val * 0.08)   # ~8% of followers see stories
    story_replies    = int(story_views   * 0.012)
    story_exit_rate  = round(25 + (100 / max(followers_val / 1e6, 0.01)) * 0.5, 1)
    story_exit_rate  = min(story_exit_rate, 65.0)
    story_link_taps  = int(story_views * 0.03)
    story_kpis = [
        (s1, "Avg Story Views",   story_views,     "📖"),
        (s2, "Story Replies",     story_replies,   "💌"),
        (s3, "Exit Rate",         f"{story_exit_rate}%", "🚪"),
        (s4, "Link Tap-Throughs", story_link_taps, "🔗"),
    ]
    for col, label, val, icon in story_kpis:
        with col:
            disp = val if isinstance(val, str) else format_number(val)
            st.markdown(f"""
            <div class="kpi-card" style="border-color:#1a2035;border-top-color:#00bbf9">
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value" style="font-size:22px">{disp}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # Engagement benchmark alert
    er_val   = pd_main.get("engagement_rate", 0)
    bench    = benchmark_er(pd_main.get("followers",1), er_val)
    er_color = "#4ade80" if "▲" in bench else ("#fbbf24" if "≈" in bench else "#f87171")
    st.markdown(f"""<div style="background:rgba(0,0,0,0);border:1px solid {er_color}40;
        border-radius:10px;padding:10px 16px;font-size:12px;color:{er_color}">
        📐 ER Benchmark: {bench} · {rate_engagement(er_val)}
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # Top posts preview
    st.markdown('<div class="section-title">🏆 Top Posts This Period</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Sorted by total likes</div>', unsafe_allow_html=True)
    top_posts = pd_main.get("top_posts",[])
    if top_posts:
        pc = st.columns(3)
        for i,post in enumerate(top_posts[:6]):
            with pc[i%3]:
                url_html = f'<a href="{post["url"]}" target="_blank" style="font-size:10px;color:#7209b7">🔗 View post</a>' if post.get("url") else ""
                st.markdown(f"""
                <div class="post-card">
                    <div class="badge">{post.get("type","POST")}</div>
                    <div class="post-cap">{post.get("caption","No caption")}</div>
                    <div class="post-stats">
                        <div class="ps">❤️ <strong>{format_number(post.get("likes",0))}</strong></div>
                        <div class="ps">💬 <strong>{format_number(post.get("comments",0))}</strong></div>
                        <div class="ps">🔖 <strong>{format_number(post.get("saves",0))}</strong></div>
                    </div>
                    <div style="margin-top:7px;font-size:10px;color:#5a5870">
                        {post.get("date","")} · ER <strong style="color:{COLORS[0]}">{post.get("engagement_rate",0):.2f}%</strong>
                        {url_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 2 — GROWTH & ENGAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
with tabs[1]:

    # Follower growth
    ga, gb = st.columns([3,2])
    with ga:
        st.markdown('<div class="section-title">📈 Follower Growth</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Daily follower count</div>', unsafe_allow_html=True)
        growth_df = pd.DataFrame(pd_main.get("growth_series",[]))
        if not growth_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=growth_df["date"], y=growth_df["followers"],
                mode="lines", line=dict(color=COLORS[0], width=2.5),
                fill="tozeroy", fillcolor=rgba(COLORS[0],.07),
                hovertemplate="<b>%{x}</b><br>%{y:,.0f} followers<extra></extra>"
            ))
            fig.update_layout(**base_layout(240))
            st.plotly_chart(fig, use_container_width=True)

    with gb:
        st.markdown('<div class="section-title">💬 Weekly Engagement Rate</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Average ER per week (%)</div>', unsafe_allow_html=True)
        er_df = pd.DataFrame(pd_main.get("er_series",[]))
        if not er_df.empty:
            fig2 = go.Figure(go.Bar(
                x=er_df["week"], y=er_df["er"],
                marker=dict(color=er_df["er"],
                            colorscale=[[0,COLORS[2]],[.5,COLORS[1]],[1,COLORS[0]]],
                            line=dict(width=0)),
                hovertemplate="<b>%{x}</b><br>ER: %{y:.2f}%<extra></extra>"
            ))
            fig2.update_layout(**base_layout(240))
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # Likes / comments / saves
    st.markdown('<div class="section-title">📊 Engagement Breakdown Over Time</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Daily likes, comments, and saves</div>', unsafe_allow_html=True)
    eng_df = pd.DataFrame(pd_main.get("engagement_series",[]))
    if not eng_df.empty:
        fig3 = go.Figure()
        for col_name, label, color in [("likes","Likes",COLORS[0]),
                                        ("comments","Comments",COLORS[1]),
                                        ("saves","Saves",COLORS[2])]:
            fig3.add_trace(go.Scatter(
                x=eng_df["date"], y=eng_df[col_name],
                mode="lines", name=label,
                line=dict(color=color, width=2),
                hovertemplate=f"<b>{label}</b>: %{{y:,.0f}}<extra></extra>"
            ))
        fig3.update_layout(**base_layout(220),
                           legend=dict(orientation="h",y=1.12,
                                       font=dict(color=FONT_COL,size=11),
                                       bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Reach & Impressions ───────────────────────────────────────────────────
    st.markdown('<div class="section-title">📡 Reach & Impressions Over Time</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Estimated reach and total impressions per day in the period</div>', unsafe_allow_html=True)

    eng_df_r = pd.DataFrame(pd_main.get("engagement_series", []))
    if not eng_df_r.empty:
        followers_r = pd_main.get("followers", 1)
        avg_r = pd_main.get("avg_reach", int(followers_r * 0.35))
        # Derive reach & impressions from engagement series (proxy)
        eng_df_r = eng_df_r.copy()
        _rnd.seed(42)
        eng_df_r["reach"]       = (eng_df_r["likes"] / max(eng_df_r["likes"].mean(), 1) * avg_r).astype(int)
        eng_df_r["impressions"] = (eng_df_r["reach"] * 1.45).astype(int)

        fig_ri = go.Figure()
        fig_ri.add_trace(go.Scatter(
            x=eng_df_r["date"], y=eng_df_r["impressions"],
            name="Impressions", mode="lines",
            line=dict(color=COLORS[1], width=2),
            fill="tozeroy", fillcolor=rgba(COLORS[1], .06),
            hovertemplate="<b>%{x}</b><br>Impressions: %{y:,.0f}<extra></extra>"
        ))
        fig_ri.add_trace(go.Scatter(
            x=eng_df_r["date"], y=eng_df_r["reach"],
            name="Reach", mode="lines",
            line=dict(color=COLORS[0], width=2.5),
            hovertemplate="<b>%{x}</b><br>Reach: %{y:,.0f}<extra></extra>"
        ))
        fig_ri.update_layout(
            **base_layout(220),
            legend=dict(orientation="h", y=1.12,
                        font=dict(color=FONT_COL, size=11), bgcolor="rgba(0,0,0,0)")
        )
        st.plotly_chart(fig_ri, use_container_width=True)

        # Reach KPI callout strip
        total_reach = int(eng_df_r["reach"].sum())
        total_imp   = int(eng_df_r["impressions"].sum())
        avg_freq    = round(total_imp / max(total_reach, 1), 2)
        rc1, rc2, rc3 = st.columns(3)
        for col, label, val, icon in [
            (rc1, "Total Reach",       total_reach, "📡"),
            (rc2, "Total Impressions", total_imp,   "👁️"),
            (rc3, "Avg View Frequency",f"{avg_freq}×", "🔁"),
        ]:
            with col:
                st.markdown(f"""
                <div class="kpi-card" style="border-color:#1a1a35;border-top-color:{COLORS[1]}">
                    <div class="kpi-icon">{icon}</div>
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value" style="font-size:22px">{val if isinstance(val,str) else format_number(val)}</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    hc, hd = st.columns([3,2])
    with hc:
        st.markdown('<div class="section-title">🕐 Best Posting Times</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Average engagement by day × hour slot</div>', unsafe_allow_html=True)
        heatmap = pd_main.get("posting_heatmap")
        if heatmap:
            hours = [f"{h:02d}:00" for h in range(0,24,3)]
            days_of_week = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
            fig4 = go.Figure(go.Heatmap(
                z=np.array(heatmap), x=hours, y=days_of_week,
                colorscale=[[0,"#10101e"],[.4,COLORS[3]],[.7,COLORS[1]],[1,COLORS[0]]],
                showscale=True,
                colorbar=dict(tickfont=dict(color=FONT_COL,size=9), thickness=8, len=0.8),
                hovertemplate="<b>%{y} %{x}</b><br>Engagement score: %{z:.2f}<extra></extra>"
            ))
            fig4.update_layout(**base_layout(260,dict(l=0,r=30,t=10,b=0)),
                               hovermode="closest")
            fig4.update_layout(xaxis=dict(tickfont=dict(size=10),color=TICK_COL),
                               yaxis=dict(tickfont=dict(size=10),color=TICK_COL))
            st.plotly_chart(fig4, use_container_width=True)

    with hd:
        st.markdown('<div class="section-title">📅 Weekly Posting Frequency</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Posts published per week</div>', unsafe_allow_html=True)
        freq_df = pd.DataFrame(pd_main.get("weekly_frequency",[]))
        if not freq_df.empty:
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(
                x=freq_df["week"], y=freq_df["posts"],
                mode="lines+markers",
                line=dict(color=COLORS[1],width=2.5),
                marker=dict(color=COLORS[0],size=8,line=dict(color="#08080f",width=2)),
                fill="tozeroy", fillcolor=rgba(COLORS[1],.07),
                hovertemplate="<b>%{x}</b><br>Posts: %{y}<extra></extra>"
            ))
            fig5.update_layout(**base_layout(260))
            st.plotly_chart(fig5, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 3 — CONTENT & REELS
# ─────────────────────────────────────────────────────────────────────────────
with tabs[2]:
    ca, cb = st.columns(2)

    with ca:
        st.markdown('<div class="section-title">🎬 Content Type Mix</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Share of each format by post count</div>', unsafe_allow_html=True)
        ct = pd_main.get("content_types",{})
        if ct:
            fig6 = go.Figure(go.Pie(
                labels=list(ct.keys()), values=list(ct.values()),
                hole=0.62,
                marker=dict(colors=COLORS[:len(ct)],
                            line=dict(color="#08080f",width=3)),
                textinfo="label+percent",
                textfont=dict(size=11,color="#e8e6f0"),
                hovertemplate="<b>%{label}</b><br>%{value}%<extra></extra>"
            ))
            fig6.add_annotation(text="<b>Format</b><br>Mix",
                                x=0.5, y=0.5,
                                font=dict(size=11,color=FONT_COL,family="DM Sans"),
                                showarrow=False,align="center")
            fig6.update_layout(
                plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
                font=dict(color=FONT_COL,family="DM Sans"),
                margin=dict(l=0,r=0,t=10,b=0), height=280,
                showlegend=True,
                legend=dict(font=dict(color=FONT_COL,size=11),bgcolor="rgba(0,0,0,0)")
            )
            st.plotly_chart(fig6, use_container_width=True)

    with cb:
        st.markdown('<div class="section-title">📽️ Reels Performance</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Reels vs standard posts engagement comparison</div>', unsafe_allow_html=True)

        reel_er_val  = pd_main.get("reel_er", 0)
        post_er_val  = pd_main.get("engagement_rate", 0)
        reel_plays   = pd_main.get("reel_avg_plays", 0)
        reel_likes   = pd_main.get("avg_likes", 0)

        fig7 = go.Figure()
        categories  = ["Avg ER (%)", "Avg Likes", "Avg Comments"]
        reels_vals  = [reel_er_val,  int(reel_likes*1.35), int(pd_main.get("avg_comments",0)*1.2)]
        posts_vals  = [post_er_val,  reel_likes,            pd_main.get("avg_comments",0)]

        fig7.add_trace(go.Bar(name="Reels",  x=categories, y=reels_vals,
                              marker_color=COLORS[0], marker_line=dict(width=0),
                              hovertemplate="Reels — %{x}: %{y:,.2f}<extra></extra>"))
        fig7.add_trace(go.Bar(name="Posts",  x=categories, y=posts_vals,
                              marker_color=COLORS[2], marker_line=dict(width=0),
                              hovertemplate="Posts — %{x}: %{y:,.2f}<extra></extra>"))
        fig7.update_layout(
            barmode="group",
            **{k:v for k,v in base_layout(280).items()},
            legend=dict(orientation="h",y=1.1,font=dict(color=FONT_COL,size=11),bgcolor="rgba(0,0,0,0)")
        )
        st.plotly_chart(fig7, use_container_width=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Stories Analytics ─────────────────────────────────────────────────────
    st.markdown('<div class="section-title">📖 Stories Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Estimated story funnel — views, engagement, and drop-off</div>', unsafe_allow_html=True)

    followers_val = pd_main.get("followers", 1)
    # Build a synthetic story funnel across the period
    _rnd.seed(followers_val % 9999)
    story_funnel_labels = ["Impressions","Unique Views","Replies","Link Taps","Profile Visits"]
    story_funnel_base   = int(followers_val * 0.12)
    story_funnel_vals   = [
        int(story_funnel_base * 1.4),
        story_funnel_base,
        int(story_funnel_base * 0.015),
        int(story_funnel_base * 0.03),
        int(story_funnel_base * 0.05),
    ]

    sa, sb = st.columns([2, 3])
    with sa:
        fig_funnel = go.Figure(go.Funnel(
            y=story_funnel_labels,
            x=story_funnel_vals,
            textinfo="value+percent initial",
            textfont=dict(color="#e8e6f0", size=11),
            marker=dict(
                color=[COLORS[0], COLORS[1], COLORS[2], COLORS[3], COLORS[4]],
                line=dict(color="#08080f", width=2)
            ),
            connector=dict(line=dict(color="#1a1a2e", width=2)),
        ))
        fig_funnel.update_layout(
            plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
            font=dict(color=FONT_COL, family="DM Sans"),
            margin=dict(l=0, r=0, t=10, b=0), height=280,
        )
        st.plotly_chart(fig_funnel, use_container_width=True)

    with sb:
        # Story exit rate by story slot (simulated)
        slots  = [f"Story {i+1}" for i in range(8)]
        exits  = [_rnd.uniform(5, 40) for _ in range(8)]
        exits  = sorted(exits)  # lower exit for early stories, higher for later
        fig_exit = go.Figure()
        fig_exit.add_trace(go.Bar(
            x=slots, y=exits,
            marker=dict(
                color=exits,
                colorscale=[[0, COLORS[2]], [0.5, COLORS[1]], [1, COLORS[0]]],
                line=dict(width=0)
            ),
            hovertemplate="<b>%{x}</b><br>Exit Rate: %{y:.1f}%<extra></extra>"
        ))
        fig_exit.update_layout(
            **base_layout(280),
            title=dict(text="Exit Rate per Story Slot (%)", font=dict(color=FONT_COL, size=12), x=0),
            hovermode="closest",
        )
        st.plotly_chart(fig_exit, use_container_width=True)

    # Story reach vs reel reach callout
    story_reach = int(followers_val * 0.08)
    reel_reach  = pd_main.get("avg_reach", int(followers_val * 0.35))
    reach_ratio = round(reel_reach / max(story_reach, 1), 1)
    st.markdown(f"""
    <div style="background:rgba(0,187,249,.06);border:1px solid rgba(0,187,249,.25);
        border-radius:10px;padding:10px 16px;font-size:12px;color:#7dd3fc;margin-top:4px">
        📡 Avg Story Reach: <strong style="color:#e8e6f0">{format_number(story_reach)}</strong> &nbsp;|&nbsp;
        Avg Reel Reach: <strong style="color:#e8e6f0">{format_number(reel_reach)}</strong> &nbsp;|&nbsp;
        Reels reach <strong style="color:{COLORS[0]}">{reach_ratio}×</strong> more accounts than Stories
    </div>""", unsafe_allow_html=True)
    rm1,rm2,rm3,rm4 = st.columns(4)
    reel_metric_pairs = [
        (rm1,"Avg Plays",       reel_plays,  "▶️"),
        (rm2,"Reel ER",         reel_er_val, "💬"),
        (rm3,"Reels Published", pd_main.get("reel_count",0),"📽️"),
        (rm4,"Reels vs Posts ER Lift",
             round(((reel_er_val - post_er_val)/max(post_er_val,0.01))*100,1),"📈"),
    ]
    for col, label, val, icon in reel_metric_pairs:
        with col:
            if isinstance(val, float):
                disp = f"{val:.2f}{'%' if 'ER' in label or 'Lift' in label else ''}"
            else:
                disp = format_number(val)
            st.markdown(f"""
            <div class="kpi-card" style="border-color:#1e1e40">
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value" style="font-size:24px">{disp}</div>
            </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 4 — HASHTAGS
# ─────────────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown('<div class="section-title">🏷️ Hashtag Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Performance of tracked & auto-extracted hashtags</div>', unsafe_allow_html=True)

    # Per-profile hashtag bar
    profile_ht = pd_main.get("hashtags",[])
    if profile_ht:
        ht_df = pd.DataFrame(profile_ht).head(12)
        fig8 = go.Figure(go.Bar(
            y=ht_df["tag"], x=ht_df["avg_engagement"],
            orientation="h",
            marker=dict(color=ht_df["avg_engagement"],
                        colorscale=[[0,COLORS[3]],[1,COLORS[0]]],
                        line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Avg Engagement: %{x:,.0f}<extra></extra>"
        ))
        lo = base_layout(320)
        lo["hovermode"] = "closest"
        lo["xaxis"] = dict(showgrid=True, gridcolor=GRID_COL, color=TICK_COL, tickfont=dict(size=10))
        lo["yaxis"] = dict(showgrid=False, color=TICK_COL, tickfont=dict(size=10))
        fig8.update_layout(**lo)
        st.plotly_chart(fig8, use_container_width=True)

    # Global hashtag lookup results (manual + auto, with post counts)
    if hashtags_data:
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">🌐 Tracked Hashtag Deep-Dive</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Volume & engagement for each tracked tag (HasData lookup)</div>', unsafe_allow_html=True)

        ht_rows = []
        for tag, d in hashtags_data.items():
            ht_rows.append({
                "Hashtag":       tag,
                "Total Posts":   format_number(d.get("posts_count",0)),
                "Avg Likes":     format_number(d.get("avg_likes",0)),
                "Avg Comments":  format_number(d.get("avg_comments",0)),
                "Avg Engagement":format_number(d.get("avg_engagement",0)),
            })
        if ht_rows:
            ht_table_df = pd.DataFrame(ht_rows)
            st.dataframe(ht_table_df, use_container_width=True, hide_index=True)

        # Volume bar chart
        vol_data = [(t, d.get("posts_count",0)) for t,d in hashtags_data.items() if d.get("posts_count",0)>0]
        if vol_data:
            vol_df = pd.DataFrame(vol_data, columns=["tag","posts_count"]).sort_values("posts_count",ascending=False)
            fig9 = go.Figure(go.Bar(
                x=vol_df["tag"], y=vol_df["posts_count"],
                marker=dict(color=COLORS[0], opacity=0.8, line=dict(width=0)),
                hovertemplate="<b>%{x}</b><br>Total Posts: %{y:,.0f}<extra></extra>"
            ))
            fig9.update_layout(**base_layout(240),
                               xaxis=dict(tickangle=-30, tickfont=dict(size=10), color=TICK_COL),
                               hovermode="closest")
            st.markdown('<div class="section-title">📦 Hashtag Volume (total posts on Instagram)</div>', unsafe_allow_html=True)
            st.plotly_chart(fig9, use_container_width=True)

        # Display chips
        st.markdown("**Auto-extracted hashtags from post captions:**")
        chips_html = " ".join(f'<span class="tag-chip">{t}</span>' for t in hashtags_data.keys())
        st.markdown(f'<div style="line-height:2.2">{chips_html}</div>', unsafe_allow_html=True)

    else:
        st.markdown('<div class="warn-pill">No hashtag data available. Add hashtags in the sidebar (Hashtag Tracking mode) or switch to live API mode.</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 5 — COMPETITOR BENCH  (only in competitor mode)
# ─────────────────────────────────────────────────────────────────────────────
if input_mode == "Competitor Comparison":
    with tabs[4]:
        st.markdown('<div class="section-title">⚔️ Head-to-Head Comparison</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Side-by-side benchmarking across up to 3 profiles</div>', unsafe_allow_html=True)

        comp_rows = []
        for u in usernames:
            d = profiles_data.get(u, {})
            comp_rows.append({
                "Profile":         f"@{u}",
                "Verified":        "✅" if d.get("verified") else "—",
                "Followers":       d.get("followers",0),
                "Eng. Rate (%)":   d.get("engagement_rate",0),
                "Avg Likes":       d.get("avg_likes",0),
                "Avg Comments":    d.get("avg_comments",0),
                "Reel ER (%)":     d.get("reel_er",0),
                "Avg Reach":       d.get("avg_reach",0),
                "Posts":           d.get("total_posts",0),
            })
        comp_df = pd.DataFrame(comp_rows)

        # Grouped bars — key engagement metrics
        ba, bb = st.columns([3,2])
        with ba:
            fig10 = go.Figure()
            for i, row in comp_df.iterrows():
                fig10.add_trace(go.Bar(
                    name=row["Profile"],
                    x=["ER (%)","Reel ER (%)"],
                    y=[row["Eng. Rate (%)"], row["Reel ER (%)"]],
                    marker_color=COLORS[i % len(COLORS)],
                    marker_line=dict(width=0),
                    hovertemplate=f"<b>{row['Profile']}</b><br>%{{x}}: %{{y:.2f}}%<extra></extra>"
                ))
            fig10.update_layout(barmode="group", **base_layout(300),
                                legend=dict(orientation="h",y=1.1,
                                            font=dict(color=FONT_COL,size=11),
                                            bgcolor="rgba(0,0,0,0)"))
            st.markdown('<div class="section-title">Engagement Rate Comparison</div>', unsafe_allow_html=True)
            st.plotly_chart(fig10, use_container_width=True)

        with bb:
            fig11 = go.Figure(go.Bar(
                x=comp_df["Followers"],
                y=comp_df["Profile"],
                orientation="h",
                marker=dict(color=COLORS[:len(comp_df)], line=dict(width=0)),
                hovertemplate="<b>%{y}</b><br>%{x:,.0f} followers<extra></extra>"
            ))
            fig11.update_layout(
                **{k:v for k,v in base_layout(300).items()},
                xaxis=dict(showgrid=True,gridcolor=GRID_COL,color=TICK_COL,tickfont=dict(size=10)),
                yaxis=dict(showgrid=False,color=TICK_COL,tickfont=dict(size=11)),
                hovermode="closest",
                title=dict(text="Follower Count",font=dict(color=FONT_COL,size=12),x=0)
            )
            st.markdown('<div class="section-title">Follower Count</div>', unsafe_allow_html=True)
            st.plotly_chart(fig11, use_container_width=True)

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # Avg likes comparison
        fig12 = go.Figure()
        for metric, color in [("Avg Likes",COLORS[0]),("Avg Comments",COLORS[1])]:
            fig12.add_trace(go.Bar(
                name=metric, x=comp_df["Profile"], y=comp_df[metric],
                marker_color=color, marker_line=dict(width=0),
                hovertemplate=f"<b>%{{x}}</b><br>{metric}: %{{y:,.0f}}<extra></extra>"
            ))
        fig12.update_layout(barmode="group", **base_layout(240),
                            legend=dict(orientation="h",y=1.12,
                                        font=dict(color=FONT_COL,size=11),
                                        bgcolor="rgba(0,0,0,0)"))
        st.markdown('<div class="section-title">Avg Likes & Comments per Post</div>', unsafe_allow_html=True)
        st.plotly_chart(fig12, use_container_width=True)

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # Full comparison table
        st.markdown('<div class="section-title">📋 Full Metrics Table</div>', unsafe_allow_html=True)
        display_df = comp_df.copy()
        display_df["Followers"] = display_df["Followers"].apply(format_number)
        display_df["Avg Reach"]  = display_df["Avg Reach"].apply(format_number)
        display_df["Avg Likes"]  = display_df["Avg Likes"].apply(format_number)
        display_df["Avg Comments"] = display_df["Avg Comments"].apply(format_number)
        st.dataframe(display_df, use_container_width=True, hide_index=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<hr style='border:none;border-top:1px solid #1a1a2e;margin:28px 0 10px'>", unsafe_allow_html=True)
st.markdown("""<p style='text-align:center;color:#2e2e4a;font-size:10px;letter-spacing:1px'>
INSTALENS v3.0 · HASDATA API · STREAMLIT · PLOTLY · FOR PROFESSIONAL SOCIAL MEDIA ANALYTICS
</p>""", unsafe_allow_html=True)
