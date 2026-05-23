import pytest

from config.settings import clear_settings_cache


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("ENABLE_METRICS", raising=False)
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_metrics_disabled_returns_none():
    from services.metrics import render_metrics_payload

    assert render_metrics_payload() is None


def test_record_route_noop_when_disabled():
    from services.metrics import record_route_finished

    record_route_finished("x", 1.0, {"entity_count": 3}, None)  # no throw
