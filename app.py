"""
app.py — LexScan (HTML/CSS/JS UI + working backend)

This starts a FastAPI server that:
- Serves the modern white UI from `LexScan/templates/index.html`
- Serves static assets from `LexScan/static/*`
- Provides JSON/PDF endpoints backed by the proven logic in `ui.py`

Run:
    python app.py

Open:
    http://127.0.0.1:7860
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = BASE_DIR / "venv" / "Scripts" / "python.exe"
WEB_DIR = BASE_DIR / "LexScan"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


def _bootstrap_to_project_venv():
    if os.getenv("NER_SKIP_BOOTSTRAP") == "1":
        return
    if not VENV_PYTHON.exists():
        return
    if Path(sys.executable).resolve() == VENV_PYTHON.resolve():
        return
    try:
        import fastapi  # noqa: F401
    except ModuleNotFoundError:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])


_bootstrap_to_project_venv()

from fastapi import FastAPI, UploadFile, File, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

import ui as ui_logic


app = FastAPI(title="LexScan Web")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
REPORT_CACHE: dict[str, str] = {}


def _init_lexscan_production(application: FastAPI) -> None:
    """Opt-in logging, metrics HTTP instrumentation, and structured logs."""
    try:
        from config.settings import get_settings

        s = get_settings()
    except Exception:
        return
    try:
        if s.enable_logging:
            from utils.logger import configure_logging

            configure_logging()
    except Exception:
        pass
    try:
        from middleware.security_middleware import SecurityMiddleware

        application.add_middleware(SecurityMiddleware)
    except Exception:
        pass
    try:
        if s.enable_request_logging or s.enable_metrics:
            from middleware.logging_middleware import RequestLoggingMiddleware

            application.add_middleware(RequestLoggingMiddleware)
    except Exception:
        pass


_init_lexscan_production(app)


def _init_lexscan_optional_routes(application: FastAPI) -> None:
    """Mount additive production-only endpoints without touching existing ones."""
    try:
        from routes.production_endpoints import router as production_router

        application.include_router(production_router)
    except Exception:
        pass
    try:
        from routes.smart_workspace import router as smart_workspace_router

        application.include_router(smart_workspace_router)
    except Exception:
        pass


_init_lexscan_optional_routes(app)


@app.on_event("startup")
async def _lexscan_startup() -> None:
    """Warm optional stores so additive features are ready before first use."""
    try:
        from services.workspace_store import workspace_store

        workspace_store.initialize()
    except Exception:
        pass
    try:
        from services.feedback_store import feedback_store

        feedback_store.initialize()
    except Exception:
        pass


def _lexscan_validate_document_text(text: str):
    """When ENABLE_VALIDATION=true, return a JSONResponse or None."""
    try:
        from config.settings import get_settings

        if not get_settings().enable_validation:
            return None
        from utils.exceptions import format_error_response
        from utils.validators import validate_document_text

        r = validate_document_text(text)
        if not r.valid:
            return JSONResponse(
                format_error_response(
                    "; ".join(r.errors),
                    "validation_error",
                    detail={"warnings": r.warnings},
                ),
                status_code=400,
            )
    except Exception:
        return None
    return None


def _lexscan_prepare_text(text: str, *, route: str) -> str:
    """Data-quality logging (optional) + preprocessing (optional). Never raises."""
    t = text or ""
    if not t:
        return t
    try:
        from services.data_quality import log_data_quality_warnings

        log_data_quality_warnings(t, context=route)
    except Exception:
        pass
    try:
        from config.settings import get_settings

        if get_settings().enable_preprocessing:
            from services.text_preprocessor import preprocess_text

            return preprocess_text(t)
    except Exception:
        return t
    return t


def _lexscan_after_route(endpoint: str, started: float, result: dict | None, exc: BaseException | None) -> None:
    elapsed = time.perf_counter() - started
    try:
        from services.metrics import record_route_finished

        record_route_finished(endpoint, elapsed, result, exc)
    except Exception:
        pass
    try:
        from services.performance_monitor import record_analysis

        record_analysis(endpoint, elapsed, result, exc)
    except Exception:
        pass


def _store_report(path: str, prefix: str) -> dict:
    report_id = uuid.uuid4().hex
    REPORT_CACHE[report_id] = path
    p = Path(path)
    size = p.stat().st_size if p.exists() else 0
    size_label = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.2f} MB"
    return {"id": report_id, "filename": p.name or f"{prefix}.pdf", "size_bytes": size, "size_label": size_label}


@app.get("/", response_class=HTMLResponse)
async def index():
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8", errors="ignore")
    return HTMLResponse(content=html)


@app.get("/api/languages")
async def languages():
    return {"languages": ui_logic.SUPPORTED_LANGUAGES}


@app.get("/api/metrics")
async def prometheus_metrics():
    """Prometheus scrape endpoint when ENABLE_METRICS=true."""
    try:
        from services.metrics import render_metrics_payload

        payload = render_metrics_payload()
        if payload is None:
            return JSONResponse({"error": "metrics disabled"}, status_code=404)
        body, ctype = payload
        return Response(content=body, media_type=ctype)
    except Exception:
        return JSONResponse({"error": "metrics unavailable"}, status_code=503)


@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    # Save to temp path and reuse existing extractor
    suffix = Path(file.filename or "upload").suffix or ".bin"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    content = await file.read()
    tmp.write(content)
    tmp.close()
    try:
        text, file_type = ui_logic.extract_text_from_path(tmp.name)
    finally:
        # keep temp for debugging? remove to avoid leaks
        try:
            Path(tmp.name).unlink(missing_ok=True)
        except Exception:
            pass
    text = _lexscan_prepare_text(text or "", route="extract")
    if not (text or "").strip():
        return JSONResponse({"error": "No readable text found in file"}, status_code=400)
    return {"text": text[:10000], "file_type": file_type, "filename": file.filename}


@app.post("/api/document/analyze")
async def document_analyze(payload: dict = Body(...)):
    text = (payload.get("text") or "")
    domain = (payload.get("domain") or "auto")
    language = (payload.get("language") or "English")
    bad = _lexscan_validate_document_text(text)
    if bad is not None:
        return bad
    t0 = time.perf_counter()
    result: dict | None = None
    exc: Exception | None = None
    try:
        text = _lexscan_prepare_text(text, route="document_analyze")
        # use ui.py proven logic (includes translation + AI insight + report)
        display_text, status, summary_html, table_rows, result, highlight_html, domain_html, insight_html, report_path = ui_logic.analyze_document(
            None,
            text,
            domain,
            language,
        )
        report = _store_report(report_path, "lexscan-report") if report_path else None
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
    except Exception as e:
        exc = e
        raise
    finally:
        _lexscan_after_route("document_analyze", t0, result if isinstance(result, dict) else None, exc)


@app.post("/api/document/report/pdf")
async def document_report_pdf(payload: dict = Body(...)):
    report_id = payload.get("report_id")
    if report_id and report_id in REPORT_CACHE:
        report_path = REPORT_CACHE[report_id]
        if Path(report_path).exists():
            return FileResponse(report_path, media_type="application/pdf", filename=Path(report_path).name)

    text = (payload.get("text") or "")
    domain = (payload.get("domain") or "auto")
    language = (payload.get("language") or "English")
    bad = _lexscan_validate_document_text(text)
    if bad is not None:
        return bad
    t0 = time.perf_counter()
    exc: Exception | None = None
    try:
        text = _lexscan_prepare_text(text, route="document_report_pdf")
        _display_text, _status, _summary_html, _table_rows, _result, _highlight_html, _domain_html, _insight_html, report_path = ui_logic.analyze_document(
            None,
            text,
            domain,
            language,
        )
        if not report_path:
            return JSONResponse({"error": "Could not generate report PDF"}, status_code=500)
        return FileResponse(report_path, media_type="application/pdf", filename=Path(report_path).name or "lexscan-report.pdf")
    except Exception as e:
        exc = e
        raise
    finally:
        _lexscan_after_route("document_report_pdf", t0, None, exc)


@app.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    report_path = REPORT_CACHE.get(report_id)
    if not report_path or not Path(report_path).exists():
        return JSONResponse({"error": "Report not found"}, status_code=404)
    return FileResponse(report_path, media_type="application/pdf", filename=Path(report_path).name)


@app.post("/api/assistant")
async def assistant(payload: dict = Body(...)):
    t0 = time.perf_counter()
    exc: Exception | None = None
    try:
        context = _lexscan_prepare_text(payload.get("context") or "", route="assistant_context")
        question = _lexscan_prepare_text(payload.get("question") or "", route="assistant_question")
        status, answer = ui_logic.ask_assistant(context, question)
        return {"status": status, "answer": answer}
    except Exception as e:
        exc = e
        raise
    finally:
        _lexscan_after_route("assistant", t0, None, exc)


@app.post("/api/batch")
async def batch(payload: dict = Body(...)):
    text_blocks = payload.get("text_blocks") or ""
    domain = payload.get("domain") or "auto"
    if (text_blocks or "").strip():
        bad = _lexscan_validate_document_text(text_blocks)
        if bad is not None:
            return bad
    t0 = time.perf_counter()
    exc: Exception | None = None
    try:
        text_blocks = _lexscan_prepare_text(text_blocks, route="batch")
        status, table_rows, full = ui_logic.batch_analyze(text_blocks, domain)
        return {"status": status, "rows": table_rows, "full": full}
    except Exception as e:
        exc = e
        raise
    finally:
        _lexscan_after_route("batch", t0, None, exc)


@app.post("/api/multilang/translate")
async def multilang_translate(payload: dict = Body(...)):
    text = payload.get("text") or ""
    language = payload.get("language") or "English"
    if (text or "").strip():
        bad = _lexscan_validate_document_text(text)
        if bad is not None:
            return bad
    text = _lexscan_prepare_text(text, route="multilang_translate")
    t0 = time.perf_counter()
    exc: Exception | None = None
    try:
        if language == "English":
            translated = ui_logic.ask_ai(
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Translate the following text to English. "
                            "Return only the translated English text with the same meaning.\n\n"
                            f"{text}"
                        ),
                    }
                ],
                system_prompt="You are a precise translator for legal and medical documents.",
            )
            if ui_logic.is_ai_error(translated):
                return JSONResponse(
                    {
                        "error": (
                            "English translation could not be completed. "
                            "Please check API key/quota/network and try again."
                        )
                    },
                    status_code=400,
                )
            status = "Translation complete. Text translated to English."
        else:
            status, translated = ui_logic.translate_text(text, language)
            if not translated:
                return JSONResponse({"error": status or "Translation failed"}, status_code=400)
        return {"status": status, "translated_text": translated}
    except Exception as e:
        exc = e
        raise
    finally:
        _lexscan_after_route("multilang_translate", t0, None, exc)


@app.post("/api/multilang/analyze")
async def multilang_analyze(payload: dict = Body(...)):
    source_text = payload.get("source_text") or ""
    translated_text = payload.get("translated_text") or ""
    domain = payload.get("domain") or "auto"
    language = payload.get("language") or "English"
    effective_translated = translated_text if translated_text else source_text
    if (effective_translated or "").strip():
        bad = _lexscan_validate_document_text(effective_translated)
        if bad is not None:
            return bad
    t0 = time.perf_counter()
    result: dict | None = None
    exc: Exception | None = None
    try:
        if source_text:
            _lexscan_prepare_text(source_text, route="multilang_source")
        effective_translated = _lexscan_prepare_text(effective_translated, route="multilang_analyze")
        effective_source = ""
        status, display_text, summary_html, badges_html, result, insight_html, report_path = ui_logic.analyze_translated_text(
            effective_source,
            effective_translated,
            domain,
            language,
        )
        report = _store_report(report_path, "lexscan-multilang-report") if report_path else None
        return {
            "status": status,
            "display_text": display_text,
            "summary_html": summary_html,
            "badges_html": badges_html,
            "result": result,
            "insight_html": insight_html,
            "report": report,
        }
    except Exception as e:
        exc = e
        raise
    finally:
        _lexscan_after_route("multilang_analyze", t0, result if isinstance(result, dict) else None, exc)


@app.post("/api/multilang/report/pdf")
async def multilang_report_pdf(payload: dict = Body(...)):
    report_id = payload.get("report_id")
    if report_id and report_id in REPORT_CACHE:
        report_path = REPORT_CACHE[report_id]
        if Path(report_path).exists():
            return FileResponse(report_path, media_type="application/pdf", filename=Path(report_path).name)

    source_text = payload.get("source_text") or ""
    translated_text = payload.get("translated_text") or ""
    domain = payload.get("domain") or "auto"
    language = payload.get("language") or "English"
    effective = translated_text if translated_text else source_text
    if (effective or "").strip():
        bad = _lexscan_validate_document_text(effective)
        if bad is not None:
            return bad
    t0 = time.perf_counter()
    exc: Exception | None = None
    try:
        if source_text:
            _lexscan_prepare_text(source_text, route="multilang_report_source")
        translated_for_report = _lexscan_prepare_text(translated_text or source_text, route="multilang_report_pdf")
        _status, _display_text, _summary_html, _badges_html, _result, _insight_html, report_path = ui_logic.analyze_translated_text(
            source_text,
            translated_for_report,
            domain,
            language,
        )
        if not report_path:
            return JSONResponse({"error": "Could not generate report PDF"}, status_code=500)
        return FileResponse(report_path, media_type="application/pdf", filename=Path(report_path).name or "lexscan-multilang-report.pdf")
    except Exception as e:
        exc = e
        raise
    finally:
        _lexscan_after_route("multilang_report_pdf", t0, None, exc)


def main():
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "7860"))
    uvicorn.run(app, host=host, port=port, log_level="info")


# ============================================
# SMART WORKSPACE & COMPARE ROUTES
# ============================================

import uuid
from datetime import datetime

# Try to import workspace services, if they don't exist, create them
try:
    from services.smart_workspace import analyze_workspace, compare_documents
    from data.workspace_store import WorkspaceStore
    workspace_store = WorkspaceStore()
except:
    # Fallback if files don't exist yet
    print("⚠️ Smart Workspace files not found - creating stubs...")
    workspace_store = None


@app.post("/api/workspace/analyze")
async def workspace_analyze(request: Request):
    """Smart Workspace Analysis"""
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        domain = data.get("domain", "auto")
        storage = data.get("storage", "analyze_only")
        title = data.get("title", "Untitled")
        collection = data.get("collection", "General")
        
        if not text:
            return {"status": "error", "message": "Document text required"}
        
        # Basic analysis (without external services)
        analysis = {
            "subtype": classify_document(text, domain),
            "explanation": text[:200] + "...",
            "red_flags": extract_flags(text, domain),
            "action_items": extract_actions(text, domain),
            "timeline": extract_dates(text),
            "relations": [],
            "normalized_entities": [],
            "timestamp": datetime.now().isoformat()
        }
        
        doc_id = None
        if storage == "analyze_and_save" and workspace_store:
            doc_id = str(uuid.uuid4())
            workspace_store.save_document(
                doc_id=doc_id,
                title=title,
                collection=collection,
                domain=domain,
                content=text,
                analysis=analysis
            )
        
        return {
            "status": "success",
            "analysis": analysis,
            "document_id": doc_id
        }
    
    except Exception as e:
        logger.error(f"Workspace analyze error: {str(e)}")
        return {
            "status": "error",
            "message": f"Analysis failed: {str(e)}"
        }


@app.post("/api/workspace/compare")
async def workspace_compare(request: Request):
    """Compare Two Documents"""
    try:
        data = await request.json()
        text_a = data.get("text_a", "").strip()
        text_b = data.get("text_b", "").strip()
        domain_a = data.get("domain_a", "auto")
        domain_b = data.get("domain_b", "auto")
        
        if not text_a or not text_b:
            return {"status": "error", "message": "Both documents required"}
        
        # Basic comparison
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        
        common = len(words_a & words_b)
        total = len(words_a | words_b)
        similarity = (common / total * 100) if total > 0 else 0
        
        comparison = {
            "document_a": {
                "subtype": classify_document(text_a, domain_a),
                "word_count": len(text_a.split())
            },
            "document_b": {
                "subtype": classify_document(text_b, domain_b),
                "word_count": len(text_b.split())
            },
            "similarity_percentage": round(similarity, 2),
            "differences": {
                "only_in_document_a": list(words_a - words_b)[:10],
                "only_in_document_b": list(words_b - words_a)[:10],
                "summary": f"Documents are {round(similarity, 1)}% similar"
            }
        }
        
        return {
            "status": "success",
            "comparison": comparison
        }
    
    except Exception as e:
        logger.error(f"Compare error: {str(e)}")
        return {
            "status": "error",
            "message": f"Comparison failed: {str(e)}"
        }


@app.get("/api/workspace/documents")
async def list_workspace_documents(collection: str = None):
    """List Saved Workspace Documents"""
    try:
        if not workspace_store:
            return {"status": "success", "documents": []}
        
        documents = workspace_store.list_documents(collection)
        return {"status": "success", "documents": documents}
    
    except Exception as e:
        logger.error(f"List error: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/api/workspace/documents/{doc_id}")
async def get_workspace_document(doc_id: str):
    """Get Specific Workspace Document"""
    try:
        if not workspace_store:
            return {"status": "error", "message": "Storage not available"}
        
        doc = workspace_store.get_document(doc_id)
        if not doc:
            return {"status": "error", "message": "Document not found"}
        
        return {"status": "success", "document": doc}
    
    except Exception as e:
        logger.error(f"Get error: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/api/workspace/search")
async def search_workspace(q: str):
    """Search Workspace Documents"""
    try:
        if not workspace_store:
            return {"status": "success", "results": []}
        
        results = workspace_store.search_documents(q)
        return {"status": "success", "results": results}
    
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.delete("/api/workspace/documents/{doc_id}")
async def delete_workspace_document(doc_id: str):
    """Delete Workspace Document"""
    try:
        if not workspace_store:
            return {"status": "error", "message": "Storage not available"}
        
        success = workspace_store.delete_document(doc_id)
        if success:
            return {"status": "success", "message": "Document deleted"}
        return {"status": "error", "message": "Could not delete"}
    
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        return {"status": "error", "message": str(e)}


# ============================================
# HELPER FUNCTIONS FOR WORKSPACE
# ============================================

def classify_document(text: str, domain: str) -> str:
    """Classify document subtype"""
    text_lower = text.lower()
    
    if domain == "medical":
        if "discharge" in text_lower:
            return "Discharge Summary"
        elif "prescription" in text_lower or "rx:" in text_lower:
            return "Prescription"
        elif "lab" in text_lower or "test" in text_lower:
            return "Lab Report"
        return "Medical Document"
    
    elif domain == "legal":
        if "agreement" in text_lower or "contract" in text_lower:
            return "Contract"
        elif "court" in text_lower:
            return "Court Order"
        elif "clause" in text_lower:
            return "Terms"
        return "Legal Document"
    
    return "General Document"


def extract_flags(text: str, domain: str) -> list:
    """Extract red flags"""
    flags = []
    text_lower = text.lower()
    
    if domain == "medical":
        keywords = [
            ("abnormal", "Abnormal result"),
            ("critical", "Critical condition"),
            ("urgent", "Urgent"),
            ("allergy", "Allergy alert"),
        ]
    else:
        keywords = [
            ("penalty", "Penalty clause"),
            ("termination", "Termination"),
            ("breach", "Breach"),
            ("deadline", "Deadline"),
        ]
    
    for kw, flag in keywords:
        if kw in text_lower:
            flags.append(flag)
    
    return flags if flags else ["No flags"]


def extract_actions(text: str, domain: str) -> list:
    """Extract action items"""
    actions = []
    text_lower = text.lower()
    
    if domain == "medical":
        keywords = [
            ("follow-up", "Schedule follow-up"),
            ("refill", "Refill prescription"),
            ("test", "Complete test"),
        ]
    else:
        keywords = [
            ("sign", "Sign document"),
            ("review", "Review document"),
            ("submit", "Submit documents"),
        ]
    
    for kw, action in keywords:
        if kw in text_lower:
            actions.append(action)
    
    return actions if actions else ["No actions"]


def extract_dates(text: str) -> list:
    """Extract dates"""
    import re
    timeline = []
    dates = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
    
    for date in dates[:5]:  # First 5 dates
        timeline.append({"date": date, "event": "Document event"})
    
    return timeline if timeline else []


if __name__ == "__main__":
    main()
