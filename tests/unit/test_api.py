"""
tests/unit/test_api.py
Unit tests for the NER API endpoints.
Run with: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


# ── Mock predictor so tests don't need real models ─────────────────────────
@pytest.fixture
def mock_predictor():
    pred = MagicMock()
    pred.get_loaded_models.return_value = ["general", "medical", "legal"]
    pred.detect_domain.return_value = "medical"
    pred.predict.return_value = [
        {"text": "diabetes", "label": "DISEASE",
         "start": 0, "end": 8, "confidence": 0.98}
    ]
    return pred


@pytest.fixture
def client(mock_predictor):
    with patch("src.api.main.predictor", mock_predictor):
        from src.api.main import app
        with TestClient(app) as c:
            yield c


# ── Tests ──────────────────────────────────────────────────────────────────
class TestHealth:
    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_shows_models(self, client):
        r = client.get("/health")
        data = r.json()
        assert "models_loaded" in data
        assert len(data["models_loaded"]) == 3


class TestModels:
    def test_models_returns_3_domains(self, client):
        r = client.get("/models")
        assert r.status_code == 200
        data = r.json()
        assert "general" in data["models"]
        assert "medical" in data["models"]
        assert "legal"   in data["models"]


class TestPredict:
    def test_predict_returns_entities(self, client):
        r = client.post("/predict", json={
            "text": "Patient has diabetes mellitus.",
            "domain": "medical"
        })
        assert r.status_code == 200
        data = r.json()
        assert "entities" in data
        assert data["entity_count"] >= 0

    def test_predict_auto_domain(self, client):
        r = client.post("/predict", json={
            "text": "The patient was diagnosed with cancer.",
            "domain": "auto"
        })
        assert r.status_code == 200

    def test_predict_empty_text_fails(self, client):
        r = client.post("/predict", json={
            "text": "",
            "domain": "medical"
        })
        assert r.status_code == 422   # validation error

    def test_predict_invalid_domain_fails(self, client):
        r = client.post("/predict", json={
            "text": "Some text here.",
            "domain": "invalid_domain"
        })
        assert r.status_code == 422

    def test_predict_has_processing_time(self, client):
        r = client.post("/predict", json={
            "text": "The court ruled in favour of the plaintiff.",
            "domain": "legal"
        })
        data = r.json()
        assert "processing_time_seconds" in data
        assert data["processing_time_seconds"] >= 0


class TestBatchPredict:
    def test_batch_predict_multiple_texts(self, client):
        r = client.post("/predict/batch", json={
            "texts": [
                "Patient has diabetes.",
                "Court ruled against defendant.",
            ],
            "domain": "auto"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["total_texts"] == 2
        assert len(data["results"]) == 2

    def test_batch_too_many_texts_fails(self, client):
        r = client.post("/predict/batch", json={
            "texts": ["text"] * 51,
            "domain": "general"
        })
        assert r.status_code == 400
