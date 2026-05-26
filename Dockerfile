# ================================================
# LexScan NER - Multi-stage Dockerfile
# ================================================

FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements-docker.txt requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-docker.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu && \
    python -m spacy download en_core_web_sm --no-deps || true

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs outputs data models

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    NER_SKIP_BOOTSTRAP=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    APP_HOST=0.0.0.0 \
    APP_PORT=7860

# ==================== API Service ====================
FROM base AS api
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["python", "run_api.py"]

# ==================== UI Service ====================
FROM base AS ui
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD curl -fsS http://127.0.0.1:7860/ || exit 1

CMD ["python", "app.py"]