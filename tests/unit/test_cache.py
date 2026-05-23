"""Unit tests for optional ``services.cache`` (no Redis required)."""

import pytest

from config.settings import clear_settings_cache
from services.cache import CacheService, get_cache, reset_cache_client


@pytest.fixture(autouse=True)
def _reset_cache_and_settings(monkeypatch):
    reset_cache_client()
    clear_settings_cache()
    yield
    reset_cache_client()
    clear_settings_cache()


def test_cache_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_CACHING", raising=False)
    clear_settings_cache()
    c = CacheService()
    assert c.enabled is False


def test_get_or_set_invokes_factory_when_cache_unavailable(monkeypatch):
    monkeypatch.setenv("ENABLE_CACHING", "false")
    clear_settings_cache()
    reset_cache_client()
    c = get_cache()
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return {"x": 42}

    out = c.get_or_set("any:key", factory, ttl_seconds=60)
    assert out == {"x": 42}
    assert calls["n"] == 1
