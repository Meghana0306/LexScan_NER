"""
Centralized configuration from environment variables.

Safe defaults preserve current LexScan behavior. Nothing in this module
mutates global state beyond optional ``load_dotenv`` (non-destructive).

``ai_helper.py`` continues to read ``GROQ_API_KEY`` directly; this module
mirrors those keys for future opt-in integration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_MODELS_DIR = _PROJECT_ROOT / "models"

# Load .env if present; do not override variables already set in the process.
load_dotenv(_PROJECT_ROOT / ".env", override=False)


def _truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of environment-driven settings."""

    # API keys (optional; existing code may still read os.environ directly)
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))

    # Model directories (defaults match src/api/predictor.py layout)
    models_dir: Path = field(default_factory=lambda: Path(os.getenv("MODELS_DIR", str(_DEFAULT_MODELS_DIR))))
    model_path_general: Path = field(default_factory=lambda: Path(os.getenv("MODEL_PATH_GENERAL", "")) or (_DEFAULT_MODELS_DIR / "general_best_model"))
    model_path_medical: Path = field(default_factory=lambda: Path(os.getenv("MODEL_PATH_MEDICAL", "")) or (_DEFAULT_MODELS_DIR / "medical_best_model"))
    model_path_legal: Path = field(default_factory=lambda: Path(os.getenv("MODEL_PATH_LEGAL", "")) or (_DEFAULT_MODELS_DIR / "legal_best_model"))

    # Database / cache (optional; empty DSN means "not configured")
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))

    # App host/port (matches app.py defaults)
    app_host: str = field(default_factory=lambda: os.getenv("APP_HOST", "127.0.0.1"))
    app_port: int = field(default_factory=lambda: _int_env("APP_PORT", 7860))

    # Logging
    enable_logging: bool = field(default_factory=lambda: _truthy("ENABLE_LOGGING", "false"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_dir: Path = field(default_factory=lambda: Path(os.getenv("LOG_DIR", str(_PROJECT_ROOT / "logs"))))
    log_max_bytes: int = field(default_factory=lambda: _int_env("LOG_MAX_BYTES", 5 * 1024 * 1024))
    log_backup_count: int = field(default_factory=lambda: _int_env("LOG_BACKUP_COUNT", 5))
    enable_log_shipping: bool = field(default_factory=lambda: _truthy("ENABLE_LOG_SHIPPING", "false"))
    log_webhook_url: str = field(default_factory=lambda: os.getenv("LOG_WEBHOOK_URL", ""))

    # Feature flags (all off by default)
    enable_caching: bool = field(default_factory=lambda: _truthy("ENABLE_CACHING", "false"))
    enable_metrics: bool = field(default_factory=lambda: _truthy("ENABLE_METRICS", "false"))
    enable_validation: bool = field(default_factory=lambda: _truthy("ENABLE_VALIDATION", "false"))
    enable_request_logging: bool = field(default_factory=lambda: _truthy("ENABLE_REQUEST_LOGGING", "false"))
    enable_preprocessing: bool = field(default_factory=lambda: _truthy("ENABLE_PREPROCESSING", "false"))
    enable_model_cache: bool = field(default_factory=lambda: _truthy("ENABLE_MODEL_CACHE", "false"))
    enable_calibration: bool = field(default_factory=lambda: _truthy("ENABLE_CALIBRATION", "false"))
    enable_model_tracker: bool = field(default_factory=lambda: _truthy("ENABLE_MODEL_TRACKER", "false"))
    enable_active_learning: bool = field(default_factory=lambda: _truthy("ENABLE_ACTIVE_LEARNING", "false"))
    enable_advanced_viz: bool = field(default_factory=lambda: _truthy("ENABLE_ADVANCED_VIZ", "false"))
    enable_data_quality: bool = field(default_factory=lambda: _truthy("ENABLE_DATA_QUALITY", "false"))
    enable_performance_monitor: bool = field(default_factory=lambda: _truthy("ENABLE_PERFORMANCE_MONITOR", "false"))
    enable_api_key_auth: bool = field(default_factory=lambda: _truthy("ENABLE_API_KEY_AUTH", "false"))
    enable_rate_limit: bool = field(default_factory=lambda: _truthy("ENABLE_RATE_LIMIT", "false"))
    enable_background_jobs: bool = field(default_factory=lambda: _truthy("ENABLE_BACKGROUND_JOBS", "false"))
    enable_feedback_db: bool = field(default_factory=lambda: _truthy("ENABLE_FEEDBACK_DB", "false"))

    # Performance monitor thresholds (used when ENABLE_PERFORMANCE_MONITOR=true)
    perf_slow_request_seconds: float = field(default_factory=lambda: _float_env("PERF_SLOW_REQUEST_SECONDS", 120.0))
    perf_min_mean_confidence: float = field(default_factory=lambda: _float_env("PERF_MIN_MEAN_CONFIDENCE", 0.15))

    # Cache TTLs (seconds)
    cache_ttl_ner_seconds: int = field(default_factory=lambda: _int_env("CACHE_TTL_NER_SECONDS", 3600))
    cache_ttl_lang_seconds: int = field(default_factory=lambda: _int_env("CACHE_TTL_LANG_SECONDS", 86400))
    cache_ttl_domain_seconds: int = field(default_factory=lambda: _int_env("CACHE_TTL_DOMAIN_SECONDS", 86400))
    model_cache_ttl_seconds: int = field(default_factory=lambda: _int_env("MODEL_CACHE_TTL_SECONDS", 3600))

    # Calibration and tracking
    calibration_store_path: Path = field(
        default_factory=lambda: Path(os.getenv("CALIBRATION_STORE_PATH", str(_PROJECT_ROOT / "data" / "calibration.json")))
    )
    model_tracker_dir: Path = field(
        default_factory=lambda: Path(os.getenv("MODEL_TRACKER_DIR", str(_PROJECT_ROOT / "logs" / "model_tracker")))
    )
    model_tracker_alert_threshold: float = field(default_factory=lambda: _float_env("MODEL_TRACKER_ALERT_THRESHOLD", 0.7))
    active_learning_dir: Path = field(
        default_factory=lambda: Path(os.getenv("ACTIVE_LEARNING_DIR", str(_PROJECT_ROOT / "logs" / "active_learning")))
    )
    feedback_db_path: Path = field(
        default_factory=lambda: Path(os.getenv("FEEDBACK_DB_PATH", str(_PROJECT_ROOT / "data" / "feedback.sqlite3")))
    )

    # Security and throughput
    api_keys_raw: str = field(default_factory=lambda: os.getenv("API_KEYS", ""))
    auth_exempt_paths_raw: str = field(default_factory=lambda: os.getenv("AUTH_EXEMPT_PATHS", "/,/static,/api/languages"))
    rate_limit_requests_per_minute: int = field(default_factory=lambda: _int_env("RATE_LIMIT_REQUESTS_PER_MINUTE", 120))
    rate_limit_burst: int = field(default_factory=lambda: _int_env("RATE_LIMIT_BURST", 30))

    # Background jobs
    background_job_ttl_seconds: int = field(default_factory=lambda: _int_env("BACKGROUND_JOB_TTL_SECONDS", 3600))
    background_job_max_workers: int = field(default_factory=lambda: _int_env("BACKGROUND_JOB_MAX_WORKERS", 2))
    workspace_store_path: Path = field(
        default_factory=lambda: Path(os.getenv("WORKSPACE_STORE_PATH", str(_PROJECT_ROOT / "data" / "workspace.sqlite3")))
    )

    # Validation limits (used when validators are called explicitly)
    max_document_chars: int = field(default_factory=lambda: _int_env("MAX_DOCUMENT_CHARS", 2_000_000))
    max_upload_bytes: int = field(default_factory=lambda: _int_env("MAX_UPLOAD_BYTES", 50 * 1024 * 1024))

    project_root: Path = field(default_factory=lambda: _PROJECT_ROOT)

    @property
    def api_keys(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.api_keys_raw.split(",") if part.strip())

    @property
    def auth_exempt_paths(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.auth_exempt_paths_raw.split(",") if part.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings snapshot (refresh by restarting the process)."""
    return Settings()


def clear_settings_cache() -> None:
    """Invalidate the cached settings object (mainly for unit tests)."""
    get_settings.cache_clear()
