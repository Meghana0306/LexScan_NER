from config.settings import clear_settings_cache
from services.model_tracker import ModelTracker


def test_tracker_disabled_is_noop(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_MODEL_TRACKER", "false")
    clear_settings_cache()
    tracker = ModelTracker(base_dir=tmp_path)
    prediction_id = tracker.record_prediction(route="document", text="abc", domain="general", entities=[])
    assert prediction_id is None
    assert not tracker.predictions_path.exists()


def test_tracker_records_prediction_and_feedback(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_MODEL_TRACKER", "true")
    clear_settings_cache()
    tracker = ModelTracker(base_dir=tmp_path)
    prediction_id = tracker.record_prediction(
        route="document_analyze",
        text="Patient has diabetes",
        domain="medical",
        entities=[{"text": "diabetes", "label": "DISEASE", "start": 12, "end": 20}],
    )
    assert prediction_id
    ok = tracker.record_feedback(
        prediction_id=prediction_id,
        corrected_entities=[{"text": "diabetes", "label": "DISEASE", "start": 12, "end": 20}],
    )
    assert ok is True
    summary = tracker.summarize()
    assert summary.predictions_logged == 1
    assert summary.feedback_logged == 1
    assert summary.exact_match_accuracy == 1.0


def test_tracker_detects_mismatch(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_MODEL_TRACKER", "true")
    clear_settings_cache()
    tracker = ModelTracker(base_dir=tmp_path)
    prediction_id = tracker.record_prediction(
        route="document_analyze",
        text="Court hearing tomorrow",
        domain="legal",
        entities=[{"text": "tomorrow", "label": "DATE", "start": 14, "end": 22}],
    )
    tracker.record_feedback(
        prediction_id=prediction_id,
        corrected_entities=[{"text": "Court", "label": "COURT", "start": 0, "end": 5}],
    )
    summary = tracker.summarize()
    assert summary.compared_predictions == 1
    assert summary.exact_match_accuracy == 0.0

