"""
Optional durable feedback storage for active-learning records.

Uses SQLite from the standard library so no migration tooling or external
database is required for initial rollout.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class FeedbackStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            try:
                from config.settings import get_settings

                db_path = get_settings().feedback_db_path
            except Exception:
                db_path = Path("data") / "feedback.sqlite3"
        self.db_path = Path(db_path)
        self._lock = threading.RLock()

    def is_enabled(self) -> bool:
        try:
            from config.settings import get_settings

            return bool(get_settings().enable_feedback_db)
        except Exception:
            return False

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_events (
                    feedback_id TEXT PRIMARY KEY,
                    prediction_id TEXT,
                    created_at REAL NOT NULL,
                    domain TEXT,
                    text_length INTEGER NOT NULL,
                    predicted_entities TEXT NOT NULL,
                    corrected_entities TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def store_feedback(self, payload: dict[str, Any]) -> bool:
        if not self.is_enabled():
            return False
        self.initialize()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO feedback_events (
                    feedback_id, prediction_id, created_at, domain, text_length,
                    predicted_entities, corrected_entities, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("feedback_id"),
                    payload.get("prediction_id"),
                    float(payload.get("timestamp", 0.0)),
                    payload.get("domain"),
                    int(payload.get("text_length", 0)),
                    json.dumps(payload.get("predicted_entities") or [], ensure_ascii=False),
                    json.dumps(payload.get("corrected_entities") or [], ensure_ascii=False),
                    json.dumps(payload.get("metadata") or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
        return True

    def count_feedback(self) -> int:
        if not self.db_path.exists():
            return 0
        self.initialize()
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM feedback_events").fetchone()
        return int(row[0]) if row else 0

    def recent_feedback(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT feedback_id, prediction_id, created_at, domain, text_length,
                       predicted_entities, corrected_entities, metadata
                FROM feedback_events
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [
            {
                "feedback_id": row[0],
                "prediction_id": row[1],
                "created_at": row[2],
                "domain": row[3],
                "text_length": row[4],
                "predicted_entities": json.loads(row[5]),
                "corrected_entities": json.loads(row[6]),
                "metadata": json.loads(row[7]),
            }
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)


feedback_store = FeedbackStore()

