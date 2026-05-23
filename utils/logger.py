"""
Structured JSON logging (opt-in via ENABLE_LOGGING).

Does not alter existing ``print()`` calls elsewhere. Call ``configure_logging()``
once at process startup if you wire this into the app; until then, importing
this module has no side effects.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any

from config.settings import get_settings


class JsonFormatter(logging.Formatter):
    """One JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Optional structured fields
        for key in ("request_id", "path", "method", "duration_ms", "extra"):
            if hasattr(record, key):
                val = getattr(record, key)
                if val is not None:
                    payload[key] = val
        return json.dumps(payload, ensure_ascii=False)


_ship_queue: queue.Queue[str | None] | None = None
_ship_thread: threading.Thread | None = None


def _ship_worker(url: str, q: queue.Queue[str | None]) -> None:
    try:
        import httpx
    except ImportError:
        return
    while True:
        item = q.get()
        if item is None:
            break
        try:
            httpx.post(url, content=item, headers={"Content-Type": "application/json"}, timeout=5.0)
        except Exception:
            pass


def _ensure_shipper(url: str) -> None:
    global _ship_queue, _ship_thread
    if _ship_queue is not None:
        return
    _ship_queue = queue.Queue(maxsize=256)
    t = threading.Thread(target=_ship_worker, args=(url, _ship_queue), daemon=True)
    t.start()
    _ship_thread = t


class WebhookHandler(logging.Handler):
    """Non-blocking enqueue of JSON log lines to an HTTP endpoint."""

    def __init__(self, url: str) -> None:
        super().__init__(level=logging.INFO)
        self.url = url
        _ensure_shipper(url)

    def emit(self, record: logging.LogRecord) -> None:
        if _ship_queue is None:
            return
        try:
            msg = self.format(record)
            _ship_queue.put_nowait(msg)
        except Exception:
            self.handleError(record)


_configured = False


def configure_logging(force: bool = False) -> None:
    """
    Attach rotating JSON file handlers and optional console + webhook.

    No-op if ENABLE_LOGGING is false unless ``force`` is True (for tests).
    """
    global _configured
    settings = get_settings()
    if _configured and not force:
        return
    if not settings.enable_logging and not force:
        return

    settings.log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("lexscan")
    root.handlers.clear()
    root.setLevel(settings.log_level.upper())

    fmt = JsonFormatter()

    debug_path = settings.log_dir / "debug.log"
    app_path = settings.log_dir / "app.log"
    err_path = settings.log_dir / "error.log"

    h_debug = RotatingFileHandler(
        debug_path, maxBytes=settings.log_max_bytes, backupCount=settings.log_backup_count, encoding="utf-8"
    )
    h_debug.setLevel(logging.DEBUG)
    h_debug.setFormatter(fmt)

    h_app = RotatingFileHandler(
        app_path, maxBytes=settings.log_max_bytes, backupCount=settings.log_backup_count, encoding="utf-8"
    )
    h_app.setLevel(logging.INFO)
    h_app.setFormatter(fmt)

    h_err = RotatingFileHandler(
        err_path, maxBytes=settings.log_max_bytes, backupCount=settings.log_backup_count, encoding="utf-8"
    )
    h_err.setLevel(logging.ERROR)
    h_err.setFormatter(fmt)

    root.addHandler(h_debug)
    root.addHandler(h_app)
    root.addHandler(h_err)

    console = logging.StreamHandler()
    console.setLevel(settings.log_level.upper())
    console.setFormatter(fmt)
    root.addHandler(console)

    if settings.enable_log_shipping and settings.log_webhook_url:
        wh = WebhookHandler(settings.log_webhook_url)
        wh.setFormatter(fmt)
        wh.setLevel(logging.INFO)
        root.addHandler(wh)

    _configured = True


def reset_logging_configuration() -> None:
    """Remove LexScan logging handlers (for isolated tests)."""
    global _configured
    log = logging.getLogger("lexscan")
    log.handlers.clear()
    log.setLevel(logging.NOTSET)
    _configured = False


def get_logger(name: str = "lexscan") -> logging.Logger:
    """
    Return the ``lexscan`` namespace logger (child loggers propagate to it).

    If ENABLE_LOGGING is true and logging has not been configured yet,
    ``configure_logging()`` is invoked lazily.
    """
    settings = get_settings()
    if settings.enable_logging and not _configured:
        configure_logging()
    return logging.getLogger(f"lexscan.{name}" if name != "lexscan" else "lexscan")
