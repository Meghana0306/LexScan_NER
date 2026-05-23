# Security Guide

## API key authentication

Enable:

```dotenv
ENABLE_API_KEY_AUTH=true
API_KEYS=key1,key2
AUTH_EXEMPT_PATHS=/,/static,/api/languages
```

Send the key with:

- Header: `x-api-key: <key>`
- Or query string: `?api_key=<key>`

## Rate limiting

Enable:

```dotenv
ENABLE_RATE_LIMIT=true
RATE_LIMIT_REQUESTS_PER_MINUTE=120
RATE_LIMIT_BURST=30
```

This is an in-memory limiter intended for a single-process deployment or a first production rollout.

## Recommendation

For larger deployments, keep this layer as the app fallback and place a real gateway or reverse proxy in front of the service.
