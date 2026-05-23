"""
Optional production-facing endpoints.

These routes are additive only and do not alter existing request flows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

import ui as ui_logic

router = APIRouter()


def _predictor_snapshot() -> dict[str, Any]:
    predictor = getattr(ui_logic, "_PREDICTOR", None)
    if predictor is None:
        return {"loaded": False, "models": []}
    try:
        return {"loaded": True, "models": predictor.get_loaded_models()}
    except Exception:
        return {"loaded": True, "models": []}


@router.get("/api/health")
async def health() -> dict[str, Any]:
    predictor = _predictor_snapshot()
    return {
        "status": "ok",
        "service": "LexScan",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "predictor_loaded": predictor["loaded"],
        "models_loaded": predictor["models"],
    }


@router.get("/api/status")
async def status() -> dict[str, Any]:
    try:
        from config.settings import get_settings

        s = get_settings()
        predictor = _predictor_snapshot()
        return {
            "service": "LexScan",
            "environment": {
                "app_host": s.app_host,
                "app_port": s.app_port,
                "models_dir": str(s.models_dir),
                "log_dir": str(s.log_dir),
            },
            "features": {
                "logging": s.enable_logging,
                "request_logging": s.enable_request_logging,
                "metrics": s.enable_metrics,
                "validation": s.enable_validation,
                "data_quality": s.enable_data_quality,
                "preprocessing": s.enable_preprocessing,
                "caching": s.enable_caching,
                "model_cache": s.enable_model_cache,
                "calibration": s.enable_calibration,
                "model_tracker": s.enable_model_tracker,
                "active_learning": s.enable_active_learning,
                "api_key_auth": s.enable_api_key_auth,
                "rate_limit": s.enable_rate_limit,
                "background_jobs": s.enable_background_jobs,
                "feedback_db": s.enable_feedback_db,
            },
            "runtime": {
                "predictor_loaded": predictor["loaded"],
                "models_loaded": predictor["models"],
            },
        }
    except Exception as exc:
        return {"service": "LexScan", "status": "degraded", "error": repr(exc)}


def _run_document_analysis_job(*, text: str, domain: str, language: str) -> dict[str, Any]:
    display_text, status, summary_html, table_rows, result, highlight_html, domain_html, insight_html, report_path = ui_logic.analyze_document(
        None,
        text,
        domain,
        language,
    )
    report = None
    if report_path:
        from app import _store_report

        report = _store_report(report_path, "lexscan-job-report")
    return {
        "display_text": display_text,
        "status": status,
        "result": result,
        "summary_html": summary_html,
        "table_rows": table_rows,
        "highlight_html": highlight_html,
        "domain_html": domain_html,
        "insight_html": insight_html,
        "report": report,
    }


@router.post("/api/feedback")
async def feedback(payload: dict = Body(...)) -> JSONResponse:
    corrected_entities = payload.get("corrected_entities") or []
    if not isinstance(corrected_entities, list):
        return JSONResponse({"error": "corrected_entities must be a list"}, status_code=400)

    try:
        from services.active_learner import collect_feedback

        result = collect_feedback(
            prediction_id=payload.get("prediction_id"),
            text=payload.get("text") or "",
            domain=payload.get("domain") or "unknown",
            predicted_entities=payload.get("predicted_entities") or [],
            corrected_entities=corrected_entities,
            metadata={"notes": payload.get("notes") or ""},
        )
        status_code = 200 if result.get("accepted", False) else 202
        return JSONResponse(result, status_code=status_code)
    except Exception as exc:
        return JSONResponse({"error": "feedback unavailable", "detail": repr(exc)}, status_code=503)


@router.post("/api/jobs/document/analyze")
async def create_document_analysis_job(payload: dict = Body(...)) -> JSONResponse:
    try:
        from config.settings import get_settings

        if not get_settings().enable_background_jobs:
            return JSONResponse({"error": "background jobs disabled"}, status_code=404)
        from services.job_queue import job_queue
    except Exception as exc:
        return JSONResponse({"error": "background jobs unavailable", "detail": repr(exc)}, status_code=503)

    record = job_queue.submit(
        _run_document_analysis_job,
        text=payload.get("text") or "",
        domain=payload.get("domain") or "auto",
        language=payload.get("language") or "English",
    )
    return JSONResponse(
        {
            "job_id": record.job_id,
            "status": record.status,
            "created_at": record.created_at,
        },
        status_code=202,
    )


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> JSONResponse:
    try:
        from config.settings import get_settings

        if not get_settings().enable_background_jobs:
            return JSONResponse({"error": "background jobs disabled"}, status_code=404)
        from services.job_queue import job_queue
    except Exception as exc:
        return JSONResponse({"error": "background jobs unavailable", "detail": repr(exc)}, status_code=503)

    record = job_queue.get(job_id)
    if record is None:
        return JSONResponse({"error": "job not found"}, status_code=404)
    return JSONResponse(
        {
            "job_id": record.job_id,
            "status": record.status,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "result": record.result,
            "error": record.error,
        }
    )


@router.get("/api/jobs")
async def list_jobs() -> JSONResponse:
    try:
        from config.settings import get_settings

        if not get_settings().enable_background_jobs:
            return JSONResponse({"error": "background jobs disabled"}, status_code=404)
        from services.job_queue import job_queue
    except Exception as exc:
        return JSONResponse({"error": "background jobs unavailable", "detail": repr(exc)}, status_code=503)

    jobs = job_queue.list_jobs(limit=20)
    return JSONResponse(
        {
            "jobs": [
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                }
                for job in jobs
            ]
        }
    )
