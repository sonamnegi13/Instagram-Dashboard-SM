"""utils.py — Helper functions for InstaLens dashboard."""


def format_number(n) -> str:
    """Format large numbers with K/M suffixes."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def calculate_engagement_rate(likes: int, comments: int, followers: int) -> float:
    """Standard ER formula: (likes + comments) / followers * 100."""
    if followers == 0:
        return 0.0
    return round((likes + comments) / followers * 100, 2)


def get_growth_delta(current: int, previous: int) -> float:
    """Percentage change between two values."""
    if previous == 0:
        return 0.0
    return round((current - previous) / previous * 100, 1)


def rate_engagement(er: float) -> str:
    """Rate engagement quality."""
    if er >= 6:   return "🔥 Exceptional"
    if er >= 3:   return "✅ Above Average"
    if er >= 1:   return "📊 Average"
    if er >= 0.5: return "⚠️  Below Average"
    return "❌ Poor"


def benchmark_er(followers: int, er: float) -> str:
    """Return benchmark ER based on account size."""
    if followers > 1_000_000:
        good = 1.5
    elif followers > 100_000:
        good = 2.5
    elif followers > 10_000:
        good = 3.5
    else:
        good = 5.0
    diff = er - good
    if diff >= 1:
        return f"▲ {abs(diff):.1f}pp above benchmark"
    elif diff <= -1:
        return f"▼ {abs(diff):.1f}pp below benchmark"
    else:
        return "≈ At benchmark"
