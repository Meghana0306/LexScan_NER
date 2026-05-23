# LexScan API Documentation

## Existing UI-backed endpoints

### `GET /`

Serves the LexScan web UI.

### `GET /api/languages`

Returns the supported output languages.

### `POST /api/extract`

Uploads a document and extracts readable text.

Response fields:

- `text`
- `file_type`
- `filename`

### `POST /api/document/analyze`

Analyzes document text through the existing `ui.py` workflow.

Request body:

```json
{
  "text": "Patient has diabetes mellitus.",
  "domain": "auto",
  "language": "English"
}
```

Response includes:

- `display_text`
- `status`
- `result`
- `summary_html`
- `table_rows`
- `highlight_html`
- `domain_html`
- `insight_html`
- `report`

### `POST /api/document/report/pdf`

Returns a generated PDF report.

### `POST /api/assistant`

Question-answer helper over document context.

### `POST /api/batch`

Analyzes multiple text blocks using the current batch flow.

### `POST /api/multilang/translate`

Translates document text before analysis.

### `POST /api/multilang/analyze`

Analyzes translated text and returns summary and report details.

### `POST /api/multilang/report/pdf`

Returns a multilingual PDF report.

## Additive production endpoints

### `GET /api/health`

Readiness-style health response with predictor snapshot.

### `GET /api/status`

Returns current feature-flag and runtime status.

### `GET /api/metrics`

Prometheus-compatible metrics when `ENABLE_METRICS=true`.

### `POST /api/feedback`

Stores user correction feedback for later model improvement.

Example:

```json
{
  "prediction_id": "optional-id",
  "text": "Court hearing tomorrow",
  "domain": "legal",
  "predicted_entities": [
    {"text": "tomorrow", "label": "DATE"}
  ],
  "corrected_entities": [
    {"text": "Court", "label": "COURT"}
  ],
  "notes": "Model missed the court entity"
}
```

### `POST /api/jobs/document/analyze`

Creates an asynchronous document-analysis job when `ENABLE_BACKGROUND_JOBS=true`.

### `GET /api/jobs/{job_id}`

Returns the current status and result for a background job.

### `GET /api/jobs`

Lists recent background jobs.
