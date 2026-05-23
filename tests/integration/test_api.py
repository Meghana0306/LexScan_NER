from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as app_module


@pytest.fixture
def client():
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_languages_endpoint(client, monkeypatch):
    monkeypatch.setattr(app_module.ui_logic, "SUPPORTED_LANGUAGES", ["English", "Hindi"])
    response = client.get("/api/languages")
    assert response.status_code == 200
    assert response.json()["languages"] == ["English", "Hindi"]


def test_document_analyze_endpoint(client, monkeypatch, tmp_path):
    report_path = tmp_path / "report.pdf"
    report_path.write_bytes(b"%PDF-1.4\n%fake\n")

    def fake_analyze(_file, text, domain, language):
        assert text == "Hello world"
        return (
            "Hello world",
            "Analysis complete.",
            "<p>summary</p>",
            [["Hello", "MISC", "0.88"]],
            {"entities": [{"text": "Hello", "label": "MISC", "confidence": 0.88}], "entity_count": 1},
            "<mark>Hello</mark>",
            "<div>general</div>",
            "<div>insight</div>",
            str(report_path),
        )

    monkeypatch.setattr(app_module.ui_logic, "analyze_document", fake_analyze)
    response = client.post("/api/document/analyze", json={"text": "Hello world", "domain": "auto", "language": "English"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Analysis complete."
    assert body["result"]["entity_count"] == 1
    assert body["report"]["filename"] == "report.pdf"


def test_extract_endpoint(client, monkeypatch):
    monkeypatch.setattr(app_module.ui_logic, "extract_text_from_path", lambda _path: ("Extracted text", "pdf"))
    response = client.post("/api/extract", files={"file": ("sample.pdf", b"%PDF-1.4 fake", "application/pdf")})
    assert response.status_code == 200
    assert response.json()["text"] == "Extracted text"


def test_health_endpoint(client, monkeypatch):
    class DummyPredictor:
        def get_loaded_models(self):
            return ["general", "medical"]

    monkeypatch.setattr(app_module.ui_logic, "_PREDICTOR", DummyPredictor(), raising=False)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["predictor_loaded"] is True
    assert response.json()["models_loaded"] == ["general", "medical"]


def test_status_endpoint(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "LexScan"
    assert "features" in body


def test_feedback_endpoint_disabled(client, monkeypatch):
    monkeypatch.setenv("ENABLE_ACTIVE_LEARNING", "false")
    from config.settings import clear_settings_cache

    clear_settings_cache()
    response = client.post("/api/feedback", json={"corrected_entities": []})
    assert response.status_code == 202
    assert response.json()["stored"] is False


def test_feedback_endpoint_enabled(client, monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_ACTIVE_LEARNING", "true")
    monkeypatch.setenv("ACTIVE_LEARNING_DIR", str(tmp_path))
    from config.settings import clear_settings_cache

    clear_settings_cache()
    response = client.post(
        "/api/feedback",
        json={
            "text": "Court hearing tomorrow",
            "domain": "legal",
            "predicted_entities": [{"text": "tomorrow", "label": "DATE"}],
            "corrected_entities": [{"text": "Court", "label": "COURT"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["stored"] is True
    assert Path(response.json()["path"]).exists()
