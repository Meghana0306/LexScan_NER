# Monitoring Guide

## Metrics

- Enable with `ENABLE_METRICS=true`
- Scrape `GET /api/metrics`

Useful metrics already exposed:

- `lexscan_documents_processed_total`
- `lexscan_handler_errors_total`
- `lexscan_route_duration_seconds`
- `lexscan_http_request_duration_seconds`
- `lexscan_entity_count`

## Recommended alerts

- High 5xx rate on API handlers
- Rising route latency
- Degraded mean confidence from the performance monitor
- Background job failures
- Feedback correction volume spikes

## Suggested dashboard panels

- Requests per minute
- P95 route latency
- Error count by endpoint
- Documents processed by endpoint
- Entity count distribution
- Background job states
- Feedback count over time
