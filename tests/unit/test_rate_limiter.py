from config.settings import clear_settings_cache
from services.rate_limiter import rate_limiter


def test_rate_limiter_disabled_returns_allowed(monkeypatch):
    monkeypatch.setenv("ENABLE_RATE_LIMIT", "false")
    clear_settings_cache()
    rate_limiter.reset()
    allowed, _, _ = rate_limiter.check("127.0.0.1")
    assert allowed is True


def test_rate_limiter_blocks_after_limit(monkeypatch):
    monkeypatch.setenv("ENABLE_RATE_LIMIT", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "2")
    monkeypatch.setenv("RATE_LIMIT_BURST", "0")
    clear_settings_cache()
    rate_limiter.reset()
    assert rate_limiter.check("127.0.0.1")[0] is True
    assert rate_limiter.check("127.0.0.1")[0] is True
    assert rate_limiter.check("127.0.0.1")[0] is False

