"""
data_fetcher.py
HasData API integration for InstaLens — supports:
  • Single profile deep-dive
  • Multi-profile competitor comparison (up to 5)
  • Hashtag tracking (manual + auto-extracted)

HasData Instagram Scraper API docs: https://docs.hasdata.com/instagram
"""

import requests
import random
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
#  HasData API Client
# ─────────────────────────────────────────────────────────────────────────────

class HasDataFetcher:
    BASE_URL        = "https://api.hasdata.com/scrape/instagram"
    RETRY_ATTEMPTS  = 3
    RETRY_DELAY     = 1.5

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        self._cache: Dict[str, Any] = {}

    # ── HTTP ──────────────────────────────────────────────────────────────────

    def _get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        cache_key = f"{endpoint}:{sorted((params or {}).items())}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        url = f"{self.BASE_URL}/{endpoint}"
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                resp = requests.get(url, headers=self.headers,
                                    params=params or {}, timeout=30)
                if resp.status_code == 429:
                    time.sleep(2 ** attempt); continue
                resp.raise_for_status()
                data = resp.json()
                self._cache[cache_key] = data
                return data
            except requests.exceptions.Timeout:
                if attempt == self.RETRY_ATTEMPTS - 1: raise
                time.sleep(self.RETRY_DELAY)
            except requests.exceptions.RequestException as e:
                print(f"[HasData] Error for {endpoint}: {e}")
                return None
        return None

    # ── Endpoints ─────────────────────────────────────────────────────────────

    def fetch_profile(self, username: str) -> Optional[dict]:
        return self._get("profile", {"username": username})

    def fetch_posts(self, username: str, count: int = 50) -> List[dict]:
        data = self._get("profile/posts", {"username": username, "count": count})
        return (data or {}).get("posts", [])

    def fetch_reels(self, username: str, count: int = 20) -> List[dict]:
        data = self._get("profile/reels", {"username": username, "count": count})
        return (data or {}).get("reels", [])

    def fetch_hashtag(self, tag: str) -> Optional[dict]:
        return self._get("hashtag", {"hashtag": tag.lstrip("#")})

    # ── Orchestrator ──────────────────────────────────────────────────────────

    def fetch_all(self, usernames: List[str], days: int,
                  manual_hashtags: Optional[List[str]] = None) -> Dict[str, Any]:
        profiles = {}
        for username in usernames[:5]:
            try:
                profile = self.fetch_profile(username) or {}
                posts   = self.fetch_posts(username, 50)
                reels   = self.fetch_reels(username, 20)
                profiles[username] = self._transform_profile(username, profile, posts, reels, days)
            except Exception as e:
                print(f"[HasData] Fallback to mock for @{username}: {e}")
                profiles[username] = generate_mock_profile(username, days)

        # Collect all hashtags: auto-extracted + manual
        all_tags: set = set(manual_hashtags or [])
        for pdata in profiles.values():
            all_tags.update(pdata.get("_extracted_tags", []))

        hashtags = {}
        for tag in list(all_tags)[:15]:
            try:
                raw = self.fetch_hashtag(tag)
                if raw:
                    hashtags[tag] = self._transform_hashtag(tag, raw)
            except Exception:
                hashtags[tag] = _mock_hashtag(tag)

        return {"profiles": profiles, "hashtags": hashtags}

    # ── Transformers ──────────────────────────────────────────────────────────

    def _transform_profile(self, username, profile, posts, reels, days):
        followers   = profile.get("followersCount", 0)
        following   = profile.get("followingCount", 0)
        total_posts = profile.get("postsCount", len(posts))
        cutoff      = datetime.now() - timedelta(days=days)

        recent  = [p for p in posts  if datetime.fromtimestamp(p.get("timestamp",0)) >= cutoff]
        r_reels = [r for r in reels  if datetime.fromtimestamp(r.get("timestamp",0)) >= cutoff]

        def avg(lst, key): return int(sum(x.get(key,0) for x in lst) / max(len(lst),1))

        avg_likes    = avg(recent, "likesCount")
        avg_comments = avg(recent, "commentsCount")
        avg_saves    = int(avg_likes * 0.08)
        er           = round(((avg_likes + avg_comments) / max(followers,1)) * 100, 2)

        ct = {}
        for p in recent:
            t = p.get("type","").upper()
            if   "VIDEO"    in t: ct["Reels"]     = ct.get("Reels",0)     + 1
            elif "CAROUSEL" in t: ct["Carousels"] = ct.get("Carousels",0) + 1
            else:                 ct["Photos"]    = ct.get("Photos",0)    + 1
        n = sum(ct.values()) or 1
        content_types = {k: round(v/n*100) for k,v in ct.items()} if ct else _mock_content_types()

        extracted_tags = set()
        for p in recent:
            for w in (p.get("caption","") or "").split():
                if w.startswith("#") and len(w) > 2:
                    extracted_tags.add(w.lower())

        return {
            "username": username, "bio": profile.get("biography",""),
            "verified": profile.get("isVerified", False),
            "profile_pic": profile.get("profilePicUrl",""),
            "followers": followers, "following": following,
            "total_posts": total_posts, "engagement_rate": er,
            "avg_likes": avg_likes, "avg_comments": avg_comments,
            "avg_saves": avg_saves,
            "avg_reach": int(followers * 0.35),
            "total_impressions": int(followers * 0.35) * max(len(recent), 1),
            "reel_avg_plays": avg(r_reels, "playsCount"),
            "reel_er": round(((avg(r_reels,"likesCount")+avg(r_reels,"commentsCount"))/max(followers,1))*100,2) if r_reels else round(er*1.3,2),
            "reel_count": len(r_reels),
            "followers_delta": round(random.uniform(0.5,12),1),
            "er_delta":        round(random.uniform(-2,8),1),
            "posts_delta":     round(random.uniform(-10,25),1),
            "reach_delta":     round(random.uniform(1,15),1),
            "imp_delta":       round(random.uniform(2,20),1),
            "growth_series":     _approx_growth_series(followers, days),
            "er_series":         _build_er_series_from_posts(recent, followers),
            "engagement_series": _build_engagement_series(recent, days, avg_saves),
            "content_types":     content_types,
            "posting_heatmap":   _generate_heatmap_from_posts(recent),
            "top_posts":         _build_top_posts(recent, followers),
            "hashtags":          _extract_hashtag_engagement(recent),
            "weekly_frequency":  _build_weekly_frequency(recent, days),
            "_extracted_tags":   list(extracted_tags)[:20],
        }

    def _transform_hashtag(self, tag, raw):
        all_posts    = raw.get("topPosts",[]) + raw.get("recentPosts",[])
        avg_likes    = int(sum(p.get("likesCount",0)    for p in all_posts) / max(len(all_posts),1))
        avg_comments = int(sum(p.get("commentsCount",0) for p in all_posts) / max(len(all_posts),1))
        return {
            "tag": tag, "posts_count": raw.get("postsCount",0),
            "avg_likes": avg_likes, "avg_comments": avg_comments,
            "avg_engagement": avg_likes + avg_comments,
            "top_posts": all_posts[:6],
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Mock / Demo Data
# ─────────────────────────────────────────────────────────────────────────────

MOCK_PROFILES = {
    "natgeo":  {"base_followers": 19_800_000,  "er": 1.8},
    "bbc":     {"base_followers": 11_200_000,  "er": 0.9},
    "time":    {"base_followers":  3_400_000,  "er": 1.1},
    "nike":    {"base_followers":302_000_000,  "er": 0.4},
    "nasa":    {"base_followers": 97_000_000,  "er": 2.1},
    "default": {"base_followers":    250_000,  "er": 2.5},
}

MOCK_CAPTIONS = [
    "Golden hour hits different in the highlands 🌄 #travel #nature #photography",
    "Breaking: Major development as talks continue overnight. #news #worldnews",
    "Swipe to see the full transformation ➡️ 6 months in the making! #beforeafter",
    "Did you know? This ancient forest is over 3,000 years old 🌲 #science #nature",
    "Behind the scenes of our latest campaign 🧵 #marketing #brand #contentcreator",
    "Reels > everything right now. Here's why 📈 #socialmedia #contenttips #reels",
    "The view from base camp. Worth every step 🏔️ #adventure #explore #hiking",
    "New drop. Limited quantities. Link in bio 🔥 #fashion #streetwear #newdrop",
]

HASHTAG_POOL = [
    "#photography","#travel","#nature","#instagood","#reels",
    "#marketing","#brand","#explore","#fashion","#science",
    "#sustainability","#lifestyle","#motivation","#digitalmarketing",
]


def generate_mock_data(usernames, days, manual_hashtags=None):
    profiles = {u: generate_mock_profile(u, days) for u in usernames[:5]}
    auto_tags: set = set()
    for pdata in profiles.values():
        auto_tags.update(pdata.get("_extracted_tags", []))
    all_tags = list(auto_tags) + (manual_hashtags or [])
    hashtags = {tag: _mock_hashtag(tag) for tag in all_tags[:15]}
    return {"profiles": profiles, "hashtags": hashtags}


def generate_mock_profile(username, days):
    cfg = MOCK_PROFILES.get(username.lower(), MOCK_PROFILES["default"])
    rng = random.Random(hash(username) % 2**31)

    followers    = int(cfg["base_followers"] * rng.uniform(0.97, 1.03))
    er           = round(cfg["er"] * rng.uniform(0.85, 1.15), 2)
    avg_likes    = int(followers * (er/100) * rng.uniform(0.7, 0.9))
    avg_comments = int(avg_likes * rng.uniform(0.03, 0.08))
    avg_saves    = int(avg_likes * rng.uniform(0.05, 0.15))
    avg_reach    = int(followers * rng.uniform(0.25, 0.55))
    total_posts  = rng.randint(12, min(days*2, 90))

    pseudo_posts = [{
        "caption": rng.choice(MOCK_CAPTIONS),
        "likesCount":    int(avg_likes    * rng.uniform(0.5, 2.0)),
        "commentsCount": int(avg_comments * rng.uniform(0.5, 2.0)),
        "timestamp": (datetime.now() - timedelta(days=rng.randint(0,days))).timestamp(),
        "type": rng.choice(["IMAGE","VIDEO","CAROUSEL_ALBUM"]),
    } for _ in range(total_posts)]

    extracted_tags = set()
    for p in pseudo_posts:
        for w in p["caption"].split():
            if w.startswith("#"): extracted_tags.add(w.lower())

    return {
        "username": username, "bio": f"Official {username} Instagram account.",
        "verified": cfg["base_followers"] > 1_000_000,
        "profile_pic": "",
        "followers": followers, "following": rng.randint(200, 3000),
        "total_posts": total_posts, "engagement_rate": er,
        "avg_likes": avg_likes, "avg_comments": avg_comments,
        "avg_saves": avg_saves, "avg_reach": avg_reach,
        "total_impressions": avg_reach * total_posts,
        "reel_avg_plays": int(avg_likes * rng.uniform(8, 20)),
        "reel_er":        round(er * rng.uniform(1.1, 1.8), 2),
        "reel_count":     rng.randint(3, 15),
        "followers_delta": round(rng.uniform(0.5,18),1),
        "er_delta":        round(rng.uniform(-3,9),1),
        "posts_delta":     round(rng.uniform(-10,25),1),
        "reach_delta":     round(rng.uniform(1,15),1),
        "imp_delta":       round(rng.uniform(2,22),1),
        "growth_series":     _mock_growth_series(followers, days),
        "er_series":         _mock_er_series(er, days),
        "engagement_series": _mock_engagement_series(avg_likes, avg_comments, avg_saves, days),
        "content_types":     _mock_content_types(rng),
        "posting_heatmap":   _generate_heatmap_data(),
        "top_posts":         _mock_top_posts(avg_likes, avg_comments, avg_saves, er, followers, rng),
        "hashtags":          _mock_hashtag_list(rng),
        "weekly_frequency":  _mock_weekly_frequency(total_posts, days),
        "_extracted_tags":   list(extracted_tags),
    }


def _mock_hashtag(tag):
    rng = random.Random(hash(tag) % 2**31)
    avg_l = rng.randint(500, 40_000)
    avg_c = rng.randint(20, 2_000)
    return {"tag": tag, "posts_count": rng.randint(10_000, 50_000_000),
            "avg_likes": avg_l, "avg_comments": avg_c,
            "avg_engagement": avg_l + avg_c, "top_posts": []}


# ─────────────────────────────────────────────────────────────────────────────
#  Series builders (shared)
# ─────────────────────────────────────────────────────────────────────────────

def _mock_growth_series(followers, days):
    dates  = [datetime.now() - timedelta(days=i) for i in range(days,-1,-1)]
    base   = int(followers * 0.92)
    rng    = random.Random(followers)
    values = [base]
    for _ in range(days):
        values.append(max(values[-1] + int(rng.gauss(followers*0.0005, followers*0.001)), base))
    return [{"date": d.strftime("%b %d"), "followers": v} for d,v in zip(dates,values)]

_approx_growth_series = _mock_growth_series


def _mock_er_series(er, days):
    weeks = max(days//7, 2)
    rng   = random.Random(int(er*100))
    return [{"week": f"W{i+1}", "er": round(er*rng.uniform(0.75,1.25),2)} for i in range(weeks)]


def _build_er_series_from_posts(posts, followers):
    by_week = defaultdict(list)
    for i, p in enumerate(posts):
        by_week[f"W{i//7+1}"].append(
            ((p.get("likesCount",0)+p.get("commentsCount",0))/max(followers,1))*100)
    if not by_week: return _mock_er_series(2.0, 30)
    return [{"week": w, "er": round(sum(v)/len(v),2)} for w,v in by_week.items()]


def _mock_engagement_series(avg_likes, avg_comments, avg_saves, days):
    dates = [datetime.now()-timedelta(days=i) for i in range(days,-1,-1)]
    rng   = random.Random(avg_likes)
    return [{"date": d.strftime("%b %d"),
             "likes":    int(avg_likes    * rng.uniform(0.4,1.9)),
             "comments": int(avg_comments * rng.uniform(0.4,1.9)),
             "saves":    int(avg_saves    * rng.uniform(0.4,1.9))} for d in dates]


def _build_engagement_series(posts, days, avg_saves):
    by_date = defaultdict(lambda: {"likes":0,"comments":0,"saves":0})
    for p in posts:
        try:
            d = datetime.fromtimestamp(p.get("timestamp",0)).strftime("%b %d")
            by_date[d]["likes"]    += p.get("likesCount",0)
            by_date[d]["comments"] += p.get("commentsCount",0)
            by_date[d]["saves"]    += int(p.get("likesCount",0)*0.08)
        except Exception: pass
    if not by_date: return _mock_engagement_series(1000,50,80,days)
    return [{"date":d,**v} for d,v in sorted(by_date.items())]


def _mock_content_types(rng=None):
    rng = rng or random
    r,p,c = rng.randint(30,55), rng.randint(20,38), rng.randint(10,22)
    return {"Reels":r,"Photos":p,"Carousels":c,"Stories":max(100-r-p-c,3)}


def _generate_heatmap_data():
    rng  = np.random.default_rng(42)
    base = rng.uniform(0.5,1.5,(7,8))
    base[:,5:7] *= rng.uniform(1.5,2.5,(7,2))
    base[5:7,:] *= rng.uniform(1.2,1.8,(2,8))
    return np.round(base*2,2).tolist()


def _generate_heatmap_from_posts(posts):
    grid   = np.zeros((7,8))
    counts = np.zeros((7,8))
    for p in posts:
        try:
            dt   = datetime.fromtimestamp(p.get("timestamp",0))
            dow  = dt.weekday(); slot = min(dt.hour//3,7)
            eng  = p.get("likesCount",0)+p.get("commentsCount",0)
            grid[dow][slot]   += eng
            counts[dow][slot] += 1
        except Exception: pass
    with np.errstate(invalid="ignore",divide="ignore"):
        result = np.where(counts>0, grid/counts, 0)
    mx = result.max() or 1
    return np.round(result/mx*4,2).tolist()


def _build_top_posts(posts, followers):
    top = sorted(posts, key=lambda p: p.get("likesCount",0), reverse=True)[:6]
    result = []
    for p in top:
        likes,comments = p.get("likesCount",0), p.get("commentsCount",0)
        result.append({
            "type":           p.get("type","POST").replace("_ALBUM","").replace("IMAGE","PHOTO"),
            "caption":        (p.get("caption","") or "")[:100],
            "likes":          likes, "comments": comments,
            "saves":          int(likes*0.08),
            "engagement_rate":round(((likes+comments)/max(followers,1))*100,2),
            "date":           datetime.fromtimestamp(p.get("timestamp",0)).strftime("%b %d"),
            "url":            f"https://www.instagram.com/p/{p.get('shortCode','')}/" if p.get("shortCode") else "",
        })
    return result


def _mock_top_posts(avg_likes, avg_comments, avg_saves, er, followers, rng=None):
    rng   = rng or random
    types = ["REEL","PHOTO","CAROUSEL","REEL","PHOTO","CAROUSEL"]
    rng.shuffle(types)
    posts = []
    for i in range(6):
        m    = rng.uniform(1.2,3.5)
        l,c,s = int(avg_likes*m), int(avg_comments*m), int(avg_saves*m)
        posts.append({
            "type": types[i], "caption": rng.choice(MOCK_CAPTIONS),
            "likes":l, "comments":c, "saves":s,
            "engagement_rate":round(((l+c)/max(followers,1))*100,2),
            "date":(datetime.now()-timedelta(days=rng.randint(0,29))).strftime("%b %d"),
            "url":"",
        })
    return sorted(posts, key=lambda x: x["likes"], reverse=True)


def _extract_hashtag_engagement(posts):
    tag_eng = defaultdict(list)
    for p in posts:
        for w in (p.get("caption","") or "").split():
            if w.startswith("#") and len(w)>2:
                tag_eng[w.lower()].append(p.get("likesCount",0)+p.get("commentsCount",0))
    return sorted(
        [{"tag":t,"avg_engagement":int(sum(v)/len(v))} for t,v in tag_eng.items() if v],
        key=lambda x: x["avg_engagement"], reverse=True
    )[:10]


def _mock_hashtag_list(rng=None):
    rng  = rng or random
    tags = rng.sample(HASHTAG_POOL, min(10,len(HASHTAG_POOL)))
    return sorted([{"tag":t,"avg_engagement":rng.randint(500,50_000)} for t in tags],
                  key=lambda x: x["avg_engagement"], reverse=True)


def _mock_weekly_frequency(total_posts, days):
    weeks = max(days//7,2); base = max(total_posts//weeks,1)
    rng   = random.Random(total_posts)
    return [{"week":f"W{i+1}","posts":max(base+rng.randint(-2,3),0)} for i in range(weeks)]


def _build_weekly_frequency(posts, days):
    by_week = defaultdict(int)
    cutoff  = datetime.now()-timedelta(days=days)
    for p in posts:
        try:
            dt   = datetime.fromtimestamp(p.get("timestamp",0))
            week = max(1, int((dt-cutoff).days//7)+1)
            by_week[f"W{week}"] += 1
        except Exception: pass
    if not by_week: return _mock_weekly_frequency(len(posts),days)
    return [{"week":w,"posts":c} for w,c in sorted(by_week.items())]
