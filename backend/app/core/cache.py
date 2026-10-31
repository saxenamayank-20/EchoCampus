"""Small cache used for admin stats and rate limits.

With REDIS_URL set it uses Redis (Upstash works). Without it, or if Redis is down,
it falls back to a dict in memory, so the app always runs.
"""
import threading
import time

import redis

from backend.app.core.config import settings


class MemoryCache:
    """lives inside this python process only, fine for one server and for tests"""

    def __init__(self):
        self._data: dict[str, tuple[str, float]] = {}   # key -> (value, expires at)
        self._lock = threading.Lock()                     # the scheduler thread uses it too

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._data.get(key)
            if not item or item[1] < time.time():
                self._data.pop(key, None)
                return None
            return item[0]

    def set(self, key: str, value: str, ttl: int) -> None:
        with self._lock:
            self._data[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def incr(self, key: str, ttl: int) -> int:
        """+1 and return the new count. the timer starts with the first hit"""
        with self._lock:
            value, expires = self._data.get(key, ("0", 0.0))
            if expires < time.time():
                value, expires = "0", time.time() + ttl
            count = int(value) + 1
            self._data[key] = (str(count), expires)
            return count

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class RedisCache:
    """same methods, stored in redis so every server shares it. errors never break a request"""

    def __init__(self, url: str):
        self.r = redis.Redis.from_url(url, decode_responses=True, socket_timeout=2)

    def get(self, key):
        try:
            return self.r.get(key)
        except redis.RedisError as e:
            print(f"[CACHE] redis get failed: {e}")
            return None

    def set(self, key, value, ttl):
        try:
            self.r.set(key, value, ex=ttl)
        except redis.RedisError as e:
            print(f"[CACHE] redis set failed: {e}")

    def delete(self, key):
        try:
            self.r.delete(key)
        except redis.RedisError as e:
            print(f"[CACHE] redis delete failed: {e}")

    def incr(self, key, ttl):
        try:
            pipe = self.r.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl, nx=True)   # only set the timer on the first hit
            return pipe.execute()[0]
        except redis.RedisError as e:
            print(f"[CACHE] redis incr failed, not limiting: {e}")
            return 0

    def clear(self):
        pass


_cache: MemoryCache | RedisCache | None = None


def get_cache() -> MemoryCache | RedisCache:
    global _cache
    if _cache is None:
        _cache = MemoryCache()
        if settings.redis_url:
            try:
                candidate = RedisCache(settings.redis_url)
                candidate.r.ping()
                _cache = candidate
            except redis.RedisError as e:
                print(f"[CACHE] can't reach redis, using memory instead: {e}")
    return _cache
