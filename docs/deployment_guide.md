# Deployment Guide

## 1. Install core dependencies

```powershell
cd D:\MultiDomainDL\ner_project
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. Install optional production extras

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-prod.txt
```

## 3. Start with all optional features off

Use the defaults from `.env.example` or explicitly set:

```powershell
$env:ENABLE_LOGGING="false"
$env:ENABLE_CACHING="false"
$env:ENABLE_METRICS="false"
$env:ENABLE_VALIDATION="false"
$env:ENABLE_DATA_QUALITY="false"
$env:ENABLE_PREPROCESSING="false"
$env:ENABLE_MODEL_CACHE="false"
$env:ENABLE_CALIBRATION="false"
$env:ENABLE_MODEL_TRACKER="false"
$env:ENABLE_ACTIVE_LEARNING="false"
$env:ENABLE_API_KEY_AUTH="false"
$env:ENABLE_RATE_LIMIT="false"
$env:ENABLE_BACKGROUND_JOBS="false"
$env:ENABLE_FEEDBACK_DB="false"
.\venv\Scripts\python.exe app.py
```

## 4. Verify baseline behavior

- Open `http://127.0.0.1:7860`
- Upload a sample file
- Run document analysis
- Confirm the response shape matches the current UI flow

## 5. Enable features gradually

Recommended order:

1. `ENABLE_LOGGING=true`
2. `ENABLE_REQUEST_LOGGING=true`
3. `ENABLE_METRICS=true`
4. `ENABLE_DATA_QUALITY=true`
5. `ENABLE_MODEL_TRACKER=true`
6. `ENABLE_ACTIVE_LEARNING=true`
7. `ENABLE_FEEDBACK_DB=true`
8. `ENABLE_API_KEY_AUTH=true`
9. `ENABLE_RATE_LIMIT=true`
10. `ENABLE_BACKGROUND_JOBS=true`

## 6. Run tests before deployment

```powershell
.\venv\Scripts\python.exe -m pytest tests\unit\ --ignore=tests\unit\test_api.py -v
.\venv\Scripts\python.exe -m pytest tests\integration\test_api.py -v
.\venv\Scripts\python.exe -m pytest tests\performance\test_speed.py -v
```

## 7. Rollback

- Turn all `ENABLE_*` flags back to `false`
- Remove optional production dependencies only if you want a smaller environment
- Keep generated logs under `logs/` for diagnostics
