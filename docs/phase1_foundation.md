# Phase 1 � Foundation (configuration, logging, errors, validation, cache)

This phase adds **standalone** Python packages under `ner_project/`:

| Path | Purpose |
|------|---------|
| `config/settings.py` | Environment-driven settings and feature flags (defaults preserve current behavior). |
| `utils/logger.py` | Optional JSON logs to rotating `debug.log`, `app.log`, `error.log`. |
| `utils/exceptions.py` | Shared error types and `ErrorResponse` helper. |
| `utils/validators.py` | Reusable validation helpers (not wired into routes by default). |
| `services/cache.py` | Optional Redis cache with graceful degradation. |

`app.py` and `ui.py` are **unchanged**. The website behaves exactly as before until you explicitly import and use these modules (or add a thin integration layer later).

## Enabling structured logging

```bash
set ENABLE_LOGGING=true
set LOG_DIR=logs
python app.py
```

Logs are written as one JSON object per line. To ship logs to an HTTP endpoint (fire-and-forget background queue):

```bash
set ENABLE_LOG_SHIPPING=true
set LOG_WEBHOOK_URL=https://example.com/logs
```

## Optional Redis caching

1. Install extras: `pip install -r requirements-prod.txt`
2. Start Redis, then:

```bash
set ENABLE_CACHING=true
set REDIS_URL=redis://127.0.0.1:6379/0
```

If Redis is down or the package is missing, cache operations no-op and callers should continue without cache.

## Validators

Import and call explicitly, for example in a future middleware:

```python
from utils.validators import validate_document_text, validate_file_upload

r = validate_document_text(text)
if not r.valid:
    ...
```

## Tests

From `ner_project/`:

```bash
python -m pytest tests/unit/test_validators.py tests/unit/test_exceptions.py tests/unit/test_utils.py tests/unit/test_cache.py -v
```

## Rollback

- Remove or ignore the new directories (`config/`, `utils/`, `services/`, extra tests) � they are not imported by `app.py`.
- Unset any new environment variables; no database or schema changes were made.
