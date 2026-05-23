# Phase 4 — Model improvements

This phase adds optional model-side helpers without changing current model loading or response formats by default.

## What was added

### `services/model_cache.py`

- **Flag:** `ENABLE_MODEL_CACHE=true`
- TTL-based in-memory cache for loaded model objects or other expensive resources.
- Intended for future wiring around existing loader functions.
- If the flag is off, `get_or_load(...)` simply calls the provided loader and returns the result.

### `services/confidence_calibrator.py`

- **Flag:** `ENABLE_CALIBRATION=true`
- Learns simple per-label calibration multipliers from validation examples.
- No extra ML dependencies required.
- Can save and load calibration state from `CALIBRATION_STORE_PATH`.
- Does not overwrite current `confidence` values unless a caller explicitly chooses to use the calibrated output.

### `services/model_tracker.py`

- **Flag:** `ENABLE_MODEL_TRACKER=true`
- Logs prediction records and optional user corrections as JSONL files.
- Computes an exact-match accuracy summary from collected feedback.
- Can log a degradation warning if accuracy falls below `MODEL_TRACKER_ALERT_THRESHOLD`.

## Environment variables

```dotenv
ENABLE_MODEL_CACHE=false
MODEL_CACHE_TTL_SECONDS=3600

ENABLE_CALIBRATION=false
CALIBRATION_STORE_PATH=data/calibration.json

ENABLE_MODEL_TRACKER=false
MODEL_TRACKER_DIR=logs/model_tracker
MODEL_TRACKER_ALERT_THRESHOLD=0.70
```

## Safe usage pattern

```python
from services.model_cache import model_cache

predictor = model_cache.get_or_load("predictor:medical", load_predictor)
```

```python
from services.confidence_calibrator import default_calibrator

entities = default_calibrator.calibrate_entities(raw_entities)
```

```python
from services.model_tracker import model_tracker

prediction_id = model_tracker.record_prediction(
    route="document_analyze",
    text=text,
    domain=domain,
    entities=entities,
)
```

## Rollback

- Leave the Phase 4 flags at `false`, or remove any future imports that opt in to these helpers.
- Stored artifacts are isolated to `data/calibration.json` and `logs/model_tracker/`.

## Tests

```powershell
cd d:\MultiDomainDL\ner_project
.\venv\Scripts\python.exe -m pytest tests\unit\test_model_cache.py tests\unit\test_confidence_calibrator.py tests\unit\test_model_tracker.py -v
```
