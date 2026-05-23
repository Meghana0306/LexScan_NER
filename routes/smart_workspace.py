"""
Additive smart-workspace routes built on top of the existing NER flow.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

import ui as ui_logic

router = APIRouter()


def _analyze_text_core(text: str, domain: str) -> dict[str, Any]:
    return ui_logic.analyze_text(text, domain)


@router.post("/api/workspace/analyze")
async def workspace_analyze(payload: dict = Body(...)) -> JSONResponse:
    text = (payload.get("text") or "").strip()
    domain = payload.get("domain") or "auto"
    title = (payload.get("title") or "").strip() or "Untitled document"
    collection_name = (payload.get("collection_name") or "").strip() or "Default"
    save_document = bool(payload.get("save_document", True))
    if not text:
        return JSONResponse({"error": "Please provide document text."}, status_code=400)
    try:
        from services.document_intelligence import build_workspace_analysis
        from services.workspace_store import workspace_store

        base = _analyze_text_core(text, domain)
        analysis = build_workspace_analysis(text, base)
        document_id = None
        if save_document:
            document_id = workspace_store.save_document(
                title=title,
                collection_name=collection_name,
                text=text,
                domain=analysis.get("domain", "general"),
                subtype=analysis.get("subtype", "general_document"),
                analysis=analysis,
            )
        return JSONResponse(
            {
                "title": title,
                "collection_name": collection_name,
                "document_id": document_id,
                "analysis": analysis,
            }
        )
    except Exception as exc:
        return JSONResponse({"error": "workspace analysis failed", "detail": repr(exc)}, status_code=503)


@router.post("/api/workspace/compare")
async def workspace_compare(payload: dict = Body(...)) -> JSONResponse:
    text_a = (payload.get("text_a") or "").strip()
    text_b = (payload.get("text_b") or "").strip()
    domain_a = payload.get("domain_a") or "auto"
    domain_b = payload.get("domain_b") or "auto"
    if not text_a or not text_b:
        return JSONResponse({"error": "Please provide both documents for comparison."}, status_code=400)
    try:
        from services.document_intelligence import compare_documents

        analysis_a = _analyze_text_core(text_a, domain_a)
        analysis_b = _analyze_text_core(text_b, domain_b)
        comparison = compare_documents(text_a, text_b, analysis_a, analysis_b)
        return JSONResponse({"comparison": comparison})
    except Exception as exc:
        return JSONResponse({"error": "compare failed", "detail": repr(exc)}, status_code=503)


@router.post("/api/workspace/question")
async def workspace_question(payload: dict = Body(...)) -> JSONResponse:
    text = (payload.get("text") or "").strip()
    question = (payload.get("question") or "").strip()
    if not text or not question:
        return JSONResponse({"error": "Please provide text and a question."}, status_code=400)
    try:
        from services.document_intelligence import grounded_answer

        answer = grounded_answer(text, question)
        return JSONResponse(answer)
    except Exception as exc:
        return JSONResponse({"error": "question answering failed", "detail": repr(exc)}, status_code=503)


@router.get("/api/workspace/search")
async def workspace_search(query: str = Query(..., min_length=1)) -> JSONResponse:
    try:
        from services.workspace_store import workspace_store

        results = workspace_store.search(query, limit=20)
        return JSONResponse({"results": results})
    except Exception as exc:
        return JSONResponse({"error": "search failed", "detail": repr(exc)}, status_code=503)


@router.get("/api/workspace/documents")
async def workspace_documents() -> JSONResponse:
    try:
        from services.workspace_store import workspace_store

        return JSONResponse({"documents": workspace_store.recent_documents(limit=20)})
    except Exception as exc:
        return JSONResponse({"error": "list failed", "detail": repr(exc)}, status_code=503)


@router.get("/api/workspace/documents/{document_id}")
async def workspace_document_detail(document_id: str) -> JSONResponse:
    try:
        from services.workspace_store import workspace_store

        doc = workspace_store.get_document(document_id)
        if doc is None:
            return JSONResponse({"error": "document not found"}, status_code=404)
        return JSONResponse(doc)
    except Exception as exc:
        return JSONResponse({"error": "detail failed", "detail": repr(exc)}, status_code=503)
