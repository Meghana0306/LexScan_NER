from config.settings import clear_settings_cache
from services.active_learner import collect_feedback


def test_active_learner_disabled_returns_noop(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_ACTIVE_LEARNING", "false")
    monkeypatch.setenv("ACTIVE_LEARNING_DIR", str(tmp_path))
    clear_settings_cache()
    result = collect_feedback(
        prediction_id=None,
        text="hello",
        domain="general",
        predicted_entities=[],
        corrected_entities=[],
    )
    assert result["accepted"] is False
    assert result["stored"] is False


def test_active_learner_stores_feedback(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_ACTIVE_LEARNING", "true")
    monkeypatch.setenv("ACTIVE_LEARNING_DIR", str(tmp_path))
    clear_settings_cache()
    result = collect_feedback(
        prediction_id=None,
        text="Patient has diabetes",
        domain="medical",
        predicted_entities=[{"text": "diabetes", "label": "DISEASE"}],
        corrected_entities=[{"text": "diabetes", "label": "DISEASE"}],
    )
    assert result["accepted"] is True
    assert result["stored"] is True
    assert result["feedback_db_stored"] is False
    assert tmp_path.joinpath("feedback.jsonl").exists()


def test_active_learner_can_store_to_feedback_db(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_ACTIVE_LEARNING", "true")
    monkeypatch.setenv("ENABLE_FEEDBACK_DB", "true")
    monkeypatch.setenv("ACTIVE_LEARNING_DIR", str(tmp_path / "jsonl"))
    monkeypatch.setenv("FEEDBACK_DB_PATH", str(tmp_path / "feedback.sqlite3"))
    clear_settings_cache()
    result = collect_feedback(
        prediction_id=None,
        text="Patient has diabetes",
        domain="medical",
        predicted_entities=[{"text": "diabetes", "label": "DISEASE"}],
        corrected_entities=[{"text": "diabetes", "label": "DISEASE"}],
    )
    assert result["feedback_db_stored"] is True
