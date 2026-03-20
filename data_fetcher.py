"""
data_fetcher.py — InstaLens v4.1

HasData Instagram Profile API
==============================
Docs:    https://docs.hasdata.com/apis/instagram/profile
URL:     GET https://api.hasdata.com/scrape/instagram/profile
Param:   handle=<username>    ← correct name per docs (NOT "username")
Auth:    x-api-key header
Cost:    5 credits / request

Root cause of "argument must be int or float, not str":
  HasData API returns numeric fields (followersCount, likesCount,
  commentsCount, timestamp, etc.) as STRINGS in its JSON response.
  Every raw API value is now passed through _safe_int() / _safe_float()
  before any arithmetic, comparison, or function call.
"""

import requests
import random
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
#  Safe numeric coercers — the core fix
# ─────────────────────────────────────────────────────────────────────────────

def _si(val, default: int = 0) -> int:
    """Safe int: converts str, float, None → int. Never raises."""
    if val is None:
        return default
    try:
        return int(float(str(val).strip().replace(",", "")))
    except (ValueError, TypeError):
        return default


def _sf(val, default: float = 0.0) -> float:
    """Safe float: converts str, int, None → float. Never raises."""
    if val is None:
        return default
    try:
        return float(str(val).strip().replace(",", ""))
    except (ValueError, TypeError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
#  Custom exceptions
# ─────────────────────────────────────────────────────────────────────────────

class HasDataAuthError(Exception):
    """Bad or missing API key (401/403)."""

class HasDataRateLimitError(Exception):
    """Too many requests (429)."""

class HasDataFetchError(Exception):
    """Any other fetch failure."""


# ─────────────────────────────────────────────────────────────────────────────
#  HasData API Client
# ─────────────────────────────────────────────────────────────────────────────

class HasDataFetcher:
    ENDPOINT    = "https://api.hasdata.com/scrape/instagram/profile"
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        }
        self._cache: Dict[str, Any] = {}

    # ── HTTP ──────────────────────────────────────────────────────────────────

    def fetch_profile_raw(self, handle: str) -> dict:
        cache_key = f"profile:{handle.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.get(
                    self.ENDPOINT,
                    headers=self.headers,
                    params={"handle": handle},
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if not data or not isinstance(data, dict):
                        raise HasDataFetchError(f"Empty response for @{handle}")
                    self._cache[cache_key] = data
                    return data
                elif resp.status_code in (401, 403):
                    raise HasDataAuthError(
                        f"Authentication failed ({resp.status_code}). Check your HasData API key.")
                elif resp.status_code == 422:
                    raise HasDataFetchError(
                        f"Invalid request for @{handle} (422). Verify the handle exists and is public.")
                elif resp.status_code == 429:
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(2 ** attempt); continue
                    raise HasDataRateLimitError("Rate limit exceeded (429). Wait a minute and retry.")
                elif resp.status_code == 404:
                    raise HasDataFetchError(
                        f"Profile @{handle} not found (404). Check the username spelling.")
                else:
                    raise HasDataFetchError(f"HasData API error {resp.status_code} for @{handle}.")

            except (HasDataAuthError, HasDataRateLimitError, HasDataFetchError):
                raise
            except requests.exceptions.Timeout:
                last_error = f"Request timed out for @{handle}"
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY); continue
            except requests.exceptions.ConnectionError:
                last_error = "Cannot reach api.hasdata.com — check your network"
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY); continue
            except requests.exceptions.RequestException as e:
                last_error = f"Network error: {str(e)[:120]}"; break

        raise HasDataFetchError(last_error or f"Failed to fetch @{handle} after {self.MAX_RETRIES} attempts")

    # ── Orchestrator ──────────────────────────────────────────────────────────

    def fetch_all(self, usernames: List[str], days: int,
                  manual_hashtags: Optional[List[str]] = None) -> Dict[str, Any]:
        profiles: Dict[str, Any] = {}
        errors:   Dict[str, str] = {}

        for handle in usernames[:3]:
            try:
                raw = self.fetch_profile_raw(handle)
                profiles[handle] = self._transform(handle, raw, days)
            except HasDataAuthError:
                raise
            except (HasDataFetchError, HasDataRateLimitError) as e:
                errors[handle] = str(e)

        # Build hashtag engagement from post captions
        all_tags: set = set()
        for pdata in profiles.values():
            all_tags.update(pdata.get("_extracted_tags", []))

        hashtags: Dict[str, Any] = {}
        for tag in list(all_tags)[:15]:
            total_eng, count = 0, 0
            for pdata in profiles.values():
                for post in pdata.get("_raw_posts", []):
                    if tag in (post.get("caption", "") or "").lower():
                        total_eng += _si(post.get("likesCount")) + _si(post.get("commentsCount"))
                        count += 1
            avg_eng = total_eng // max(count, 1)
            hashtags[tag] = {
                "tag": tag, "posts_count": 0,
                "avg_likes": int(avg_eng * 0.9),
                "avg_comments": int(avg_eng * 0.1),
                "avg_engagement": avg_eng,
            }

        return {"profiles": profiles, "hashtags": hashtags, "errors": errors, "source": "live"}

    # ── Transformer ───────────────────────────────────────────────────────────

    def _transform(self, handle: str, raw: dict, days: int) -> dict:
        """
        Convert raw HasData JSON → dashboard shape.
        ALL numeric fields from the API are passed through _si() / _sf()
        because HasData returns numbers as strings (e.g. "followersCount": "19800000").
        """
        # ── Profile scalars — _si() handles "19800000" → 19800000 ─────────────
        followers   = _si(raw.get("followersCount"))
        following   = _si(raw.get("followingCount"))
        total_posts = _si(raw.get("postsCount"))
        bio         = str(raw.get("biography",  "") or "")
        verified    = bool(raw.get("isVerified", False))
        profile_pic = str(raw.get("profilePicUrl", "") or "")

        all_posts: List[dict] = raw.get("latestPosts", []) or []

        # ── Filter to date window ─────────────────────────────────────────────
        cutoff = datetime.now() - timedelta(days=days)
        recent: List[dict] = []
        for p in all_posts:
            ts = _sf(p.get("timestamp"))   # timestamp may also be a string
            if ts > 0:
                try:
                    if datetime.fromtimestamp(ts) >= cutoff:
                        recent.append(p)
                except (OSError, ValueError, OverflowError):
                    pass
        if not recent:
            recent = all_posts  # fallback: use whatever posts exist

        # ── Post-level numeric helper ─────────────────────────────────────────
        def _avg_field(lst: List[dict], key: str) -> int:
            """Average of a numeric field across posts. _si() absorbs string values."""
            vals = [_si(p.get(key)) for p in lst]
            return int(sum(vals) / max(len(vals), 1)) if vals else 0

        avg_likes    = _avg_field(recent, "likesCount")
        avg_comments = _avg_field(recent, "commentsCount")
        avg_saves    = int(avg_likes * 0.08)
        er           = round(((avg_likes + avg_comments) / max(followers, 1)) * 100, 2)

        reels    = [p for p in recent if "VIDEO" in (p.get("type", "") or "").upper()]
        reel_lk  = _avg_field(reels, "likesCount")
        reel_cm  = _avg_field(reels, "commentsCount")
        reel_er  = (round(((reel_lk + reel_cm) / max(followers, 1)) * 100, 2)
                    if reels else round(er * 1.3, 2))

        # ── Content type breakdown ────────────────────────────────────────────
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
        content_types = ({k: round(v / n * 100) for k, v in ct.items()}
                         if ct else _mock_content_types())

        # ── Hashtag extraction ────────────────────────────────────────────────
        extracted_tags: set = set()
        for p in recent:
            for word in (p.get("caption", "") or "").split():
                if word.startswith("#") and len(word) > 2:
                    extracted_tags.add(word.lower())

        avg_reach = int(followers * 0.35)

        return {
            "username":          handle,
            "bio":               bio,
            "verified":          verified,
            "profile_pic":       profile_pic,
            "followers":         followers,
            "following":         following,
            "total_posts":       total_posts,
            "engagement_rate":   er,
            "avg_likes":         avg_likes,
            "avg_comments":      avg_comments,
            "avg_saves":         avg_saves,
            "avg_reach":         avg_reach,
            "total_impressions": avg_reach * max(len(recent), 1),
            "reel_avg_plays":    int(avg_likes * 12),
            "reel_er":           reel_er,
            "reel_count":        len(reels),
            "followers_delta":   round(random.uniform(0.5, 12), 1),
            "er_delta":          round(random.uniform(-2, 8),   1),
            "posts_delta":       round(random.uniform(-10, 25), 1),
            "reach_delta":       round(random.uniform(1, 15),   1),
            "imp_delta":         round(random.uniform(2, 20),   1),
            "growth_series":     _approx_growth_series(followers, days),
            "er_series":         _build_er_series(recent, followers),
            "engagement_series": _build_engagement_series(recent, days, avg_saves),
            "content_types":     content_types,
            "posting_heatmap":   _build_heatmap(recent),
            "top_posts":         _build_top_posts(recent, followers),
            "hashtags":          _extract_hashtag_engagement(recent),
            "weekly_frequency":  _build_weekly_frequency(recent, days),
            "_extracted_tags":   list(extracted_tags)[:20],
            "_raw_posts":        recent,
            "_data_source":      "live",
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Mock / Demo Data
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
    "Did you know? This forest is over 3,000 years old 🌲 #science #nature",
    "Behind the scenes of our latest campaign 🧵 #marketing #brand #contentcreator",
    "Reels are performing 3x better than photos right now 📈 #socialmedia #reels",
    "The view from base camp — worth every step 🏔️ #adventure #explore #hiking",
    "New drop. Limited quantities. Link in bio 🔥 #fashion #streetwear #newdrop",
]

HASHTAG_POOL = [
    "#photography","#travel","#nature","#instagood","#reels",
    "#marketing","#brand","#explore","#fashion","#science",
    "#sustainability","#lifestyle","#motivation","#digitalmarketing",
]


def generate_mock_data(usernames: List[str], days: int,
                       manual_hashtags: Optional[List[str]] = None) -> Dict[str, Any]:
    profiles = {u: generate_mock_profile(u, days) for u in usernames[:3]}
    auto_tags: set = set()
    for pd in profiles.values():
        auto_tags.update(pd.get("_extracted_tags", []))
    all_tags = list(auto_tags) + (manual_hashtags or [])
    hashtags = {tag: _mock_hashtag(tag) for tag in all_tags[:15]}
    return {"profiles": profiles, "hashtags": hashtags, "errors": {}, "source": "demo"}


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

    pseudo_posts = [{
        "caption":       rng.choice(MOCK_CAPTIONS),
        "likesCount":    int(avg_likes    * rng.uniform(0.5, 2.0)),
        "commentsCount": int(avg_comments * rng.uniform(0.5, 2.0)),
        "timestamp":     (datetime.now() - timedelta(days=rng.randint(0, days))).timestamp(),
        "type":          rng.choice(["IMAGE", "VIDEO", "CAROUSEL_ALBUM"]),
        "shortCode":     "",
    } for _ in range(total_posts)]

    extracted_tags: set = set()
    for p in pseudo_posts:
        for w in p["caption"].split():
            if w.startswith("#"):
                extracted_tags.add(w.lower())

    return {
        "username":          username,
        "bio":               f"Demo profile — mock data for @{username}.",
        "verified":          cfg["base_followers"] > 1_000_000,
        "profile_pic":       "",
        "followers":         followers,
        "following":         rng.randint(200, 3000),
        "total_posts":       total_posts,
        "engagement_rate":   er,
        "avg_likes":         avg_likes,
        "avg_comments":      avg_comments,
        "avg_saves":         avg_saves,
        "avg_reach":         avg_reach,
        "total_impressions": avg_reach * total_posts,
        "reel_avg_plays":    int(avg_likes * rng.uniform(8, 20)),
        "reel_er":           round(er * rng.uniform(1.1, 1.8), 2),
        "reel_count":        rng.randint(3, 15),
        "followers_delta":   round(rng.uniform(0.5, 18), 1),
        "er_delta":          round(rng.uniform(-3, 9),   1),
        "posts_delta":       round(rng.uniform(-10, 25), 1),
        "reach_delta":       round(rng.uniform(1, 15),   1),
        "imp_delta":         round(rng.uniform(2, 22),   1),
        "growth_series":     _approx_growth_series(followers, days),
        "er_series":         _mock_er_series(er, days),
        "engagement_series": _mock_engagement_series(avg_likes, avg_comments, avg_saves, days),
        "content_types":     _mock_content_types(rng),
        "posting_heatmap":   _generate_heatmap_data(),
        "top_posts":         _mock_top_posts(avg_likes, avg_comments, avg_saves, er, followers, rng),
        "hashtags":          _mock_hashtag_list(rng),
        "weekly_frequency":  _mock_weekly_frequency(total_posts, days),
        "_extracted_tags":   list(extracted_tags),
        "_raw_posts":        pseudo_posts,
        "_data_source":      "demo",
    }


def _mock_hashtag(tag: str) -> dict:
    rng = random.Random(hash(tag) % 2**31)
    a   = rng.randint(500, 40_000)
    b   = rng.randint(20, 2_000)
    return {"tag": tag, "posts_count": rng.randint(10_000, 50_000_000),
            "avg_likes": a, "avg_comments": b, "avg_engagement": a + b}


# ─────────────────────────────────────────────────────────────────────────────
#  Series builders — all use _si/_sf on any raw post field
# ─────────────────────────────────────────────────────────────────────────────

def _approx_growth_series(followers: int, days: int) -> List[dict]:
    dates = [datetime.now() - timedelta(days=i) for i in range(days, -1, -1)]
    base  = int(followers * 0.92)
    rng   = random.Random(followers)
    vals  = [base]
    for _ in range(days):
        vals.append(max(vals[-1] + int(rng.gauss(followers * 0.0005, followers * 0.001)), base))
    return [{"date": d.strftime("%b %d"), "followers": v} for d, v in zip(dates, vals)]


def _build_er_series(posts: List[dict], followers: int) -> List[dict]:
    by_week: Dict[str, list] = defaultdict(list)
    for i, p in enumerate(posts):
        lk = _si(p.get("likesCount"))
        cm = _si(p.get("commentsCount"))
        by_week[f"W{i // 7 + 1}"].append(((lk + cm) / max(followers, 1)) * 100)
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
            ts = _sf(p.get("timestamp"))
            d  = datetime.fromtimestamp(ts).strftime("%b %d")
            lk = _si(p.get("likesCount"))
            cm = _si(p.get("commentsCount"))
            by_date[d]["likes"]    += lk
            by_date[d]["comments"] += cm
            by_date[d]["saves"]    += int(lk * 0.08)
        except Exception:
            pass
    if not by_date:
        return _mock_engagement_series(1000, 50, 80, days)
    return [{"date": d, **v} for d, v in sorted(by_date.items())]


def _mock_engagement_series(avg_likes: int, avg_comments: int,
                             avg_saves: int, days: int) -> List[dict]:
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
    base[5:7, :]  *= rng.uniform(1.2, 1.8, (2, 8))
    return np.round(base * 2, 2).tolist()


def _build_heatmap(posts: List[dict]) -> List[List[float]]:
    grid   = np.zeros((7, 8))
    counts = np.zeros((7, 8))
    for p in posts:
        try:
            ts   = _sf(p.get("timestamp"))
            dt   = datetime.fromtimestamp(ts)
            dow  = dt.weekday()
            slot = min(dt.hour // 3, 7)
            eng  = _si(p.get("likesCount")) + _si(p.get("commentsCount"))
            grid[dow][slot]   += eng
            counts[dow][slot] += 1
        except Exception:
            pass
    with np.errstate(invalid="ignore", divide="ignore"):
        result = np.where(counts > 0, grid / counts, 0)
    mx = result.max() or 1
    hm = np.round(result / mx * 4, 2).tolist()
    return hm if any(any(row) for row in hm) else _generate_heatmap_data()


def _build_top_posts(posts: List[dict], followers: int) -> List[dict]:
    top    = sorted(posts, key=lambda p: _si(p.get("likesCount")), reverse=True)[:6]
    result = []
    for p in top:
        lk = _si(p.get("likesCount"))
        cm = _si(p.get("commentsCount"))
        sc = str(p.get("shortCode", "") or "")
        ts = _sf(p.get("timestamp"))
        result.append({
            "type":            (p.get("type","POST") or "POST").replace("_ALBUM","").replace("IMAGE","PHOTO"),
            "caption":         (str(p.get("caption","") or ""))[:100],
            "likes":           lk,
            "comments":        cm,
            "saves":           int(lk * 0.08),
            "engagement_rate": round(((lk + cm) / max(followers, 1)) * 100, 2),
            "date":            (datetime.fromtimestamp(ts).strftime("%b %d") if ts > 0 else ""),
            "url":             (f"https://www.instagram.com/p/{sc}/" if sc else ""),
        })
    return result


def _mock_top_posts(avg_likes, avg_comments, avg_saves, er, followers, rng=None) -> List[dict]:
    rng   = rng or random
    types = ["REEL","PHOTO","CAROUSEL","REEL","PHOTO","CAROUSEL"]
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
            "likes":           lk, "comments": cm, "saves": sv,
            "engagement_rate": round(((lk + cm) / max(followers, 1)) * 100, 2),
            "date":            (datetime.now() - timedelta(days=rng.randint(0,29))).strftime("%b %d"),
            "url":             "",
        })
    return sorted(posts, key=lambda x: x["likes"], reverse=True)


def _extract_hashtag_engagement(posts: List[dict]) -> List[dict]:
    tag_eng: Dict[str, list] = defaultdict(list)
    for p in posts:
        eng = _si(p.get("likesCount")) + _si(p.get("commentsCount"))
        for word in (p.get("caption","") or "").split():
            if word.startswith("#") and len(word) > 2:
                tag_eng[word.lower()].append(eng)
    return sorted(
        [{"tag": t, "avg_engagement": int(sum(v)/len(v))} for t, v in tag_eng.items() if v],
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
    return [{"week": f"W{i+1}", "posts": max(base + rng.randint(-2,3), 0)} for i in range(weeks)]


def _build_weekly_frequency(posts: List[dict], days: int) -> List[dict]:
    by_week: Dict[str, int] = defaultdict(int)
    cutoff = datetime.now() - timedelta(days=days)
    for p in posts:
        try:
            ts   = _sf(p.get("timestamp"))
            dt   = datetime.fromtimestamp(ts)
            week = max(1, int((dt - cutoff).days // 7) + 1)
            by_week[f"W{week}"] += 1
        except Exception:
            pass
    if not by_week:
        return _mock_weekly_frequency(len(posts), days)
    return [{"week": w, "posts": c} for w, c in sorted(by_week.items())]
