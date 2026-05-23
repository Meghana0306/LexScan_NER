from pathlib import Path

from config.settings import clear_settings_cache
from services.confidence_calibrator import CalibrationSample, ConfidenceCalibrator


def test_fit_learns_label_multiplier():
    calibrator = ConfidenceCalibrator(store_path=Path("tmp-calibration.json"))
    learned = calibrator.fit(
        [
            CalibrationSample(label="DISEASE", score=0.9, correct=False),
            CalibrationSample(label="DISEASE", score=0.8, correct=False),
            CalibrationSample(label="DISEASE", score=0.2, correct=True),
            CalibrationSample(label="DRUG", score=0.5, correct=True),
            CalibrationSample(label="DRUG", score=0.6, correct=True),
        ]
    )
    assert learned["DISEASE"].multiplier < 1.0
    assert learned["DRUG"].multiplier > 1.0


def test_calibrate_entities_respects_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_CALIBRATION", "false")
    clear_settings_cache()
    calibrator = ConfidenceCalibrator(store_path=tmp_path / "calibration.json")
    calibrator.fit([CalibrationSample(label="DISEASE", score=0.9, correct=False)])
    entities = calibrator.calibrate_entities([{"text": "x", "label": "DISEASE", "confidence": 0.9}])
    assert "confidence_calibrated" not in entities[0]


def test_save_and_load_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_CALIBRATION", "true")
    clear_settings_cache()
    path = tmp_path / "calibration.json"
    first = ConfidenceCalibrator(store_path=path)
    first.fit([CalibrationSample(label="COURT", score=0.75, correct=True)])
    first.save()

    second = ConfidenceCalibrator(store_path=path)
    loaded = second.load()
    assert "COURT" in loaded
    assert second.calibrate_score("COURT", 0.75) >= 0.75

