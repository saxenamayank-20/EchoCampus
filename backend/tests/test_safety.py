from backend.app.core.cache import MemoryCache, get_cache
from backend.app.core.config import settings


def test_tests_never_reach_real_services():
    """guard: if this fails, the test run could touch the real db, redis, email or ai"""
    assert settings.database_url == "sqlite://"
    assert not settings.redis_url and not settings.smtp_host and not settings.gemini_api_key
    assert isinstance(get_cache(), MemoryCache)
