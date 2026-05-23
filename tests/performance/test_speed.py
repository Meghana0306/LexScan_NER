import time

from services.confidence_calibrator import CalibrationSample, ConfidenceCalibrator
from services.data_quality import assess_text
from services.text_preprocessor import preprocess_text


def test_preprocessing_speed_is_reasonable():
    text = ("Patient has diabetes and hypertension. " * 2000).strip()
    start = time.perf_counter()
    for _ in range(25):
        preprocess_text(text)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.5


def test_data_quality_speed_is_reasonable():
    text = ("The court ruled in favor of the plaintiff. " * 2000).strip()
    start = time.perf_counter()
    for _ in range(10):
        assess_text(text)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.5


def test_calibration_speed_is_reasonable(tmp_path):
    calibrator = ConfidenceCalibrator(store_path=tmp_path / "calibration.json")
    samples = [CalibrationSample(label="DISEASE", score=0.6, correct=True) for _ in range(1000)]
    start = time.perf_counter()
    calibrator.fit(samples)
    for _ in range(200):
        calibrator.calibrate_score("DISEASE", 0.75)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0
