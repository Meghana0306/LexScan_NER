#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

for d in models/general_best_model models/medical_best_model models/legal_best_model; do
  mkdir -p "$d"
done

echo "Building and starting LexScan containers..."
docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d --build

echo "Waiting for API health..."
for i in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 5
done

curl -fsS http://127.0.0.1:8000/health >/dev/null || { echo "API health check failed"; docker compose logs api; exit 1; }

echo ""
echo "LexScan is running:"
echo "  API: http://localhost:8000/docs"
echo "  UI:  http://localhost:7860"
docker compose ps
