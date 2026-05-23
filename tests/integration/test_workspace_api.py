from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as app_module
from services.workspace_store import workspace_store


@pytest.fixture
def client(tmp_path, monkeypatch):
    workspace_store.db_path = tmp_path / "workspace.sqlite3"
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_workspace_analyze_and_search(client, monkeypatch):
    monkeypatch.setattr(
        app_module.ui_logic,
        "analyze_text",
        lambda text, domain: {
            "text": text,
            "domain": "medical" if domain == "auto" else domain,
            "entities": [
                {"text": "diabetes", "label": "DISEASE", "confidence": 0.9},
                {"text": "March 20, 2025", "label": "DATE", "confidence": 0.88},
            ],
            "entity_count": 2,
            "processing_time_seconds": 0.1,
        },
    )
    response = client.post(
        "/api/workspace/analyze",
        json={
            "title": "Clinic note",
            "collection_name": "Patients",
            "text": "Patient has diabetes and follow-up on March 20, 2025.",
            "domain": "auto",
            "save_document": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["subtype"]
    assert body["analysis"]["timeline"]

    search = client.get("/api/workspace/search", params={"query": "diabetes"})
    assert search.status_code == 200
    assert search.json()["results"]


def test_workspace_question_and_compare(client, monkeypatch):
    monkeypatch.setattr(
        app_module.ui_logic,
        "analyze_text",
        lambda text, domain: {
            "text": text,
            "domain": "legal",
            "entities": [{"text": "Court", "label": "COURT", "confidence": 0.95}],
            "entity_count": 1,
            "processing_time_seconds": 0.1,
        },
    )
    question = client.post(
        "/api/workspace/question",
        json={"text": "The contract renews on March 20, 2025.", "question": "When does it renew?"},
    )
    assert question.status_code == 200
    assert question.json()["citations"]

    compare = client.post(
        "/api/workspace/compare",
        json={"text_a": "Court order", "text_b": "Judge order", "domain_a": "legal", "domain_b": "legal"},
    )
    assert compare.status_code == 200
    assert "comparison" in compare.json()
