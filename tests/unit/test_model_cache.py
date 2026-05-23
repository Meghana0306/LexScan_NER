from config.settings import clear_settings_cache
from services.model_cache import ModelCache


def test_model_cache_disabled_calls_loader_each_time(monkeypatch):
    monkeypatch.setenv("ENABLE_MODEL_CACHE", "false")
    clear_settings_cache()
    cache = ModelCache()
    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        return {"ok": True, "n": calls["count"]}

    first = cache.get_or_load("general", loader)
    second = cache.get_or_load("general", loader)
    assert first["n"] == 1
    assert second["n"] == 2


def test_model_cache_enabled_reuses_loaded_value(monkeypatch):
    monkeypatch.setenv("ENABLE_MODEL_CACHE", "true")
    monkeypatch.setenv("MODEL_CACHE_TTL_SECONDS", "60")
    clear_settings_cache()
    cache = ModelCache()
    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        return {"count": calls["count"]}

    first = cache.get_or_load("medical", loader)
    second = cache.get_or_load("medical", loader)
    assert first == second
    assert calls["count"] == 1


def test_model_cache_expires_entries(monkeypatch):
    monkeypatch.setenv("ENABLE_MODEL_CACHE", "true")
    clear_settings_cache()
    cache = ModelCache()
    cache.set("legal", {"x": 1}, ttl_seconds=0)
    assert cache.get("legal") is None

