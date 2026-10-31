from backend.app.core.cache import get_cache
from backend.app.services.errors import RateLimitError


def hit(key: str, limit: int, window_seconds: int) -> None:
    """counts one more request for key. over the limit inside the window -> 429"""
    count = get_cache().incr(f"rl:{key}", window_seconds)
    if count > limit:
        minutes = max(1, window_seconds // 60)
        raise RateLimitError(f"Too many requests. You can do this {limit} times per {minutes} minutes.")
