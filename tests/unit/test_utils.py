"""Unit tests for foundation utilities (settings + logging)."""

import json
import logging
from pathlib import Path

import pytest

from config.settings import clear_settings_cache, get_settings
from utils.logger import configure_logging, reset_logging_configuration


@pytest.fixture(autouse=True)
def _clean_env_and_logging(monkeypatch, tmp_path):
    monkeypatch.delenv("ENABLE_LOGGING", raising=False)
    monkeypatch.delenv("LOG_DIR", raising=False)
    clear_settings_cache()
    reset_logging_configuration()
    yield
    reset_logging_configuration()
    clear_settings_cache()


def test_settings_defaults_match_app_host_port(monkeypatch):
    monkeypatch.delenv("APP_HOST", raising=False)
    monkeypatch.delenv("APP_PORT", raising=False)
    clear_settings_cache()
    s = get_settings()
    assert s.app_host == "127.0.0.1"
    assert s.app_port == 7860


def test_feature_flags_default_false(monkeypatch):
    monkeypatch.delenv("ENABLE_CACHING", raising=False)
    clear_settings_cache()
    s = get_settings()
    assert s.enable_caching is False
    assert s.enable_metrics is False


def test_configure_logging_writes_json_lines(monkeypatch, tmp_path):
    log_dir = tmp_path / "logs"
    monkeypatch.setenv("ENABLE_LOGGING", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_DIR", str(log_dir))
    clear_settings_cache()
    configure_logging(force=True)
    log = logging.getLogger("lexscan.test")
    log.info("hello", extra={"request_id": "abc"})
    reset_logging_configuration()

    app_log = log_dir / "app.log"
    assert app_log.exists()
    line = app_log.read_text(encoding="utf-8").strip().splitlines()[-1]
    data = json.loads(line)
    assert data["message"] == "hello"
    assert data["request_id"] == "abc"
