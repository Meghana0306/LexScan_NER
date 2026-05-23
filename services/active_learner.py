"""
Optional active-learning feedback collector.

Stores user corrections for later review and can forward matched feedback to
the model tracker when a prediction id is supplied.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


def _enabled() -> bool:
    try:
        from config.settings import get_settings

        return bool(get_settings().enable_active_learning)
    except Exception:
        return False


def _store_dir() -> Path:
    try:
        from config.settings import get_settings

        return get_settings().active_learning_dir
    except Exception:
        return Path("logs") / "active_learning"


def _feedback_path() -> Path:
    return _store_dir() / "feedback.jsonl"


def collect_feedback(
    *,
    prediction_id: str | None,
    text: str,
    domain: str,
    predicted_entities: list[dict[str, Any]],
    corrected_entities: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not _enabled():
        return {
            "accepted": False,
            "stored": False,
            "message": "active learning disabled",
        }

    path = _feedback_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    feedback_id = uuid.uuid4().hex
    payload = {
        "feedback_id": feedback_id,
        "prediction_id": prediction_id,
        "timestamp": time.time(),
        "text_length": len(text or ""),
        "domain": domain,
        "predicted_entities": predicted_entities or [],
        "corrected_entities": corrected_entities or [],
        "metadata": metadata or {},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    feedback_db_stored = False
    try:
        from services.feedback_store import feedback_store

        feedback_db_stored = bool(feedback_store.store_feedback(payload))
    except Exception:
        feedback_db_stored = False

    tracker_synced = False
    if prediction_id:
        try:
            from services.model_tracker import model_tracker

            tracker_synced = bool(
                model_tracker.record_feedback(
                    prediction_id=prediction_id,
                    corrected_entities=corrected_entities,
                    metadata={"source": "active_learning", **(metadata or {})},
                )
            )
        except Exception:
            tracker_synced = False

    return {
        "accepted": True,
        "stored": True,
        "feedback_id": feedback_id,
        "tracker_synced": tracker_synced,
        "feedback_db_stored": feedback_db_stored,
        "path": str(path),
    }
