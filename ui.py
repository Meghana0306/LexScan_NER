from __future__ import annotations

import html
import json
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import docx
import gradio as gr
import pdfplumber
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

from ai_helper import ask_ai
from src.api.predictor import LEGAL_KEYWORDS, MEDICAL_KEYWORDS, NERPredictor


MEDICAL_EXAMPLE = """Patient presented with acute chest pain, shortness of breath and diaphoresis.
ECG showed ST-elevation myocardial infarction (STEMI). History of Type 2 Diabetes Mellitus and hypertension.
Prescribed Aspirin 325mg, Clopidogrel 75mg, Atorvastatin 40mg and Metformin 500mg twice daily.
Referred to cardiology for urgent coronary angiography."""

LEGAL_EXAMPLE = """In Case No. 2024-CV-04521, Plaintiff TechCorp Inc. filed a lawsuit against
Defendant DataSystems LLC in the Southern District of New York before Judge Patricia Williams.
The complaint alleges violations of Section 12(b) of the Securities Exchange Act of 1934.
The prosecution seeks damages of $2.4 million. Hearing scheduled for March 20, 2025."""

SUPPORTED_LANGUAGES = [
    "English",
    "Hindi",
    "Spanish",
    "French",
    "Arabic",
    "German",
    "Italian",
    "Portuguese",
    "Dutch",
    "Russian",
    "Chinese (Simplified)",
    "Chinese (Traditional)",
    "Japanese",
    "Korean",
    "Turkish",
    "Bengali",
    "Tamil",
    "Telugu",
    "Marathi",
    "Gujarati",
    "Punjabi",
    "Urdu",
    "Malayalam",
    "Kannada",
    "Polish",
]

DEFAULT_OUTPUT_STRINGS = {
    "document_summary": "Document Summary",
    "file": "File",
    "type": "Type",
    "detected_domain": "Detected Domain",
    "entities_found": "Entities Found",
    "processing_time": "Processing Time",
    "generated": "Generated",
    "medical_keyword_hits": "Medical keyword hits",
    "legal_keyword_hits": "Legal keyword hits",
    "domain_reasoning": "Domain Reasoning",
    "overall_domain": "Overall domain",
    "medical_score": "Medical score",
    "legal_score": "Legal score",
    "general_signal": "General signal",
    "matched_keywords": "matched keywords",
    "non_domain_words_scanned": "non-domain words scanned",
    "words_suggesting_medical": "Words suggesting medical",
    "words_suggesting_legal": "Words suggesting legal",
    "other_general_words_seen": "Other general words seen",
    "no_strong_keywords": "No strong keywords",
    "report_title": "NER Analysis Report",
    "domain": "Domain",
    "time": "Time",
    "detected_entities": "Detected Entities",
    "entity_text": "Entity Text",
    "label": "Label",
    "confidence": "Confidence",
    "no_entities_detected": "No entities detected",
    "domain_signals": "Domain Signals",
    "medical_keywords_found": "Medical keywords found",
    "legal_keywords_found": "Legal keywords found",
    "other_general_words_sampled": "Other general words sampled",
    "analyzed_text": "Analyzed Text",
    "ai_insights": "AI Insights",
    "manual_text_input": "Manual text input",
    "text_type": "TEXT",
    "analysis_complete": "Analysis complete.",
    "loaded_from": "Loaded from",
    "could_not_read_file": "Could not read the file",
    "no_highlight_output": "No highlighted output yet.",
    "no_ai_insights_yet": "No AI insights yet.",
    "translated_highlight_note": "Entity highlighting is shown on the analysis language only. Review the translated text and entity table below.",
    "translated_report_note": "This report was localized to the selected output language after analysis.",
    "translated_text": "Translated Text",
}

OUTPUT_STRINGS_CACHE: dict[str, dict[str, str]] = {}
REGISTERED_PDF_FONTS: set[str] = set()

ENTITY_COLORS = {
    "DISEASE": "#ef4444",
    "DRUG": "#fb923c",
    "CHEMICAL": "#f59e0b",
    "SYMPTOM": "#ec4899",
    "PROCEDURE": "#8b5cf6",
    "ANATOMY": "#14b8a6",
    "AGE": "#22c55e",
    "GENDER": "#e879f9",
    "FINDING": "#0ea5e9",
    "PARTY": "#60a5fa",
    "COURT": "#3b82f6",
    "STATUTE": "#06b6d4",
    "DATE": "#4ade80",
    "LAW": "#a78bfa",
    "CASE": "#94a3b8",
    "JUDGE": "#818cf8",
    "LOCATION": "#2dd4bf",
    "PERSON": "#f97316",
    "PER": "#f97316",
    "ORG": "#fbbf24",
    "LOC": "#4ade80",
    "MISC": "#c084fc",
    "PENALTY": "#f43f5e",
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --bg: #07111f;
    --bg-alt: #0b1527;
    --surface: rgba(10, 18, 34, 0.88);
    --surface-strong: #101a2e;
    --line: rgba(148, 163, 184, 0.18);
    --line-strong: rgba(148, 163, 184, 0.3);
    --text: #f2f7ff;
    --text-soft: #d5e3fb;
    --muted: #aabddd;
    --heading: #f8fbff;
    --brand: #7dd3fc;
    --accent: #a78bfa;
    --accent-warm: #f59e0b;
    --success: #34d399;
    --danger: #fb7185;
    --radius-lg: 20px;
    --radius-md: 16px;
    --radius-xl: 28px;
    --shadow-card: 0 16px 36px rgba(15, 23, 42, 0.18);
}

body,
.gradio-container {
    background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.18), transparent 26%),
        radial-gradient(circle at top right, rgba(167, 139, 250, 0.18), transparent 22%),
        linear-gradient(180deg, var(--bg-alt) 0%, var(--bg) 100%) !important;
    color: var(--text) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

.gradio-container {
    max-width: 1280px !important;
    margin: 0 auto !important;
    padding: 24px 20px 52px !important;
}

.gradio-container * {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

#app-shell {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 30px;
    padding: 28px;
    box-shadow: 0 22px 60px rgba(2, 6, 23, 0.2);
    backdrop-filter: blur(14px);
}

#app-header {
    padding: 34px 30px 28px;
    border-radius: var(--radius-xl);
    border: 1px solid var(--line);
    background:
        radial-gradient(circle at top right, rgba(125, 211, 252, 0.14), transparent 32%),
        radial-gradient(circle at bottom left, rgba(167, 139, 250, 0.12), transparent 34%),
        linear-gradient(135deg, rgba(10, 18, 34, 0.92), rgba(17, 28, 49, 0.84));
    box-shadow: var(--shadow-card);
}

#app-brow {
    color: var(--brand);
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    margin-bottom: 12px;
}

#app-title {
    color: var(--heading);
    font-size: 46px;
    font-weight: 800;
    letter-spacing: -0.04em;
    margin-bottom: 10px;
    line-height: 1.05;
}

#app-subtitle {
    color: var(--text-soft);
    font-size: 15px;
    line-height: 1.75;
    max-width: 760px;
}

#status-bar,
#dashboard-stats {
    display: grid;
    gap: 14px;
}

#status-bar {
    grid-template-columns: repeat(5, minmax(0, 1fr));
    margin-top: 22px;
}

#dashboard-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 24px 0 18px;
}

.status-pill,
.stat-card,
#entity-legend,
.about-card {
    border: 1px solid var(--line);
    box-shadow: var(--shadow-card);
}

.status-pill {
    background: rgba(255, 255, 255, 0.04);
    color: var(--text);
    border-radius: 999px;
    padding: 10px 14px;
    text-align: center;
    font-size: 12px;
    font-weight: 700;
}

.stat-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
    border-radius: var(--radius-lg);
    padding: 22px;
}

.stat-kicker {
    color: var(--muted);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}

.stat-value {
    color: var(--heading);
    font-size: 34px;
    font-weight: 800;
    margin-top: 12px;
}

.stat-note {
    color: var(--text-soft);
    font-size: 13px;
    line-height: 1.65;
    margin-top: 8px;
}

.legend-title {
    color: var(--muted);
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.16em;
    margin-right: 8px;
}

#entity-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 18px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.03);
}

.legend-chip {
    display: inline-flex;
    align-items: center;
    padding: 8px 12px;
    border-radius: 999px;
    border: 1px solid var(--line);
    font-size: 12px;
    font-weight: 700;
}

.tabs {
    border: 1px solid var(--line);
    border-radius: var(--radius-xl);
    background: rgba(9, 16, 30, 0.62);
    box-shadow: var(--shadow-card);
    padding: 14px 14px 18px;
}

.tab-nav {
    gap: 10px !important;
    padding: 0 8px 12px !important;
    border-bottom: 1px solid var(--line) !important;
}

.tab-nav button {
    border: 1px solid transparent !important;
    border-radius: 999px !important;
    background: transparent !important;
    color: var(--text-soft) !important;
    font-weight: 700 !important;
    padding: 10px 14px !important;
}

.tab-nav button.selected {
    color: var(--heading) !important;
    background: linear-gradient(135deg, rgba(125,211,252,0.18), rgba(167,139,250,0.14)) !important;
    border-color: rgba(125,211,252,0.35) !important;
    box-shadow: 0 0 0 1px rgba(125,211,252,0.08) inset;
}

.tabitem {
    border: none !important;
    border-radius: 20px !important;
    background: transparent !important;
    padding: 18px 8px 6px !important;
}

.block,
.gr-box,
.gr-panel {
    border-radius: 18px !important;
}

.gr-button-primary {
    background: linear-gradient(135deg, var(--brand), var(--accent)) !important;
    color: #05111d !important;
    border: none !important;
    box-shadow: 0 12px 24px rgba(125, 211, 252, 0.18) !important;
}

.gr-button-secondary {
    background: rgba(255,255,255,0.04) !important;
    color: var(--text) !important;
    border: 1px solid var(--line-strong) !important;
}

.section-copy {
    color: var(--text-soft);
    font-size: 14px;
    line-height: 1.75;
}

.section-hero {
    border: 1px solid var(--line);
    border-radius: var(--radius-xl);
    padding: 22px 22px 18px;
    background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 28%),
        linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015));
    margin-bottom: 18px;
}

.section-hero h3 {
    margin: 0 0 10px 0;
    color: var(--heading);
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.03em;
}

.section-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    margin-top: 18px;
}

.feature-box {
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 16px;
    background: rgba(255,255,255,0.03);
}

.feature-kicker {
    color: var(--muted);
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 8px;
}

.feature-title {
    color: var(--heading);
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 6px;
}

.feature-note {
    color: var(--text-soft);
    font-size: 13px;
    line-height: 1.6;
}

.panel-card {
    border: 1px solid var(--line);
    border-radius: var(--radius-xl);
    padding: 18px;
    background: linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.015));
    box-shadow: var(--shadow-card);
}

.panel-title {
    color: var(--heading);
    font-size: 18px;
    font-weight: 800;
    margin-bottom: 6px;
}

.panel-copy {
    color: var(--text-soft);
    font-size: 13px;
    line-height: 1.65;
    margin-bottom: 14px;
}

.report-shell {
    display: grid;
    gap: 14px;
}

.highlight-box {
    min-height: 150px;
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    line-height: 1.9;
    color: var(--text);
    white-space: pre-wrap;
}

.entity-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.entity-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    padding: 8px 12px;
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.03);
    font-size: 12px;
    font-weight: 700;
}

.note-box {
    background: rgba(245,158,11,0.1);
    border: 1px solid rgba(245,158,11,0.28);
    color: var(--text-soft);
    border-radius: 16px;
    padding: 12px 16px;
}

.report-summary {
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    margin-bottom: 14px;
}

.report-summary h4 {
    margin: 0 0 10px 0;
    color: var(--heading);
    font-size: 16px;
}

.report-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 16px;
}

.report-item {
    color: var(--text-soft);
    font-size: 13px;
    line-height: 1.6;
}

.report-item strong {
    color: var(--heading);
}

.insight-box {
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    color: var(--text-soft);
    line-height: 1.8;
    white-space: pre-wrap;
}

.domain-panel {
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    margin-bottom: 14px;
}

.domain-panel h4 {
    margin: 0 0 10px 0;
    color: var(--heading);
    font-size: 16px;
}

.domain-explain {
    color: var(--text-soft);
    font-size: 13px;
    line-height: 1.75;
    margin-bottom: 12px;
}

.domain-scores {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 12px;
}

.domain-score {
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.02);
}

.domain-score strong {
    display: block;
    color: var(--heading);
    font-size: 13px;
    margin-bottom: 4px;
}

.domain-score span {
    color: var(--text-soft);
    font-size: 12px;
}

.keyword-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.keyword-chip {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 7px 11px;
    font-size: 12px;
    font-weight: 700;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.03);
    color: var(--text);
}

.gradio-container textarea,
.gradio-container input,
.gradio-container select,
.gradio-container .wrap,
.gradio-container .block {
    background-color: rgba(255,255,255,0.03) !important;
}

.gradio-container textarea,
.gradio-container input {
    color: var(--text) !important;
}

.gradio-container label {
    color: var(--text-soft) !important;
    font-weight: 700 !important;
}

.gr-dataframe {
    border-radius: 18px !important;
    overflow: hidden !important;
}

.gr-dataframe table thead th {
    background: rgba(255,255,255,0.04) !important;
    color: var(--heading) !important;
}

@media (max-width: 1024px) {
    #status-bar,
    #dashboard-stats {
        grid-template-columns: 1fr;
    }

    .domain-scores {
        grid-template-columns: 1fr;
    }

    .section-grid {
        grid-template-columns: 1fr;
    }

    #app-title {
        font-size: 34px;
    }
}
"""

_PREDICTOR: NERPredictor | None = None


def get_header_html() -> str:
    return """
    <div id='app-shell'>
        <div id='app-header'>
            <div id='app-brow'>AI Entity Intelligence</div>
            <div id='app-title'>Multi-Domain Entity Extraction for Legal and Medical Documents using NER</div>
            <div id='app-subtitle'>Three domain-aware pipelines work together across medical, legal, and general text. Upload a document, inspect why the system chose a domain, review named entities in context, and export a polished analysis report.</div>
            <div id='status-bar'>
                <div class='status-pill'><strong>BioBERT</strong><br>Medical extraction</div>
                <div class='status-pill'><strong>LegalBERT</strong><br>Legal entities</div>
                <div class='status-pill'><strong>DistilBERT</strong><br>General fallback</div>
                <div class='status-pill'><strong>AI Assistant</strong><br>Guided analysis</div>
                <div class='status-pill'><strong>20+</strong><br>Languages supported</div>
            </div>
        </div>
        <div id='dashboard-stats'>
            <div class='stat-card'>
                <div class='stat-kicker'>Models</div>
                <div class='stat-value'>3</div>
                <div class='stat-note'>Dedicated pipelines for legal, medical, and general NER scenarios.</div>
            </div>
            <div class='stat-card'>
                <div class='stat-kicker'>Average F1 Score</div>
                <div class='stat-value'>91%</div>
                <div class='stat-note'>Strong extraction quality tuned for high-signal documents and review workflows.</div>
            </div>
            <div class='stat-card'>
                <div class='stat-kicker'>Languages</div>
                <div class='stat-value'>20+</div>
                <div class='stat-note'>Analyze and translate cross-language content without leaving the Python app.</div>
            </div>
        </div>
    </div>
    """


def get_document_intro_html() -> str:
    return """
    <div class='section-hero'>
        <h3>Single document review</h3>
        <div class='section-copy'>
            Upload a PDF, DOCX, or TXT file, or paste raw text directly. The dashboard keeps the source content visible,
            identifies the most likely domain, explains the domain decision, highlights named entities in context,
            and prepares a downloadable NER analysis report.
        </div>
        <div class='section-grid'>
            <div class='feature-box'>
                <div class='feature-kicker'>Supported Input</div>
                <div class='feature-title'>PDF, DOCX, TXT</div>
                <div class='feature-note'>Works with medical reports, legal documents, contracts, notes, and plain text.</div>
            </div>
            <div class='feature-box'>
                <div class='feature-kicker'>Domain Reasoning</div>
                <div class='feature-title'>Medical · Legal · General</div>
                <div class='feature-note'>Shows the overall domain and the specific keywords that pushed the document toward that class.</div>
            </div>
            <div class='feature-box'>
                <div class='feature-kicker'>Client Report</div>
                <div class='feature-title'>Download Analysis PDF</div>
                <div class='feature-note'>Exports entities, analyzed content, domain signals, and AI insights in a polished report layout.</div>
            </div>
        </div>
    </div>
    """


def get_legend_html(entity_colors: dict[str, str]) -> str:
    html_parts = ["<div id='entity-legend'><span class='legend-title'>ENTITY TYPES</span>"]
    for label, color in list(entity_colors.items())[:12]:
        html_parts.append(
            f"<span class='legend-chip' style='color:{color};border-color:{color}55;background:{color}14'>{label}</span>"
        )
    html_parts.append("</div>")
    return "".join(html_parts)


def get_about_html() -> str:
    return """
    <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:24px'>
        <div class='about-card' style='background:var(--surface-strong);border-radius:24px;padding:24px;text-align:center;'>
            <div style='font-size:36px;font-weight:800;color:var(--brand);font-family:IBM Plex Mono, monospace'>3</div>
            <div style='color:var(--muted);font-size:12px;margin-top:8px;text-transform:uppercase;letter-spacing:0.12em'>BERT models trained</div>
        </div>
        <div class='about-card' style='background:var(--surface-strong);border-radius:24px;padding:24px;text-align:center;'>
            <div style='font-size:36px;font-weight:800;color:var(--accent);font-family:IBM Plex Mono, monospace'>91%</div>
            <div style='color:var(--muted);font-size:12px;margin-top:8px;text-transform:uppercase;letter-spacing:0.12em'>Average F1 score</div>
        </div>
        <div class='about-card' style='background:var(--surface-strong);border-radius:24px;padding:24px;text-align:center;'>
            <div style='font-size:36px;font-weight:800;color:var(--accent-warm);font-family:IBM Plex Mono, monospace'>20+</div>
            <div style='color:var(--muted);font-size:12px;margin-top:8px;text-transform:uppercase;letter-spacing:0.12em'>Languages supported</div>
        </div>
    </div>
    <div class='section-copy'>This version removes the separate frontend folder and keeps the interactive dashboard directly inside <code>ui.py</code>, so you only need to maintain one Python UI surface.</div>
    """


def get_disclaimer_html() -> str:
    return """
    <div class='note-box'>
        <strong style='color:var(--accent-warm)'>Note</strong>
        AI responses are for informational purposes only. Always consult qualified medical or legal professionals.
    </div>
    """


def get_predictor() -> NERPredictor:
    global _PREDICTOR
    if _PREDICTOR is None:
        predictor = NERPredictor()
        predictor.load_all_models()
        _PREDICTOR = predictor
    return _PREDICTOR


def extract_text_from_path(file_path: str | None) -> tuple[str, str]:
    if not file_path:
        return "", ""

    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".txt":
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return path.read_text(encoding=encoding), "txt"
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode TXT file")

    if suffix == ".pdf":
        parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(text)
        return "\n\n".join(parts).strip(), "pdf"

    if suffix == ".docx":
        document = docx.Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs).strip(), "docx"

    raise ValueError("Unsupported file type. Use PDF, DOCX, or TXT.")


def normalize_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in entities:
        normalized.append(
            {
                "text": item.get("text", ""),
                "label": item.get("label", ""),
                "start": int(item.get("start", 0)),
                "end": int(item.get("end", 0)),
                "confidence": float(item.get("confidence", 0.0)),
            }
        )
    return normalized


def render_highlighted_text(text: str, entities: list[dict[str, Any]]) -> str:
    if not text:
        return "<div class='highlight-box'>No highlighted output yet.</div>"

    items = sorted(normalize_entities(entities), key=lambda item: item["start"])
    cursor = 0
    html_parts: list[str] = []
    for entity in items:
        start = entity["start"]
        end = entity["end"]
        if start < cursor or end <= start:
            continue
        color = ENTITY_COLORS.get(entity["label"].upper(), "#60a5fa")
        html_parts.append(html.escape(text[cursor:start]))
        html_parts.append(
            f"<span style='background:{color}22;border:1px solid {color}55;border-radius:10px;padding:2px 6px'>"
            f"{html.escape(text[start:end])}</span>"
        )
        cursor = end
    html_parts.append(html.escape(text[cursor:]))
    return f"<div class='highlight-box'>{''.join(html_parts)}</div>"


def clean_ai_json(text: str) -> str:
    value = (text or "").strip()
    value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*```$", "", value)
    return value.strip()


def is_ai_error(text: str) -> bool:
    value = (text or "").strip()
    lowered = value.lower()
    if (
        not value
        or value.startswith("Error:")
        or value.startswith("Groq Error:")
        or value.startswith("Unexpected:")
        or "add groq_api_key" in lowered
    ):
        return True
    return text.startswith("âŒ") or text.startswith("Error:") or text.startswith("Groq Error:")


def translate_plain_text(text: str, target_language: str, *, preserve_line_breaks: bool = True) -> str:
    clean_text = (text or "").strip()
    if not clean_text or target_language == "English":
        return clean_text

    line_break_rule = "Preserve paragraph breaks and line breaks." if preserve_line_breaks else ""
    translated = ask_ai(
        messages=[
            {
                "role": "user",
                "content": (
                    f"Translate the following text to {target_language}.\n"
                    f"{line_break_rule}\n"
                    "Return only the translated text.\n\n"
                    f"{clean_text}"
                ),
            }
        ],
        system_prompt=(
            "You are a precise translator for legal, medical, and general documents. "
            "Keep the meaning accurate and natural."
        ),
    )
    return clean_text if is_ai_error(translated) else translated.strip()


def translate_text_for_analysis(text: str) -> str:
    clean_text = (text or "").strip()
    if not clean_text:
        return clean_text

    translated = ask_ai(
        messages=[
            {
                "role": "user",
                "content": (
                    "Convert the following document text into English for downstream NER analysis. "
                    "If it is already English, return it unchanged. Preserve the meaning and paragraph structure. "
                    "Return only the English text.\n\n"
                    f"{clean_text}"
                ),
            }
        ],
        system_prompt=(
            "You are a precise document translator preparing text for named entity extraction. "
            "Do not summarize or explain."
        ),
    )
    return clean_text if is_ai_error(translated) else translated.strip()


def get_output_strings(target_language: str) -> dict[str, str]:
    if target_language == "English":
        return DEFAULT_OUTPUT_STRINGS

    cached = OUTPUT_STRINGS_CACHE.get(target_language)
    if cached:
        return cached

    payload = json.dumps(DEFAULT_OUTPUT_STRINGS, ensure_ascii=False)
    translated = ask_ai(
        messages=[
            {
                "role": "user",
                "content": (
                    f"Translate every JSON value into {target_language}. "
                    "Keep every key exactly the same. Return JSON only.\n\n"
                    f"{payload}"
                ),
            }
        ],
        system_prompt=(
            "You localize application output for multilingual document analysis. "
            "Return valid JSON only."
        ),
    )
    if is_ai_error(translated):
        return DEFAULT_OUTPUT_STRINGS

    try:
        parsed = json.loads(clean_ai_json(translated))
    except json.JSONDecodeError:
        return DEFAULT_OUTPUT_STRINGS

    localized = DEFAULT_OUTPUT_STRINGS.copy()
    for key, value in parsed.items():
        if key in localized and isinstance(value, str) and value.strip():
            localized[key] = value.strip()
    OUTPUT_STRINGS_CACHE[target_language] = localized
    return localized


def localize_domain_name(domain: str, target_language: str) -> str:
    mapping = {
        "medical": "medical",
        "legal": "legal",
        "general": "general",
        "unknown": "unknown",
    }
    term = mapping.get((domain or "").lower(), domain or "unknown")
    translated = translate_plain_text(term, target_language, preserve_line_breaks=False)
    return translated or term


def localize_domain_info(domain_info: dict[str, Any], target_language: str) -> dict[str, Any]:
    if not domain_info or target_language == "English":
        return domain_info

    localized = dict(domain_info)
    localized["predicted_domain_display"] = localize_domain_name(
        str(domain_info.get("predicted_domain", "unknown")),
        target_language,
    )
    localized["explanation"] = translate_plain_text(str(domain_info.get("explanation", "")), target_language)
    return localized


def get_pdf_font_config(target_language: str) -> tuple[str, str]:
    font_name = "ArialUnicodeFallback"
    font_path = r"C:\Windows\Fonts\arial.ttf"

    if target_language in {"Hindi", "Bengali", "Tamil", "Telugu", "Marathi", "Gujarati", "Punjabi", "Malayalam", "Kannada"}:
        font_name = "NirmalaUI"
        font_path = r"C:\Windows\Fonts\Nirmala.ttc"
    elif target_language in {"Chinese (Simplified)", "Chinese (Traditional)"}:
        font_name = "STSong-Light"
        if font_name not in REGISTERED_PDF_FONTS:
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))
            REGISTERED_PDF_FONTS.add(font_name)
        return font_name, font_name
    elif target_language == "Japanese":
        font_name = "HeiseiMin-W3"
        if font_name not in REGISTERED_PDF_FONTS:
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))
            REGISTERED_PDF_FONTS.add(font_name)
        return font_name, font_name
    elif target_language == "Korean":
        font_name = "HYSMyeongJo-Medium"
        if font_name not in REGISTERED_PDF_FONTS:
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))
            REGISTERED_PDF_FONTS.add(font_name)
        return font_name, font_name
    elif target_language in {"Arabic", "Urdu"}:
        font_name = "SegoeUI"
        font_path = r"C:\Windows\Fonts\segoeui.ttf"

    if font_name not in REGISTERED_PDF_FONTS:
        pdfmetrics.registerFont(TTFont(font_name, font_path))
        REGISTERED_PDF_FONTS.add(font_name)
    return font_name, font_name


def render_entity_badges(entities: list[dict[str, Any]]) -> str:
    if not entities:
        return "<div class='entity-badges'><span class='entity-badge'>No entities detected</span></div>"

    parts = ["<div class='entity-badges'>"]
    for entity in normalize_entities(entities)[:12]:
        color = ENTITY_COLORS.get(entity["label"].upper(), "#60a5fa")
        parts.append(
            f"<span class='entity-badge' style='border-color:{color}66;color:{color}'>"
            f"{html.escape(entity['label'])}: {html.escape(entity['text'])}</span>"
        )
    parts.append("</div>")
    return "".join(parts)


def entities_to_table(entities: list[dict[str, Any]]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for entity in normalize_entities(entities):
        rows.append(
            [
                entity["text"],
                entity["label"],
                entity["start"],
                entity["end"],
                round(entity["confidence"], 4),
            ]
        )
    return rows


def get_domain_evidence(text: str, predicted_domain: str) -> dict[str, Any]:
    words = re.findall(r"[a-zA-Z]+", (text or "").lower())
    unique_words = set(words)

    medical_matches = sorted(unique_words & MEDICAL_KEYWORDS)
    legal_matches = sorted(unique_words & LEGAL_KEYWORDS)

    medical_score = len(medical_matches)
    legal_score = len(legal_matches)
    general_score = max(len(unique_words) - medical_score - legal_score, 0)

    if predicted_domain == "medical":
        explanation = (
            "This document leans medical because it contains health, diagnosis, treatment, or symptom-related wording."
        )
    elif predicted_domain == "legal":
        explanation = (
            "This document leans legal because it contains court, case, law, contract, or party-related wording."
        )
    else:
        explanation = (
            "This document was treated as general because strong medical or legal keyword evidence was limited or mixed."
        )

    return {
        "predicted_domain": predicted_domain,
        "medical_score": medical_score,
        "legal_score": legal_score,
        "general_score": general_score,
        "medical_matches": medical_matches[:12],
        "legal_matches": legal_matches[:12],
        "general_matches": sorted(unique_words - set(medical_matches) - set(legal_matches))[:12],
        "explanation": explanation,
    }


def render_domain_panel(domain_info: dict[str, Any], strings: dict[str, str] | None = None) -> str:
    if not domain_info:
        return ""
    strings = strings or DEFAULT_OUTPUT_STRINGS

    def chips(values: list[str], color: str) -> str:
        if not values:
            return f"<span class='keyword-chip'>{html.escape(strings['no_strong_keywords'])}</span>"
        return "".join(
            f"<span class='keyword-chip' style='border-color:{color}55;color:{color};background:{color}14'>{html.escape(value)}</span>"
            for value in values
        )

    return f"""
    <div class='domain-panel'>
        <h4>{html.escape(strings['domain_reasoning'])}</h4>
        <div class='domain-explain'>
            <strong>{html.escape(strings['overall_domain'])}:</strong> {html.escape(str(domain_info.get('predicted_domain_display', domain_info.get('predicted_domain', 'unknown'))))}<br/>
            {html.escape(domain_info.get('explanation', ''))}
        </div>
        <div class='domain-scores'>
            <div class='domain-score'>
                <strong>{html.escape(strings['medical_score'])}</strong>
                <span>{domain_info.get('medical_score', 0)} {html.escape(strings['matched_keywords'])}</span>
            </div>
            <div class='domain-score'>
                <strong>{html.escape(strings['legal_score'])}</strong>
                <span>{domain_info.get('legal_score', 0)} {html.escape(strings['matched_keywords'])}</span>
            </div>
            <div class='domain-score'>
                <strong>{html.escape(strings['general_signal'])}</strong>
                <span>{domain_info.get('general_score', 0)} {html.escape(strings['non_domain_words_scanned'])}</span>
            </div>
        </div>
        <div class='report-item' style='margin-bottom:8px;'><strong>{html.escape(strings['words_suggesting_medical'])}:</strong></div>
        <div class='keyword-list' style='margin-bottom:12px;'>{chips(domain_info.get('medical_matches', []), '#14b8a6')}</div>
        <div class='report-item' style='margin-bottom:8px;'><strong>{html.escape(strings['words_suggesting_legal'])}:</strong></div>
        <div class='keyword-list' style='margin-bottom:12px;'>{chips(domain_info.get('legal_matches', []), '#f59e0b')}</div>
        <div class='report-item' style='margin-bottom:8px;'><strong>{html.escape(strings['other_general_words_seen'])}:</strong></div>
        <div class='keyword-list'>{chips(domain_info.get('general_matches', []), '#60a5fa')}</div>
    </div>
    """


def build_ai_insight(result: dict[str, Any], target_language: str) -> str:
    entities = normalize_entities(result.get("entities", []))
    if not entities:
        fallback = (
            "No named entities were detected in this document. Review the source content and "
            "consider providing a longer or more domain-specific document for better extraction."
        )
        return translate_plain_text(fallback, target_language)

    entity_list = ", ".join(f"{entity['text']} ({entity['label']})" for entity in entities[:12])
    prompt = (
        f"Document domain: {result.get('domain', 'unknown')}\n"
        f"Detected entities: {entity_list}\n\n"
        f"Document text:\n{result.get('text', '')[:3000]}\n\n"
        "Provide a concise analysis report insight in one paragraph. "
        "If the document is medical, mention likely issues and suggest professional follow-up. "
        "If legal, mention key parties, places, dates, and suggested legal review focus. "
        "Do not claim certainty. End with a short safety disclaimer. "
        f"Write the full response in {target_language}."
    )
    insight = ask_ai(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=(
            "You are an expert review assistant for named entity extraction across legal and medical documents. "
            "Write clear, professional, client-facing report insights."
        ),
    )
    if insight.startswith("❌") or insight.startswith("Error:") or insight.startswith("Groq Error:"):
        labels = sorted({entity["label"] for entity in entities})
        return (
            f"The document was classified as {result.get('domain', 'unknown')} and contains "
            f"{result.get('entity_count', 0)} extracted entities across labels: {', '.join(labels)}. "
            "Review the highlighted spans and structured table below for the most important detected names, "
            "clinical terms, or legal references. Please consult a qualified professional before taking action."
        )
    return insight


def render_report_summary(
    file_name: str,
    file_type: str,
    result: dict[str, Any],
    strings: dict[str, str],
) -> str:
    domain_info = result.get("domain_analysis", {})
    return f"""
    <div class='report-summary'>
        <h4>{html.escape(strings['document_summary'])}</h4>
        <div class='report-grid'>
            <div class='report-item'><strong>{html.escape(strings['file'])}:</strong> {html.escape(file_name or strings['manual_text_input'])}</div>
            <div class='report-item'><strong>{html.escape(strings['type'])}:</strong> {html.escape(file_type.upper() if file_type else strings['text_type'])}</div>
            <div class='report-item'><strong>{html.escape(strings['detected_domain'])}:</strong> {html.escape(str(result.get('domain_display', result.get('domain', 'unknown'))))}</div>
            <div class='report-item'><strong>{html.escape(strings['entities_found'])}:</strong> {html.escape(str(result.get('entity_count', 0)))}</div>
            <div class='report-item'><strong>{html.escape(strings['processing_time'])}:</strong> {html.escape(str(result.get('processing_time_seconds', 0)))}s</div>
            <div class='report-item'><strong>{html.escape(strings['generated'])}:</strong> {html.escape(datetime.now().strftime('%Y-%m-%d %H:%M'))}</div>
            <div class='report-item'><strong>{html.escape(strings['medical_keyword_hits'])}:</strong> {html.escape(str(domain_info.get('medical_score', 0)))}</div>
            <div class='report-item'><strong>{html.escape(strings['legal_keyword_hits'])}:</strong> {html.escape(str(domain_info.get('legal_score', 0)))}</div>
        </div>
    </div>
    """


def save_report(
    result: dict[str, Any] | None,
    file_name: str,
    file_type: str,
    ai_insight: str,
    target_language: str,
    strings: dict[str, str],
) -> str | None:
    if not result:
        return None

    temp_dir = Path(tempfile.gettempdir())
    report_name = f"{Path(file_name).stem if file_name else 'ner-analysis'}-report.pdf"
    path = temp_dir / report_name

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    regular_font, bold_font = get_pdf_font_config(target_language)
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=bold_font,
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=10,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=10,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
        leading=14,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName=bold_font,
        fontSize=13,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=8,
        spaceBefore=10,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName=regular_font,
        fontSize=10,
        textColor=colors.HexColor("#1e293b"),
        leading=14,
        spaceAfter=8,
    )
    text_block_style = ParagraphStyle(
        "TextBlock",
        parent=styles["Code"],
        fontName=regular_font,
        fontSize=9,
        textColor=colors.HexColor("#1e293b"),
        leading=13,
        spaceAfter=8,
    )
    if target_language in {"Chinese (Simplified)", "Chinese (Traditional)", "Japanese", "Korean"}:
        body_style.wordWrap = "CJK"
        text_block_style.wordWrap = "CJK"

    story: list[Any] = []
    story.append(Paragraph(strings["report_title"], title_style))
    story.append(Paragraph(f"{strings['generated']}: {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style))
    story.append(
        Paragraph(
            f"{strings['domain']}: {str(result.get('domain_display', result.get('domain', 'unknown')))} | "
            f"{strings['entities_found']}: {result.get('entity_count', 0)} | "
            f"{strings['time']}: {result.get('processing_time_seconds', 0)}s | "
            f"{strings['file']}: {file_name or strings['manual_text_input']}",
            meta_style,
        )
    )

    domain_info = result.get("domain_analysis", {})
    story.append(
        Paragraph(
            f"{strings['domain_reasoning']}: "
            f"{strings['medical_keyword_hits']}={domain_info.get('medical_score', 0)}, "
            f"{strings['legal_keyword_hits']}={domain_info.get('legal_score', 0)}, "
            f"{strings['detected_domain']}={str(result.get('domain_display', result.get('domain', 'unknown')))}",
            meta_style,
        )
    )

    story.append(Paragraph(strings["detected_entities"], section_style))
    entities = normalize_entities(result.get("entities", []))
    table_rows = [[strings["entity_text"], strings["label"], strings["confidence"]]]
    if entities:
        for entity in entities:
            table_rows.append([entity["text"], entity["label"], f"{entity['confidence'] * 100:.1f}%"])
    else:
        table_rows.append([strings["no_entities_detected"], "-", "-"])

    entity_table = Table(table_rows, colWidths=[3.6 * inch, 1.1 * inch, 1.0 * inch])
    entity_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTNAME", (0, 1), (-1, -1), regular_font),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(entity_table)

    story.append(Paragraph(strings["domain_signals"], section_style))
    medical_terms = ", ".join(domain_info.get("medical_matches", [])) or strings["no_strong_keywords"]
    legal_terms = ", ".join(domain_info.get("legal_matches", [])) or strings["no_strong_keywords"]
    general_terms = ", ".join(domain_info.get("general_matches", [])) or strings["no_strong_keywords"]
    story.append(Paragraph(f"{strings['medical_keywords_found']}: {html.escape(medical_terms)}", body_style))
    story.append(Paragraph(f"{strings['legal_keywords_found']}: {html.escape(legal_terms)}", body_style))
    story.append(Paragraph(f"{strings['other_general_words_sampled']}: {html.escape(general_terms)}", body_style))

    story.append(Paragraph(strings["translated_text"], section_style))
    story.append(
        Preformatted(
            result.get("display_text", result.get("text", "")) or strings["no_entities_detected"],
            text_block_style,
        )
    )
    story.append(Paragraph(strings["analyzed_text"], section_style))
    story.append(
        Preformatted(
            result.get("display_text", result.get("text", "")) or strings["no_entities_detected"],
            text_block_style,
        )
    )
    if target_language != "English":
        story.append(Paragraph(strings["translated_report_note"], body_style))

    story.append(Paragraph(strings["ai_insights"], section_style))
    story.append(Paragraph(html.escape(ai_insight).replace("\n", "<br/>"), body_style))

    doc.build(story)
    return str(path)


def analyze_text(text: str, domain: str) -> dict[str, Any]:
    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("Please provide some text to analyze.")

    predictor = get_predictor()
    active_domain = domain
    if active_domain == "auto":
        active_domain = predictor.detect_domain(clean_text)

    start_time = time.time()
    entities = predictor.predict(clean_text, active_domain)
    elapsed = round(time.time() - start_time, 3)
    domain_info = get_domain_evidence(clean_text, active_domain)

    return {
        "text": clean_text,
        "domain": active_domain,
        "domain_analysis": domain_info,
        "entities": entities,
        "entity_count": len(entities),
        "processing_time_seconds": elapsed,
    }


def use_uploaded_file(file_path: str | None, current_text: str) -> tuple[str, str]:
    if not file_path:
        return current_text, "No file selected."

    text, file_type = extract_text_from_path(file_path)
    if not text.strip():
        return current_text, f"No readable text found in the {file_type.upper()} file."

    return text[:10000], f"Loaded {Path(file_path).name} ({file_type.upper()}) into the editor."


def analyze_document(
    file_path: str | None, text: str, domain: str, target_language: str
) -> tuple[str, str, str, list[list[Any]], dict[str, Any], str, str, str, str]:
    strings = get_output_strings(target_language)
    file_name = ""
    file_type = ""
    if file_path:
        try:
            file_text, file_type = extract_text_from_path(file_path)
            if file_text.strip():
                text = file_text[:10000]
            file_name = Path(file_path).name
            source_note = f"{strings['loaded_from']} {file_name} ({file_type.upper()}). "
        except Exception as exc:
            return (
                text,
                f"{strings['could_not_read_file']}: {exc}",
                "",
                [],
                {},
                f"<div class='highlight-box'>{html.escape(strings['no_highlight_output'])}</div>",
                "",
                f"<div class='insight-box'>{html.escape(strings['no_ai_insights_yet'])}</div>",
                "",
            )
    else:
        source_note = ""
        file_name = "manual_input.txt"
        file_type = "txt"

    source_text = (text or "").strip()
    analysis_text = translate_text_for_analysis(source_text)

    try:
        result = analyze_text(analysis_text, domain)
    except Exception as exc:
        return (
            source_text,
            str(exc),
            "",
            [],
            {},
            f"<div class='highlight-box'>{html.escape(strings['no_highlight_output'])}</div>",
            "",
            f"<div class='insight-box'>{html.escape(strings['no_ai_insights_yet'])}</div>",
            "",
        )

    localized_text = translate_plain_text(source_text or result["text"], target_language)
    result["source_text"] = source_text
    result["display_text"] = localized_text or source_text or result["text"]
    result["output_language"] = target_language
    result["domain_display"] = localize_domain_name(result.get("domain", "unknown"), target_language)
    result["domain_analysis"] = localize_domain_info(result.get("domain_analysis", {}), target_language)

    ai_insight = build_ai_insight(result, target_language)
    status = (
        f"{source_note}{strings['analysis_complete']} {strings['entities_found']}: {result['entity_count']} | "
        f"{strings['detected_domain']}: {result['domain_display']} | "
        f"{strings['processing_time']}: {result['processing_time_seconds']}s."
    )
    translated_highlight = (
        f"<div class='highlight-box'>{html.escape(result['display_text']).replace(chr(10), '<br/>')}</div>"
        f"<div class='section-copy' style='margin-top:10px;'>{html.escape(strings['translated_highlight_note'])}</div>"
        if target_language != "English"
        else render_highlighted_text(result["text"], result["entities"])
    )
    return (
        result["display_text"],
        status,
        render_report_summary(file_name, file_type, result, strings),
        entities_to_table(result["entities"]),
        result,
        translated_highlight,
        render_domain_panel(result.get("domain_analysis", {}), strings),
        f"<div class='insight-box'>{html.escape(ai_insight)}</div>",
        save_report(result, file_name, file_type, ai_insight, target_language, strings) or "",
    )


def ask_assistant(context: str, question: str) -> tuple[str, str]:
    clean_question = (question or "").strip()
    if not clean_question:
        return "Please enter a question for the assistant.", "No answer yet."

    clean_context = (context or "").strip() or "No context provided."
    answer = ask_ai(
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{clean_context}\n\nQuestion:\n{clean_question}",
            }
        ],
        system_prompt=(
            "You are a helpful assistant for legal and medical named entity extraction. "
            "Answer clearly, use the provided context, and call out important entities and risks when relevant."
        ),
    )
    return "Assistant response ready.", answer


def batch_analyze(text_blocks: str, domain: str) -> tuple[str, list[list[Any]], dict[str, Any]]:
    chunks = [chunk.strip() for chunk in (text_blocks or "").split("\n\n") if chunk.strip()]
    if not chunks:
        return "Please add at least one document block.", [], {}

    results: list[dict[str, Any]] = []
    started = time.time()
    for text in chunks[:50]:
        try:
            result = analyze_text(text, domain)
            results.append(result)
        except Exception as exc:
            results.append(
                {
                    "text": text,
                    "domain": domain,
                    "entities": [],
                    "entity_count": 0,
                    "error": str(exc),
                }
            )

    table_rows: list[list[Any]] = []
    for index, result in enumerate(results, start=1):
        preview = (result.get("text", "") or "")[:110]
        table_rows.append([index, result.get("domain", "unknown"), result.get("entity_count", 0), preview])

    payload = {
        "results": results,
        "total_texts": len(results),
        "processing_time_seconds": round(time.time() - started, 3),
    }
    status = f"Batch analysis complete for {len(results)} document(s)."
    return status, table_rows, payload


def translate_text(text: str, target_language: str) -> tuple[str, str]:
    clean_text = (text or "").strip()
    if not clean_text:
        return "Please enter source text first.", ""

    if target_language == "English":
        return "Translation complete. Text translated to English.", clean_text

    translated = ask_ai(
        messages=[
            {
                "role": "user",
                "content": f"Translate the following text to {target_language}:\n\n{clean_text}",
            }
        ],
        system_prompt=(
            f"You are a precise translator. Translate the text to {target_language}. "
            "Return only the translated text and nothing else."
        ),
    )
    if is_ai_error(translated):
        return (
            "Translation could not be completed. The AI translation service did not return usable text. "
            "Please check the API key, quota, or network connection.",
            "",
        )
    return f"Translation complete. Text translated to {target_language}.", translated.strip()


def analyze_translated_text(
    source_text: str,
    translated_text: str,
    domain: str,
    target_language: str,
) -> tuple[str, str, str, str, dict[str, Any], str, str]:
    strings = get_output_strings(target_language)
    clean_source = (source_text or "").strip()
    clean_translated = (translated_text or "").strip()

    if not clean_source and not clean_translated:
        return (
            "Please provide text to analyze.",
            "",
            "",
            render_entity_badges([]),
            {},
            f"<div class='insight-box'>{html.escape(strings['no_ai_insights_yet'])}</div>",
            "",
        )

    base_text = clean_source or clean_translated
    display_text = base_text if target_language == "English" else translate_plain_text(base_text, target_language)

    if is_ai_error(display_text):
        return (
            "Analysis could not start because the selected-language text could not be prepared. Please check the AI service configuration.",
            "",
            "",
            render_entity_badges([]),
            {},
            f"<div class='insight-box'>{html.escape(strings['no_ai_insights_yet'])}</div>",
            "",
        )

    analysis_text = translate_text_for_analysis(base_text)
    if is_ai_error(analysis_text):
        return (
            "Analysis could not start because translation to the internal analysis language failed. Please check the AI service configuration.",
            display_text,
            "",
            render_entity_badges([]),
            {},
            f"<div class='insight-box'>{html.escape(strings['no_ai_insights_yet'])}</div>",
            "",
        )

    try:
        result = analyze_text(analysis_text, domain)
    except Exception as exc:
        return (
            str(exc),
            display_text,
            "",
            render_entity_badges([]),
            {},
            f"<div class='insight-box'>{html.escape(strings['no_ai_insights_yet'])}</div>",
            "",
        )

    result["source_text"] = clean_source
    result["display_text"] = display_text
    result["output_language"] = target_language
    result["domain_display"] = localize_domain_name(result.get("domain", "unknown"), target_language)
    result["domain_analysis"] = localize_domain_info(result.get("domain_analysis", {}), target_language)
    ai_insight = build_ai_insight(result, target_language)
    summary = render_report_summary("manual_input.txt", "txt", result, strings)
    report_path = save_report(result, "manual_input.txt", "txt", ai_insight, target_language, strings) or ""
    status = (
        f"Cross-language analysis complete. {strings['entities_found']}: {result['entity_count']} | "
        f"{strings['detected_domain']}: {result['domain_display']} | "
        f"{strings['processing_time']}: {result['processing_time_seconds']}s."
    )
    return (
        status,
        display_text,
        summary,
        render_entity_badges(result["entities"]),
        result,
        f"<div class='insight-box'>{html.escape(ai_insight)}</div>",
        report_path,
    )


def create_app() -> gr.Blocks:
    with gr.Blocks(title="Multi-Domain NER Dashboard") as demo:
        gr.HTML(f"<style>{CSS}</style>")
        gr.HTML(get_header_html())

        with gr.Tabs():
            with gr.Tab("Document Analysis"):
                gr.HTML(get_document_intro_html())
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.HTML("<div class='panel-title'>Input Workspace</div><div class='panel-copy'>Load a document, inspect the extracted text, and choose whether domain detection should run automatically or use a fixed mode.</div>")
                        file_input = gr.File(label="Upload file", file_types=[".pdf", ".docx", ".txt"], type="filepath")
                        load_file_btn = gr.Button("Load File Into Editor", variant="secondary")
                        doc_text = gr.Textbox(label="Document text", lines=14, value=MEDICAL_EXAMPLE)
                        doc_domain = gr.Dropdown(
                            choices=["auto", "medical", "legal", "general"],
                            value="auto",
                            label="Domain",
                        )
                        doc_language = gr.Dropdown(
                            choices=SUPPORTED_LANGUAGES,
                            value="English",
                            label="Return results in",
                        )
                        with gr.Row():
                            analyze_btn = gr.Button("Analyze Document", variant="primary")
                            report_file = gr.File(label="Download report", interactive=False)
                        doc_status = gr.Textbox(label="Status", interactive=False)
                    with gr.Column(scale=1):
                        gr.HTML("<div class='panel-title'>Analysis Output</div><div class='panel-copy'>See the source content with highlighted entities, the final detected domain, and the reasoning signals that explain why the document belongs there.</div>")
                        doc_summary = gr.HTML("")
                        doc_highlight = gr.HTML(render_highlighted_text("", []))
                        doc_domain_reason = gr.HTML("")
                        doc_table = gr.Dataframe(
                            headers=["Text", "Label", "Start", "End", "Confidence"],
                            datatype=["str", "str", "number", "number", "number"],
                            row_count=8,
                            column_count=(5, "fixed"),
                            label="Detected entities",
                        )
                        doc_insight = gr.HTML("<div class='insight-box'>AI insights will appear here after analysis.</div>")
                        with gr.Accordion("Advanced structured result", open=False):
                            doc_json = gr.JSON(label="Structured result")

                load_file_btn.click(use_uploaded_file, inputs=[file_input, doc_text], outputs=[doc_text, doc_status])
                analyze_btn.click(
                    analyze_document,
                    inputs=[file_input, doc_text, doc_domain, doc_language],
                    outputs=[
                        doc_text,
                        doc_status,
                        doc_summary,
                        doc_table,
                        doc_json,
                        doc_highlight,
                        doc_domain_reason,
                        doc_insight,
                        report_file,
                    ],
                )

            with gr.Tab("AI Assistant"):
                gr.Markdown(
                    "### AI review assistant\n"
                    "<div class='section-copy'>Ask follow-up questions about the extracted entities, request a summary, "
                    "or get a plain-language explanation of the document.</div>"
                )
                assistant_context = gr.Textbox(label="Context text", lines=12, value=MEDICAL_EXAMPLE)
                assistant_question = gr.Textbox(label="Question", lines=6, placeholder="Ask for a summary, explanation, or next-step review.")
                assistant_ask_btn = gr.Button("Ask Assistant", variant="primary")
                assistant_status = gr.Textbox(label="Status", interactive=False)
                assistant_answer = gr.Textbox(label="Assistant response", lines=14, interactive=False)
                gr.HTML(get_disclaimer_html())

                assistant_ask_btn.click(
                    ask_assistant,
                    inputs=[assistant_context, assistant_question],
                    outputs=[assistant_status, assistant_answer],
                )

            with gr.Tab("Batch Analysis"):
                gr.Markdown(
                    "### Batch document analysis\n"
                    "<div class='section-copy'>Paste multiple documents, one per block separated by a blank line. "
                    "This runs them together and returns a compact review table.</div>"
                )
                batch_text = gr.Textbox(
                    label="Batch input",
                    lines=14,
                    value=f"{MEDICAL_EXAMPLE}\n\n{LEGAL_EXAMPLE}",
                )
                batch_domain = gr.Dropdown(
                    choices=["auto", "medical", "legal", "general"],
                    value="auto",
                    label="Domain",
                )
                batch_run_btn = gr.Button("Run Batch Analysis", variant="primary")
                batch_status = gr.Textbox(label="Status", interactive=False)
                batch_table = gr.Dataframe(
                    headers=["#", "Domain", "Entities", "Preview"],
                    datatype=["number", "str", "number", "str"],
                    row_count=10,
                    column_count=(4, "fixed"),
                    label="Batch results",
                )
                with gr.Accordion("Advanced batch JSON", open=False):
                    batch_json = gr.JSON(label="Batch JSON")

                batch_run_btn.click(
                    batch_analyze,
                    inputs=[batch_text, batch_domain],
                    outputs=[batch_status, batch_table, batch_json],
                )

            with gr.Tab("Multi-Language"):
                gr.Markdown(
                    "### Cross-language analysis\n"
                    "<div class='section-copy'>Translate text into your preferred output language, then run entity extraction "
                    "on the translated version without leaving the dashboard.</div>"
                )
                gr.HTML(
                    """
                    <div class='section-grid' style='margin-top:0;margin-bottom:18px;'>
                        <div class='feature-box'>
                            <div class='feature-kicker'>Language Coverage</div>
                            <div class='feature-title'>20+ Targets</div>
                            <div class='feature-note'>English, Hindi, Spanish, Arabic, French, Bengali, Tamil, Urdu, Chinese, and more.</div>
                        </div>
                        <div class='feature-box'>
                            <div class='feature-kicker'>Workflow</div>
                            <div class='feature-title'>Translate → Analyze</div>
                            <div class='feature-note'>Move from raw source text to translated content and structured entity extraction in one place.</div>
                        </div>
                        <div class='feature-box'>
                            <div class='feature-kicker'>Project Scope</div>
                            <div class='feature-title'>Matches 20+ Claim</div>
                            <div class='feature-note'>The selector now exposes the broader multilingual support that the project advertises.</div>
                        </div>
                    </div>
                    """
                )
                source_text = gr.Textbox(label="Source text", lines=10, value="Paciente con dolor torácico agudo. Se prescribió aspirina y se recomendó angiografía coronaria urgente.")
                with gr.Row():
                    target_language = gr.Dropdown(
                        choices=SUPPORTED_LANGUAGES,
                        value="English",
                        label="Return results in",
                    )
                    lang_domain = gr.Dropdown(
                        choices=["auto", "medical", "legal", "general"],
                        value="auto",
                        label="Domain",
                    )
                with gr.Row():
                    translate_btn = gr.Button("Translate Text", variant="secondary")
                    lang_analyze_btn = gr.Button("Analyze Translated Text", variant="primary")
                lang_status = gr.Textbox(label="Status", interactive=False)
                translated_text = gr.Textbox(label="Translated text", lines=10)
                lang_summary = gr.HTML("")
                lang_entities = gr.HTML(render_entity_badges([]))
                lang_insight = gr.HTML("<div class='insight-box'>AI insights will appear here after analysis.</div>")
                lang_report_file = gr.File(label="Download report", interactive=False)
                with gr.Accordion("Advanced structured result", open=False):
                    lang_json = gr.JSON(label="Structured result")

                translate_btn.click(
                    translate_text,
                    inputs=[source_text, target_language],
                    outputs=[lang_status, translated_text],
                )
                lang_analyze_btn.click(
                    analyze_translated_text,
                    inputs=[source_text, translated_text, lang_domain, target_language],
                    outputs=[lang_status, translated_text, lang_summary, lang_entities, lang_json, lang_insight, lang_report_file],
                )

            with gr.Tab("About"):
                gr.HTML(get_about_html())

        gr.HTML(get_legend_html(ENTITY_COLORS))

    return demo
