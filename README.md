# 📸 InstaLens v2 — Instagram Analytics Dashboard

A production-grade Instagram analytics platform for social media agencies. Built with the **HasData Instagram Scraper API**, **Streamlit**, and **Plotly**. Supports three distinct data input modes and covers every major Instagram metric.

---

## 🚀 Features

### Three Input Modes
| Mode | Description |
|---|---|
| **Single Profile** | Deep-dive analytics for one Instagram account |
| **Competitor Comparison** | Side-by-side benchmarking of up to 5 profiles |
| **Hashtag Tracking** | Manual hashtag lookup + auto-extract from captions |

### Metrics Covered
| Category | Metrics |
|---|---|
| **Followers & Growth** | Count, daily trend, period delta, follower/following ratio |
| **Engagement** | Rate (%), likes, comments, saves, weekly ER trend |
| **Reach & Impressions** | Avg reach/post, total impressions, deltas |
| **Stories & Reels** | Avg plays, Reel ER, Reel vs Post ER lift, count |
| **Content Mix** | Reels / Photos / Carousels / Stories donut |
| **Timing** | Day×Hour engagement heatmap, weekly frequency |
| **Hashtags** | Per-post extraction, global volume, avg engagement |
| **Benchmarking** | ER benchmark by follower tier, competitor table |

---

## 🛠️ Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/instalens-dashboard.git
cd instalens-dashboard
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open **http://localhost:8501** — works instantly in **Demo Mode** (no API key needed).

---

## 🔑 HasData API — Live Mode

### Setup
1. Sign up at [hasdata.com](https://hasdata.com) and grab your API key
2. In InstaLens sidebar: toggle **Demo Mode OFF** → paste your key
3. Enter usernames / hashtags → click **Analyse**

### Endpoints Used

| Endpoint | What it returns |
|---|---|
| `GET /scrape/instagram/profile?username=X` | Followers, following, bio, verified status |
| `GET /scrape/instagram/profile/posts?username=X&count=50` | Post list: likes, comments, type, caption, timestamp |
| `GET /scrape/instagram/profile/reels?username=X&count=20` | Reels: plays, likes, comments, duration |
| `GET /scrape/instagram/hashtag?hashtag=X` | Total posts, top posts, recent posts for a tag |

Full docs: **https://docs.hasdata.com/instagram**

### Using Secrets (Streamlit Cloud)
Add to `Settings → Secrets`:
```toml
HASDATA_API_KEY = "hd_your_key_here"
```
Then in `app.py` auto-load it:
```python
api_key = st.secrets.get("HASDATA_API_KEY") or None
```

---

## ☁️ Deploy to Streamlit Cloud (Free)

1. Push repo to GitHub (include `.streamlit/config.toml`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Connect repo, set main file to `app.py`
4. Add secret `HASDATA_API_KEY` under Advanced Settings
5. **Deploy** — live in ~60 seconds

---

## 📁 Structure

```
instalens-dashboard/
├── app.py                       # Streamlit UI — 4+ tab layout
├── data_fetcher.py              # HasData API client + mock data generator
├── utils.py                     # Formatting, ER calc, benchmarking
├── requirements.txt
├── .streamlit/
│   └── config.toml              # Dark theme
├── .github/
│   └── workflows/ci.yml         # GitHub Actions CI
└── README.md
```

---

## 📐 ER Benchmarks by Account Size

| Tier | Followers | Good ER |
|---|---|---|
| Nano | < 10K | > 5% |
| Micro | 10K–100K | > 3.5% |
| Mid | 100K–1M | > 2.5% |
| Macro | 1M+ | > 1.5% |

---

## 🔮 Roadmap
- [ ] PDF one-click report export
- [ ] Automated email digests (weekly/monthly)
- [ ] Stories analytics (requires Instagram Business API)
- [ ] AI caption & hashtag recommendations
- [ ] SQLite historical data storage
- [ ] Later / Buffer scheduling integration

---

## 📄 License
MIT — free for personal and commercial use.
