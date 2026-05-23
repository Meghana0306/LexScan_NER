import pytest

from config.settings import clear_settings_cache
from services.performance_monitor import record_analysis, reset_monitor_state


@pytest.fixture(autouse=True)
def _clean():
    reset_monitor_state()
    clear_settings_cache()
    yield
    reset_monitor_state()
    clear_settings_cache()


def test_monitor_noop_when_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_PERFORMANCE_MONITOR", "false")
    clear_settings_cache()
    record_analysis("r", 1.0, {"entities": [{"score": 0.9}]}, None)


def test_monitor_logs_slow(monkeypatch):
    monkeypatch.setenv("ENABLE_PERFORMANCE_MONITOR", "true")
    monkeypatch.setenv("PERF_SLOW_REQUEST_SECONDS", "0.001")
    clear_settings_cache()
    record_analysis("r", 10.0, {"entities": []}, None)
