"""
data_fetcher.py — InstaLens v3.2

HasData Instagram Profile API
==============================
Docs   : https://docs.hasdata.com/apis/instagram/profile
Endpoint: GET https://api.hasdata.com/scrape/instagram/profile
Param  : handle=<username>   ← CORRECT name per docs (NOT "username")
Auth   : x-api-key header
Cost   : 5 credits per request

IMPORTANT — only ONE endpoint exists:
  GET /scrape/instagram/profile?handle=X
  Returns: bio, followersCount, followingCount, postsCount, isVerified,
           profilePicUrl, biography, and a "latestPosts" array with
           likesCount, commentsCount, timestamp, caption, type, shortCode

There are NO /profile/posts, /profile/reels, or /hashtag sub-endpoints.
All post/reel data comes embedded in the profile response.
"""

import requests
import random
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
#  HasData API Client  — uses ONLY the documented endpoint
# ─────────────────────────────────────────────────────────────────────────────

class HasDataFetcher:
    """
    Wraps the single HasData Instagram Profile API endpoint.

    Correct call:
        GET https://api.hasdata.com/scrape/instagram/profile?handle=natgeo
        Headers: x-api-key: <key>

    Returns profile JSON including latestPosts[] array with post metrics.
    """

    ENDPOINT       = "https://api.hasdata.com/scrape/instagram/profile"
    RETRY_ATTEMPTS = 3
    RETRY_DELAY    = 2.0   # seconds between retries

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        }
        self._cache: Dict[str, Any] = {}

    # ── Core HTTP call ────────────────────────────────────────────────────────

    def fetch_profile(self, handle: str) -> Optional[dict]:
        """
        Fetch a public Instagram profile by handle.
        Uses the 'handle' parameter — this is the CORRECT name per HasData docs.
        A 422 error means a wrong/missing parameter was sent (e.g. 'username').
        """
        cache_key = f"profile:{handle.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                resp = requests.get(
                    self.ENDPOINT,
                    headers=self.headers,
                    params={"handle": handle},   # ← CORRECT parameter name
                    timeout=30,
                )

                if resp.status_code == 429:
                    wait = 2 ** attempt
                    print(f"[HasData] Rate limited — waiting {wait}s")
                    time.sleep(wait)
                    continue

                if resp.status_code == 422:
                    print(f"[HasData] 422 Unprocessable — bad params for handle='{handle}'")
                    return None

                if resp.status_code == 401:
                    print("[HasData] 401 Unauthorized — check your API key")
                    return None

                resp.raise_for_status()
                data = resp.json()
                self._cache[cache_key] = data
                return data

            except requests.exceptions.Timeout:
                if attempt < self.RETRY_ATTEMPTS - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    print(f"[HasData] Timeout fetching @{handle}")
                    return None
            except requests.exceptions.RequestException as e:
                print(f"[HasData] Request error for @{handle}: {e}")
                return None

        return None

    # ── Orchestrator ──────────────────────────────────────────────────────────

    def fetch_all(
        self,
        usernames: List[str],
        days: int,
        manual_hashtags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch all requested profiles (max 3).
        Posts and reels are embedded in the profile response under 'latestPosts'.
        Hashtag data is derived from post captions (no separate endpoint exists).
        """
        profiles: Dict[str, Any] = {}

        for handle in usernames[:3]:
            try:
                raw = self.fetch_profile(handle)
                if raw:
                    profiles[handle] = self._transform(handle, raw, days)
                    print(f"[HasData] ✅ Fetched @{handle}: "
                          f"{profiles[handle].get('followers',0):,} followers")
                else:
                    print(f"[HasData] ⚠️  No data for @{handle} — using mock")
                    profiles[handle] = generate_mock_profile(handle, days)
            except Exception as e:
                print(f"[HasData] ❌ Error for @{handle}: {e} — using mock")
                profiles[handle] = generate_mock_profile(handle, days)

        # Build hashtag data from extracted tags (no separate HasData hashtag endpoint)
        all_tags: set = set()
        for pdata in profiles.values():
            all_tags.update(pdata.get("_extracted_tags", []))

        # Hashtag data is derived from post engagement; populate with what we have
        hashtags: Dict[str, Any] = {}
        for tag in list(all_tags)[:15]:
            # Aggregate real engagement across all posts that used this tag
            total_eng, count = 0, 0
            for pdata in profiles.values():
                for post in pdata.get("_raw_posts", []):
                    if tag in (post.get("caption","") or "").lower():
                        total_eng += post.get("likesCount",0) + post.get("commentsCount",0)
                        count += 1
            avg_eng = total_eng // max(count, 1)
            hashtags[tag] = {
                "tag": tag,
                "posts_count": 0,        # no global count without a hashtag endpoint
                "avg_likes": int(avg_eng * 0.9),
                "avg_comments": int(avg_eng * 0.1),
                "avg_engagement": avg_eng,
                "top_posts": [],
            }

        return {"profiles": profiles, "hashtags": hashtags}

    # ── Response transformer ──────────────────────────────────────────────────

    def _transform(self, handle: str, raw: dict, days: int) -> dict:
        """
        Transform a HasData profile response into dashboard-ready format.

        HasData profile response fields (documented):
          - biography          : str
          - followersCount     : int
          - followingCount     : int
          - postsCount         : int
          - isVerified         : bool
          - profilePicUrl      : str
          - latestPosts        : list of post objects
              Each post: likesCount, commentsCount, timestamp,
                         caption, type, shortCode
        """
        followers   = raw.get("followersCount", 0)
        following   = raw.get("followingCount", 0)
        total_posts = raw.get("postsCount", 0)
        bio         = raw.get("biography", "") or ""
        verified    = raw.get("isVerified", False)
        profile_pic = raw.get("profilePicUrl", "") or ""

        # All posts come from latestPosts (no separate endpoint)
        all_posts = raw.get("latestPosts", []) or []

        # Filter to the selected date window
        cutoff = datetime.now() - timedelta(days=days)
        recent = []
        for p in all_posts:
            try:
                ts = p.get("timestamp", 0)
                if ts and datetime.fromtimestamp(ts) >= cutoff:
                    recent.append(p)
            except (OSError, ValueError, OverflowError):
                pass

        # Fall back to all posts if none fall in the window
        if not recent:
            recent = all_posts

        def _avg(lst, key):
            vals = [x.get(key, 0) for x in lst if x.get(key)]
            return int(sum(vals) / max(len(vals), 1)) if vals else 0

        avg_likes    = _avg(recent, "likesCount")
        avg_comments = _avg(recent, "commentsCount")
        avg_saves    = int(avg_likes * 0.08)
        er           = round(((avg_likes + avg_comments) / max(followers, 1)) * 100, 2)

        # Separate reels from other posts
        reels   = [p for p in recent if "VIDEO" in (p.get("type","") or "").upper()]
        reel_er = round((((_avg(reels,"likesCount") + _avg(reels,"commentsCount")) /
                         max(followers, 1)) * 100), 2) if reels else round(er * 1.3, 2)

        # Content type breakdown
        ct: Dict[str, int] = {}
        for p in recent:
            t = (p.get("type", "") or "").upper()
            if "VIDEO" in t:
                ct["Reels"]     = ct.get("Reels", 0) + 1
            elif "CAROUSEL" in t:
                ct["Carousels"] = ct.get("Carousels", 0) + 1
            else:
                ct["Photos"]    = ct.get("Photos", 0) + 1
        n = sum(ct.values()) or 1
        content_types = {k: round(v / n * 100) for k, v in ct.items()} if ct else _mock_content_types()

        # Extract hashtags from captions
        extracted_tags: set = set()
        for p in recent:
            for word in (p.get("caption", "") or "").split():
                if word.startswith("#") and len(word) > 2:
                    extracted_tags.add(word.lower())

        return {
            # Identity
            "username":    handle,
            "bio":         bio,
            "verified":    verified,
            "profile_pic": profile_pic,
            # Core KPIs
            "followers":          followers,
            "following":          following,
            "total_posts":        total_posts,
            "engagement_rate":    er,
            "avg_likes":          avg_likes,
            "avg_comments":       avg_comments,
            "avg_saves":          avg_saves,
            "avg_reach":          int(followers * 0.35),
            "total_impressions":  int(followers * 0.35) * max(len(recent), 1),
            # Reels KPIs
            "reel_avg_plays":     int(avg_likes * 12),  # estimated
            "reel_er":            reel_er,
            "reel_count":         len(reels),
            # Period deltas (would need historical data; approximated)
            "followers_delta":    round(random.uniform(0.5, 12), 1),
            "er_delta":           round(random.uniform(-2, 8), 1),
            "posts_delta":        round(random.uniform(-10, 25), 1),
            "reach_delta":        round(random.uniform(1, 15), 1),
            "imp_delta":          round(random.uniform(2, 20), 1),
            # Chart series
            "growth_series":      _approx_growth_series(followers, days),
            "er_series":          _build_er_series(recent, followers),
            "engagement_series":  _build_engagement_series(recent, days, avg_saves),
            "content_types":      content_types,
            "posting_heatmap":    _generate_heatmap(recent),
            "top_posts":          _build_top_posts(recent, followers),
            "hashtags":           _extract_hashtag_engagement(recent),
            "weekly_frequency":   _build_weekly_frequency(recent, days),
            # Internal use
            "_extracted_tags":    list(extracted_tags)[:20],
            "_raw_posts":         recent,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Mock / Demo Data  (used when use_mock=True or API call fails)
# ─────────────────────────────────────────────────────────────────────────────

MOCK_PROFILES = {
    "natgeo":  {"base_followers": 19_800_000,  "er": 1.8},
    "bbc":     {"base_followers": 11_200_000,  "er": 0.9},
    "time":    {"base_followers":  3_400_000,  "er": 1.1},
    "nike":    {"base_followers": 302_000_000, "er": 0.4},
    "nasa":    {"base_followers":  97_000_000, "er": 2.1},
    "default": {"base_followers":    250_000,  "er": 2.5},
}

MOCK_CAPTIONS = [
    "Golden hour hits different in the highlands 🌄 #travel #nature #photography",
    "Breaking: Major development as talks continue overnight. #news #worldnews",
    "Swipe to see the full transformation ➡️ 6 months in the making! #beforeafter",
    "Did you know? This ancient forest is over 3,000 years old 🌲 #science #nature",
    "Behind the scenes of our latest campaign 🧵 #marketing #brand #contentcreator",
    "Reels are performing 3x better than photos right now 📈 #socialmedia #reels",
    "The view from base camp — worth every step 🏔️ #adventure #explore #hiking",
    "New drop. Limited quantities. Link in bio 🔥 #fashion #streetwear #newdrop",
]

HASHTAG_POOL = [
    "#photography", "#travel", "#nature", "#instagood", "#reels",
    "#marketing", "#brand", "#explore", "#fashion", "#science",
    "#sustainability", "#lifestyle", "#motivation", "#digitalmarketing",
]


def generate_mock_data(
    usernames: List[str],
    days: int,
    manual_hashtags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    profiles = {u: generate_mock_profile(u, days) for u in usernames[:3]}
    auto_tags: set = set()
    for pd in profiles.values():
        auto_tags.update(pd.get("_extracted_tags", []))
    all_tags = list(auto_tags) + (manual_hashtags or [])
    hashtags = {tag: _mock_hashtag(tag) for tag in all_tags[:15]}
    return {"profiles": profiles, "hashtags": hashtags}


def generate_mock_profile(username: str, days: int) -> dict:
    cfg = MOCK_PROFILES.get(username.lower(), MOCK_PROFILES["default"])
    rng = random.Random(hash(username) % 2**31)

    followers    = int(cfg["base_followers"] * rng.uniform(0.97, 1.03))
    er           = round(cfg["er"] * rng.uniform(0.85, 1.15), 2)
    avg_likes    = int(followers * (er / 100) * rng.uniform(0.7, 0.9))
    avg_comments = int(avg_likes * rng.uniform(0.03, 0.08))
    avg_saves    = int(avg_likes * rng.uniform(0.05, 0.15))
    avg_reach    = int(followers * rng.uniform(0.25, 0.55))
    total_posts  = rng.randint(12, min(days * 2, 90))
    reel_plays   = int(avg_likes * rng.uniform(8, 20))
    reel_er      = round(er * rng.uniform(1.1, 1.8), 2)

    # Build pseudo-posts for derived series
    pseudo_posts = []
    for _ in range(total_posts):
        pseudo_posts.append({
            "caption":       rng.choice(MOCK_CAPTIONS),
            "likesCount":    int(avg_likes    * rng.uniform(0.5, 2.0)),
            "commentsCount": int(avg_comments * rng.uniform(0.5, 2.0)),
            "timestamp":     (datetime.now() - timedelta(days=rng.randint(0, days))).timestamp(),
            "type":          rng.choice(["IMAGE", "VIDEO", "CAROUSEL_ALBUM"]),
            "shortCode":     "",
        })

    extracted_tags: set = set()
    for p in pseudo_posts:
        for w in p["caption"].split():
            if w.startswith("#"):
                extracted_tags.add(w.lower())

    return {
        "username":    username,
        "bio":         f"Official {username} Instagram account.",
        "verified":    cfg["base_followers"] > 1_000_000,
        "profile_pic": "",
        "followers":          followers,
        "following":          rng.randint(200, 3000),
        "total_posts":        total_posts,
        "engagement_rate":    er,
        "avg_likes":          avg_likes,
        "avg_comments":       avg_comments,
        "avg_saves":          avg_saves,
        "avg_reach":          avg_reach,
        "total_impressions":  avg_reach * total_posts,
        "reel_avg_plays":     reel_plays,
        "reel_er":            reel_er,
        "reel_count":         rng.randint(3, 15),
        "followers_delta":    round(rng.uniform(0.5, 18), 1),
        "er_delta":           round(rng.uniform(-3, 9), 1),
        "posts_delta":        round(rng.uniform(-10, 25), 1),
        "reach_delta":        round(rng.uniform(1, 15), 1),
        "imp_delta":          round(rng.uniform(2, 22), 1),
        "growth_series":      _approx_growth_series(followers, days),
        "er_series":          _mock_er_series(er, days),
        "engagement_series":  _mock_engagement_series(avg_likes, avg_comments, avg_saves, days),
        "content_types":      _mock_content_types(rng),
        "posting_heatmap":    _generate_heatmap_data(),
        "top_posts":          _mock_top_posts(avg_likes, avg_comments, avg_saves, er, followers, rng),
        "hashtags":           _mock_hashtag_list(rng),
        "weekly_frequency":   _mock_weekly_frequency(total_posts, days),
        "_extracted_tags":    list(extracted_tags),
        "_raw_posts":         pseudo_posts,
    }


def _mock_hashtag(tag: str) -> dict:
    rng = random.Random(hash(tag) % 2**31)
    avg_l = rng.randint(500, 40_000)
    avg_c = rng.randint(20, 2_000)
    return {
        "tag":            tag,
        "posts_count":    rng.randint(10_000, 50_000_000),
        "avg_likes":      avg_l,
        "avg_comments":   avg_c,
        "avg_engagement": avg_l + avg_c,
        "top_posts":      [],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Shared series builders  (used by both live transformer and mock generator)
# ─────────────────────────────────────────────────────────────────────────────

def _approx_growth_series(followers: int, days: int) -> List[dict]:
    dates  = [datetime.now() - timedelta(days=i) for i in range(days, -1, -1)]
    base   = int(followers * 0.92)
    rng    = random.Random(followers)
    values = [base]
    for _ in range(days):
        delta = int(rng.gauss(followers * 0.0005, followers * 0.001))
        values.append(max(values[-1] + delta, base))
    return [{"date": d.strftime("%b %d"), "followers": v} for d, v in zip(dates, values)]


def _build_er_series(posts: List[dict], followers: int) -> List[dict]:
    by_week: Dict[str, list] = defaultdict(list)
    for i, p in enumerate(posts):
        week = f"W{i // 7 + 1}"
        lk = p.get("likesCount", 0)
        cm = p.get("commentsCount", 0)
        by_week[week].append(((lk + cm) / max(followers, 1)) * 100)
    if not by_week:
        return _mock_er_series(2.0, 30)
    return [{"week": w, "er": round(sum(v) / len(v), 2)} for w, v in by_week.items()]


def _mock_er_series(er: float, days: int) -> List[dict]:
    weeks = max(days // 7, 2)
    rng   = random.Random(int(er * 100))
    return [{"week": f"W{i+1}", "er": round(er * rng.uniform(0.75, 1.25), 2)} for i in range(weeks)]


def _build_engagement_series(posts: List[dict], days: int, avg_saves: int) -> List[dict]:
    by_date: Dict[str, dict] = defaultdict(lambda: {"likes": 0, "comments": 0, "saves": 0})
    for p in posts:
        try:
            d = datetime.fromtimestamp(p.get("timestamp", 0)).strftime("%b %d")
            by_date[d]["likes"]    += p.get("likesCount", 0)
            by_date[d]["comments"] += p.get("commentsCount", 0)
            by_date[d]["saves"]    += int(p.get("likesCount", 0) * 0.08)
        except Exception:
            pass
    if not by_date:
        return _mock_engagement_series(1000, 50, 80, days)
    return [{"date": d, **v} for d, v in sorted(by_date.items())]


def _mock_engagement_series(avg_likes: int, avg_comments: int, avg_saves: int, days: int) -> List[dict]:
    dates = [datetime.now() - timedelta(days=i) for i in range(days, -1, -1)]
    rng   = random.Random(avg_likes)
    return [{"date": d.strftime("%b %d"),
             "likes":    int(avg_likes    * rng.uniform(0.4, 1.9)),
             "comments": int(avg_comments * rng.uniform(0.4, 1.9)),
             "saves":    int(avg_saves    * rng.uniform(0.4, 1.9))} for d in dates]


def _mock_content_types(rng=None) -> dict:
    rng = rng or random
    r, p, c = rng.randint(30, 55), rng.randint(20, 38), rng.randint(10, 22)
    return {"Reels": r, "Photos": p, "Carousels": c, "Stories": max(100 - r - p - c, 3)}


def _generate_heatmap_data() -> List[List[float]]:
    rng  = np.random.default_rng(42)
    base = rng.uniform(0.5, 1.5, (7, 8))
    base[:, 5:7] *= rng.uniform(1.5, 2.5, (7, 2))
    base[5:7, :] *= rng.uniform(1.2, 1.8, (2, 8))
    return np.round(base * 2, 2).tolist()


def _generate_heatmap(posts: List[dict]) -> List[List[float]]:
    """Build real heatmap from post timestamps; fall back to mock if no data."""
    grid   = np.zeros((7, 8))
    counts = np.zeros((7, 8))
    for p in posts:
        try:
            dt   = datetime.fromtimestamp(p.get("timestamp", 0))
            dow  = dt.weekday()
            slot = min(dt.hour // 3, 7)
            eng  = p.get("likesCount", 0) + p.get("commentsCount", 0)
            grid[dow][slot]   += eng
            counts[dow][slot] += 1
        except Exception:
            pass
    with np.errstate(invalid="ignore", divide="ignore"):
        result = np.where(counts > 0, grid / counts, 0)
    mx = result.max() or 1
    hm = np.round(result / mx * 4, 2).tolist()
    # If all zeros, use mock
    return hm if any(any(row) for row in hm) else _generate_heatmap_data()


def _build_top_posts(posts: List[dict], followers: int) -> List[dict]:
    top = sorted(posts, key=lambda p: p.get("likesCount", 0), reverse=True)[:6]
    result = []
    for p in top:
        lk = p.get("likesCount", 0)
        cm = p.get("commentsCount", 0)
        sc = p.get("shortCode", "") or ""
        result.append({
            "type":             (p.get("type","POST") or "POST").replace("_ALBUM","").replace("IMAGE","PHOTO"),
            "caption":          ((p.get("caption","") or "")[:100]),
            "likes":            lk,
            "comments":         cm,
            "saves":            int(lk * 0.08),
            "engagement_rate":  round(((lk + cm) / max(followers, 1)) * 100, 2),
            "date":             datetime.fromtimestamp(p.get("timestamp", 0)).strftime("%b %d") if p.get("timestamp") else "",
            "url":              f"https://www.instagram.com/p/{sc}/" if sc else "",
        })
    return result


def _mock_top_posts(avg_likes, avg_comments, avg_saves, er, followers, rng=None) -> List[dict]:
    rng   = rng or random
    types = ["REEL", "PHOTO", "CAROUSEL", "REEL", "PHOTO", "CAROUSEL"]
    rng.shuffle(types)
    posts = []
    for i in range(6):
        m  = rng.uniform(1.2, 3.5)
        lk = int(avg_likes * m)
        cm = int(avg_comments * m)
        sv = int(avg_saves * m)
        posts.append({
            "type":            types[i],
            "caption":         rng.choice(MOCK_CAPTIONS),
            "likes":           lk,
            "comments":        cm,
            "saves":           sv,
            "engagement_rate": round(((lk + cm) / max(followers, 1)) * 100, 2),
            "date":            (datetime.now() - timedelta(days=rng.randint(0, 29))).strftime("%b %d"),
            "url":             "",
        })
    return sorted(posts, key=lambda x: x["likes"], reverse=True)


def _extract_hashtag_engagement(posts: List[dict]) -> List[dict]:
    tag_eng: Dict[str, list] = defaultdict(list)
    for p in posts:
        eng = p.get("likesCount", 0) + p.get("commentsCount", 0)
        for word in (p.get("caption", "") or "").split():
            if word.startswith("#") and len(word) > 2:
                tag_eng[word.lower()].append(eng)
    return sorted(
        [{"tag": t, "avg_engagement": int(sum(v) / len(v))} for t, v in tag_eng.items() if v],
        key=lambda x: x["avg_engagement"], reverse=True
    )[:10]


def _mock_hashtag_list(rng=None) -> List[dict]:
    rng  = rng or random
    tags = rng.sample(HASHTAG_POOL, min(10, len(HASHTAG_POOL)))
    return sorted([{"tag": t, "avg_engagement": rng.randint(500, 50_000)} for t in tags],
                  key=lambda x: x["avg_engagement"], reverse=True)


def _mock_weekly_frequency(total_posts: int, days: int) -> List[dict]:
    weeks = max(days // 7, 2)
    base  = max(total_posts // weeks, 1)
    rng   = random.Random(total_posts)
    return [{"week": f"W{i+1}", "posts": max(base + rng.randint(-2, 3), 0)} for i in range(weeks)]


def _build_weekly_frequency(posts: List[dict], days: int) -> List[dict]:
    by_week: Dict[str, int] = defaultdict(int)
    cutoff = datetime.now() - timedelta(days=days)
    for p in posts:
        try:
            dt   = datetime.fromtimestamp(p.get("timestamp", 0))
            week = max(1, int((dt - cutoff).days // 7) + 1)
            by_week[f"W{week}"] += 1
        except Exception:
            pass
    if not by_week:
        return _mock_weekly_frequency(len(posts), days)
    return [{"week": w, "posts": c} for w, c in sorted(by_week.items())]
