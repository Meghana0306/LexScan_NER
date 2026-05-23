# Troubleshooting

## Server does not start

- Make sure the virtual environment exists at `venv\Scripts\python.exe`
- Install `requirements.txt` first
- Check whether port `7860` is already in use

## Metrics endpoint returns 404

`/api/metrics` returns `404` when `ENABLE_METRICS=false`. This is expected.

## Redis cache does not work

- Set `ENABLE_CACHING=true`
- Install `requirements-prod.txt`
- Confirm `REDIS_URL` points to a reachable Redis instance

## Feedback endpoint returns accepted false

That means `ENABLE_ACTIVE_LEARNING=false`. Turn it on to persist feedback.

## Logging files are not created

- Set `ENABLE_LOGGING=true`
- Check `LOG_DIR`
- Confirm the process can write to the log directory

## Model tracker files are missing

- Set `ENABLE_MODEL_TRACKER=true`
- Make sure feedback or prediction logging is actually being called by the code path you enabled

## Background jobs return disabled

- Set `ENABLE_BACKGROUND_JOBS=true`
- Use the additive `/api/jobs/...` endpoints rather than the normal synchronous flow

## API returns unauthorized

- Check `ENABLE_API_KEY_AUTH`
- Send a valid `x-api-key` header
- Verify the route is not intentionally protected by your current `AUTH_EXEMPT_PATHS` value
