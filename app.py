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
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import ui as ui_logic


app = FastAPI(title="LexScan Web")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
REPORT_CACHE: dict[str, str] = {}


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
    if not (text or "").strip():
        return JSONResponse({"error": "No readable text found in file"}, status_code=400)
    return {"text": text[:10000], "file_type": file_type, "filename": file.filename}


@app.post("/api/document/analyze")
async def document_analyze(payload: dict = Body(...)):
    text = (payload.get("text") or "")
    domain = (payload.get("domain") or "auto")
    language = (payload.get("language") or "English")
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
    _display_text, _status, _summary_html, _table_rows, _result, _highlight_html, _domain_html, _insight_html, report_path = ui_logic.analyze_document(
        None,
        text,
        domain,
        language,
    )
    if not report_path:
        return JSONResponse({"error": "Could not generate report PDF"}, status_code=500)
    return FileResponse(report_path, media_type="application/pdf", filename=Path(report_path).name or "lexscan-report.pdf")


@app.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    report_path = REPORT_CACHE.get(report_id)
    if not report_path or not Path(report_path).exists():
        return JSONResponse({"error": "Report not found"}, status_code=404)
    return FileResponse(report_path, media_type="application/pdf", filename=Path(report_path).name)


@app.post("/api/assistant")
async def assistant(payload: dict = Body(...)):
    context = payload.get("context") or ""
    question = payload.get("question") or ""
    status, answer = ui_logic.ask_assistant(context, question)
    return {"status": status, "answer": answer}


@app.post("/api/batch")
async def batch(payload: dict = Body(...)):
    text_blocks = payload.get("text_blocks") or ""
    domain = payload.get("domain") or "auto"
    status, table_rows, full = ui_logic.batch_analyze(text_blocks, domain)
    return {"status": status, "rows": table_rows, "full": full}


@app.post("/api/multilang/translate")
async def multilang_translate(payload: dict = Body(...)):
    text = payload.get("text") or ""
    language = payload.get("language") or "English"
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


@app.post("/api/multilang/analyze")
async def multilang_analyze(payload: dict = Body(...)):
    source_text = payload.get("source_text") or ""
    translated_text = payload.get("translated_text") or ""
    domain = payload.get("domain") or "auto"
    language = payload.get("language") or "English"
    # Always prioritize translated text when provided, so Analyze uses what user saw in Translate.
    effective_source = ""
    effective_translated = translated_text if translated_text else source_text
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
    _status, _display_text, _summary_html, _badges_html, _result, _insight_html, report_path = ui_logic.analyze_translated_text(
        source_text,
        translated_text,
        domain,
        language,
    )
    if not report_path:
        return JSONResponse({"error": "Could not generate report PDF"}, status_code=500)
    return FileResponse(report_path, media_type="application/pdf", filename=Path(report_path).name or "lexscan-multilang-report.pdf")


def main():
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "7860"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()