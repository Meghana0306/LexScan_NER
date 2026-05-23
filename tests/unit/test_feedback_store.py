from config.settings import clear_settings_cache
from services.feedback_store import FeedbackStore


def test_feedback_store_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_FEEDBACK_DB", "false")
    clear_settings_cache()
    store = FeedbackStore(tmp_path / "feedback.sqlite3")
    assert store.store_feedback({"feedback_id": "x", "timestamp": 1, "text_length": 1}) is False


def test_feedback_store_writes_rows(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_FEEDBACK_DB", "true")
    clear_settings_cache()
    store = FeedbackStore(tmp_path / "feedback.sqlite3")
    assert store.store_feedback(
        {
            "feedback_id": "fb1",
            "prediction_id": "pred1",
            "timestamp": 1.0,
            "domain": "medical",
            "text_length": 12,
            "predicted_entities": [{"text": "x", "label": "DISEASE"}],
            "corrected_entities": [{"text": "x", "label": "DISEASE"}],
            "metadata": {"note": "ok"},
        }
    ) is True
    assert store.count_feedback() == 1
    assert store.recent_feedback(limit=1)[0]["feedback_id"] == "fb1"

