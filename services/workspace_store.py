"""
SQLite-backed storage for saved smart-workspace documents.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any


class WorkspaceStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            try:
                from config.settings import get_settings

                db_path = get_settings().workspace_store_path
            except Exception:
                db_path = Path("data") / "workspace.sqlite3"
        self.db_path = Path(db_path)
        self._lock = threading.RLock()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_documents (
                    document_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    collection_name TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    subtype TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    text TEXT NOT NULL,
                    analysis_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_document(
        self,
        *,
        title: str,
        collection_name: str,
        text: str,
        domain: str,
        subtype: str,
        analysis: dict[str, Any],
    ) -> str:
        self.initialize()
        document_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workspace_documents (
                    document_id, title, collection_name, domain, subtype,
                    created_at, text, analysis_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    title or "Untitled document",
                    collection_name or "Default",
                    domain or "general",
                    subtype or "general_document",
                    time.time(),
                    text,
                    json.dumps(analysis, ensure_ascii=False),
                ),
            )
            conn.commit()
        return document_id

    def recent_documents(self, limit: int = 20) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT document_id, title, collection_name, domain, subtype, created_at
                FROM workspace_documents
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [
            {
                "document_id": row[0],
                "title": row[1],
                "collection_name": row[2],
                "domain": row[3],
                "subtype": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        self.initialize()
        q = f"%{query.strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT document_id, title, collection_name, domain, subtype, created_at, text, analysis_json
                FROM workspace_documents
                WHERE title LIKE ? OR collection_name LIKE ? OR text LIKE ? OR analysis_json LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (q, q, q, q, int(limit)),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            analysis = json.loads(row[7])
            out.append(
                {
                    "document_id": row[0],
                    "title": row[1],
                    "collection_name": row[2],
                    "domain": row[3],
                    "subtype": row[4],
                    "created_at": row[5],
                    "preview": (row[6] or "")[:220],
                    "entity_count": int(analysis.get("entity_count", 0)),
                    "action_items": analysis.get("action_items", [])[:3],
                }
            )
        return out

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        self.initialize()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT document_id, title, collection_name, domain, subtype, created_at, text, analysis_json
                FROM workspace_documents
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "document_id": row[0],
            "title": row[1],
            "collection_name": row[2],
            "domain": row[3],
            "subtype": row[4],
            "created_at": row[5],
            "text": row[6],
            "analysis": json.loads(row[7]),
        }

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)


workspace_store = WorkspaceStore()

