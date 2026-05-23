import time

import pytest
from fastapi.testclient import TestClient

import app as app_module
from config.settings import clear_settings_cache
from services.job_queue import job_queue
from services.rate_limiter import rate_limiter


@pytest.fixture(autouse=True)
def _clean():
    clear_settings_cache()
    rate_limiter.reset()
    job_queue.reset()
    yield
    clear_settings_cache()
    rate_limiter.reset()
    job_queue.reset()


@pytest.fixture
def client():
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_background_jobs_flow(client, monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_BACKGROUND_JOBS", "true")
    clear_settings_cache()

    report_path = tmp_path / "job-report.pdf"
    report_path.write_bytes(b"%PDF-1.4\n%fake\n")

    monkeypatch.setattr(
        app_module.ui_logic,
        "analyze_document",
        lambda _file, text, domain, language: (
            text,
            "ok",
            "<p/>",
            [],
            {"entities": [], "entity_count": 0},
            "<mark/>",
            "<div/>",
            "<div/>",
            str(report_path),
        ),
    )

    created = client.post("/api/jobs/document/analyze", json={"text": "hello", "domain": "auto", "language": "English"})
    assert created.status_code == 202
    job_id = created.json()["job_id"]

    final = None
    for _ in range(50):
        polled = client.get(f"/api/jobs/{job_id}")
        assert polled.status_code == 200
        final = polled.json()
        if final["status"] == "succeeded":
            break
        time.sleep(0.02)
    assert final is not None
    assert final["status"] == "succeeded"
    assert final["result"]["status"] == "ok"


def test_security_rejects_missing_api_key(client, monkeypatch):
    monkeypatch.setenv("ENABLE_API_KEY_AUTH", "true")
    monkeypatch.setenv("API_KEYS", "secret1")
    monkeypatch.setenv("AUTH_EXEMPT_PATHS", "/,/static,/api/languages")
    clear_settings_cache()
    response = client.get("/api/status")
    assert response.status_code == 401


def test_security_accepts_valid_api_key(client, monkeypatch):
    monkeypatch.setenv("ENABLE_API_KEY_AUTH", "true")
    monkeypatch.setenv("API_KEYS", "secret1")
    monkeypatch.setenv("AUTH_EXEMPT_PATHS", "/,/static,/api/languages")
    clear_settings_cache()
    response = client.get("/api/status", headers={"x-api-key": "secret1"})
    assert response.status_code == 200

