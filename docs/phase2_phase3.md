# Phase 2 � Monitoring & Phase 3 � Data quality

## Phase 2

### Metrics (`services/metrics.py`)

- **Flag:** `ENABLE_METRICS=true`
- **Endpoint:** `GET /api/metrics` � Prometheus text exposition (404 when disabled).
- **Series:** document counters and route histograms per handler name, HTTP latency histogram, entity-count histogram.
- **Integration:** `app.py` calls `record_route_finished` in `finally` blocks; `middleware/logging_middleware.py` records HTTP timings when metrics are enabled.

### Request logging (`middleware/logging_middleware.py`)

- **Flags:** `ENABLE_REQUEST_LOGGING=true` (uses structured `lexscan.http` logger when `ENABLE_LOGGING=true`; otherwise stdlib logging).
- Skips `/static/*` noise.

### Performance hints (`services/performance_monitor.py`)

- **Flag:** `ENABLE_PERFORMANCE_MONITOR=true`
- Logs warnings for slow requests (`PERF_SLOW_REQUEST_SECONDS`, default 120) and low mean token confidence (`PERF_MIN_MEAN_CONFIDENCE`, default 0.15).
- Never changes model outputs.

## Phase 3

### Data quality (`services/data_quality.py`)

- **Flag:** `ENABLE_DATA_QUALITY=true`
- Runs `assess_text` (encoding, length, PII hints, null bytes) and logs warnings only.
- Wired via `_lexscan_prepare_text` in `app.py` (same path as optional preprocessing).

### Text preprocessing (`services/text_preprocessor.py`)

- **Flag:** `ENABLE_PREPROCESSING=true`
- NFC unicode, CRLF normalization, unicode dash/quotes to ASCII forms, whitespace tidy.
- Applied in document, batch, multilingual, assistant, and extract flows when enabled.

## `app.py` behavior (flags off)

With all new flags at default `false`, responses match prior behavior except:

- **`GET /api/metrics`** always exists and returns **404** with `{"error":"metrics disabled"}` (new route).

## Suggested checks

```powershell
cd d:\MultiDomainDL\ner_project
$env:ENABLE_METRICS="true"
$env:ENABLE_LOGGING="true"
$env:ENABLE_REQUEST_LOGGING="true"
.\venv\Scripts\python.exe app.py
# Visit http://127.0.0.1:7860/api/metrics
```

## Tests

Heavy `tests/unit/test_api.py` loads real PyTorch models; run foundation tests only:

```powershell
.\venv\Scripts\python.exe -m pytest tests\unit\ --ignore=tests\unit\test_api.py -v
```
