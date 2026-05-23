"""
Simple in-process background job runner for document analysis.

Provides additive async-style endpoints without replacing the current
request/response workflow.
"""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class JobRecord:
    job_id: str
    status: str
    created_at: float
    updated_at: float
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class JobQueue:
    def __init__(self) -> None:
        self._executor: ThreadPoolExecutor | None = None
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.RLock()

    def is_enabled(self) -> bool:
        try:
            from config.settings import get_settings

            return bool(get_settings().enable_background_jobs)
        except Exception:
            return False

    def submit(self, fn: Callable[..., dict[str, Any]], **payload: Any) -> JobRecord:
        self._ensure_executor()
        self._purge_old_jobs()
        job_id = uuid.uuid4().hex
        now = time.time()
        record = JobRecord(job_id=job_id, status="queued", created_at=now, updated_at=now, payload=dict(payload))
        with self._lock:
            self._jobs[job_id] = record
        assert self._executor is not None
        self._executor.submit(self._run_job, job_id, fn, payload)
        return record

    def get(self, job_id: str) -> JobRecord | None:
        self._purge_old_jobs()
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> list[JobRecord]:
        self._purge_old_jobs()
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.created_at, reverse=True)
        return jobs[:limit]

    def _ensure_executor(self) -> None:
        if self._executor is not None:
            return
        try:
            from config.settings import get_settings

            workers = max(int(get_settings().background_job_max_workers), 1)
        except Exception:
            workers = 2
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="lexscan-job")

    def _run_job(self, job_id: str, fn: Callable[..., dict[str, Any]], payload: dict[str, Any]) -> None:
        self._update(job_id, status="running")
        try:
            result = fn(**payload)
            self._update(job_id, status="succeeded", result=result, error=None)
        except Exception as exc:
            self._update(job_id, status="failed", result=None, error=repr(exc))

    def _update(self, job_id: str, *, status: str, result: dict[str, Any] | None = None, error: str | None = None) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.status = status
            record.updated_at = time.time()
            record.result = result
            record.error = error

    def _purge_old_jobs(self) -> None:
        try:
            from config.settings import get_settings

            ttl = max(int(get_settings().background_job_ttl_seconds), 60)
        except Exception:
            ttl = 3600
        cutoff = time.time() - ttl
        with self._lock:
            for job_id in list(self._jobs.keys()):
                record = self._jobs[job_id]
                if record.updated_at < cutoff:
                    self._jobs.pop(job_id, None)

    def reset(self) -> None:
        with self._lock:
            self._jobs.clear()
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
        self._executor = None


job_queue = JobQueue()

