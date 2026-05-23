from config.settings import clear_settings_cache, get_settings
from services.data_quality import assess_text, log_data_quality_warnings


def test_assess_detects_null_bytes():
    r = assess_text("hello\x00world")
    assert any("Null" in w for w in r.warnings)


def test_log_respects_feature_flag(monkeypatch):
    monkeypatch.setenv("ENABLE_DATA_QUALITY", "false")
    clear_settings_cache()
    log_data_quality_warnings("x" * 600_000, context="t")  # should no-op


def test_log_when_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_DATA_QUALITY", "true")
    monkeypatch.setenv("ENABLE_LOGGING", "false")
    clear_settings_cache()
    log_data_quality_warnings("short", context="unit")
    assert get_settings().enable_data_quality is True
