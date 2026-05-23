"""
Higher-level document intelligence built on top of the existing NER output.

This layer does not replace current entity extraction. It adds subtype
classification, risk clues, timelines, grounded answers, compare tools, and
plain-language summaries.
"""

from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any


_DATE_PATTERNS = [
    re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
    re.compile(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"),
]

_SUBTYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "prescription": ("rx", "tablet", "capsule", "dosage", "prescribed", "take once daily", "mg"),
    "lab_report": ("hemoglobin", "platelet", "wbc", "mri", "ct scan", "test result", "reference range"),
    "discharge_summary": ("discharge", "admitted", "hospital stay", "follow-up", "chief complaint"),
    "contract": ("agreement", "party", "terms", "obligation", "termination", "indemnity"),
    "court_order": ("court", "judge", "order", "petition", "hearing", "appellant", "respondent"),
    "invoice": ("invoice", "amount due", "gst", "bill to", "subtotal"),
    "identity_document": ("passport", "aadhaar", "license", "date of birth", "identity number"),
    "insurance_document": ("policy", "premium", "claim", "coverage", "insured"),
    "resume": ("experience", "education", "skills", "project", "employment history"),
}

_LEGAL_RED_FLAGS = [
    ("Termination risk", re.compile(r"\btermination\b|\bterminate\b", re.IGNORECASE), "Review exit rights, notice period, and penalties."),
    ("Penalty exposure", re.compile(r"\bpenalt(?:y|ies)\b|\bliquidated damages\b", re.IGNORECASE), "Check money exposure and triggering conditions."),
    ("Auto-renewal", re.compile(r"\bauto[- ]renew\b|\brenewal\b", re.IGNORECASE), "Track renewal deadlines to avoid accidental extension."),
    ("Confidentiality burden", re.compile(r"\bconfidential\b|\bnondisclosure\b", re.IGNORECASE), "Confirm what data is protected and for how long."),
]

_MEDICAL_RED_FLAGS = [
    ("Urgent symptom", re.compile(r"\bchest pain\b|\bshortness of breath\b|\bsevere\b|\burgent\b", re.IGNORECASE), "This may need urgent medical review."),
    ("Drug interaction review", re.compile(r"\baspirin\b|\bclopidogrel\b|\binsulin\b|\bwarfarin\b", re.IGNORECASE), "Review medicines and dosing carefully."),
    ("Follow-up needed", re.compile(r"\bfollow[- ]up\b|\breview after\b|\bmonitor\b", re.IGNORECASE), "A follow-up date or monitoring plan may be important."),
    ("Abnormal lab clue", re.compile(r"\babnormal\b|\bhigh\b|\blow\b|\bpositive\b", re.IGNORECASE), "Check whether the result is outside the normal range."),
]

_GENERAL_RED_FLAGS = [
    ("Financial obligation", re.compile(r"\bpay\b|\bdue\b|\bamount\b", re.IGNORECASE), "There may be a payment or money-related obligation."),
    ("Deadline", re.compile(r"\bdeadline\b|\bdue date\b|\bby\s+\d", re.IGNORECASE), "There may be a date-sensitive action item."),
]


def _sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [part.strip() for part in parts if part.strip()]


def _find_dates(text: str) -> list[str]:
    found: list[str] = []
    for pattern in _DATE_PATTERNS:
        found.extend(pattern.findall(text or ""))
    seen: set[str] = set()
    out: list[str] = []
    for item in found:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def classify_document_subtype(text: str, domain: str) -> dict[str, Any]:
    lowered = (text or "").lower()
    scores: dict[str, int] = {}
    for subtype, keywords in _SUBTYPE_KEYWORDS.items():
        scores[subtype] = sum(1 for keyword in keywords if keyword in lowered)
    best_subtype = max(scores, key=scores.get) if scores else "general_document"
    if scores.get(best_subtype, 0) == 0:
        best_subtype = {
            "medical": "medical_note",
            "legal": "legal_document",
        }.get(domain, "general_document")
    confidence = min(0.99, 0.35 + (scores.get(best_subtype, 0) * 0.12))
    return {"subtype": best_subtype, "confidence": round(confidence, 2), "scores": scores}


def normalize_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for entity in entities:
        item = dict(entity)
        text = str(entity.get("text") or "").strip()
        label = str(entity.get("label") or "").upper()
        canonical = text
        if label in {"DRUG", "DISEASE", "LAW", "STATUTE"}:
            canonical = text.lower()
        elif label in {"DATE"}:
            canonical = text.replace("/", "-")
        elif label in {"PERSON", "ORG", "COURT", "PARTY"}:
            canonical = " ".join(part.capitalize() for part in text.split())
        item["canonical_text"] = canonical
        normalized.append(item)
    return normalized


def extract_relations(text: str, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sentences = _sentence_split(text)
    relations: list[dict[str, Any]] = []
    for sentence in sentences[:25]:
        sentence_entities = [entity for entity in entities if str(entity.get("text") or "") and str(entity.get("text")) in sentence]
        if len(sentence_entities) < 2:
            continue
        labels = {str(item.get("label") or "").upper() for item in sentence_entities}
        relation_type = "co_occurs_with"
        if {"DRUG", "DISEASE"} <= labels:
            relation_type = "treats_or_related_to"
        elif {"PARTY", "DATE"} <= labels or {"COURT", "DATE"} <= labels:
            relation_type = "scheduled_or_filed_on"
        elif {"PERSON", "DATE"} <= labels:
            relation_type = "person_event_date"
        elif {"LAW", "CASE"} <= labels or {"STATUTE", "CASE"} <= labels:
            relation_type = "legal_reference"
        relations.append(
            {
                "relation": relation_type,
                "entities": [item.get("text") for item in sentence_entities[:4]],
                "evidence": sentence,
            }
        )
    return relations[:12]


def detect_red_flags(text: str, domain: str) -> list[dict[str, str]]:
    rules = _GENERAL_RED_FLAGS
    if domain == "legal":
        rules = _LEGAL_RED_FLAGS + _GENERAL_RED_FLAGS
    elif domain == "medical":
        rules = _MEDICAL_RED_FLAGS + _GENERAL_RED_FLAGS
    flags: list[dict[str, str]] = []
    for title, pattern, guidance in rules:
        match = pattern.search(text or "")
        if match:
            flags.append(
                {
                    "title": title,
                    "evidence": match.group(0),
                    "guidance": guidance,
                    "severity": "high" if domain in {"legal", "medical"} else "medium",
                }
            )
    return flags


def build_timeline(text: str, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sentences = _sentence_split(text)
    dates = [entity.get("text") for entity in entities if str(entity.get("label") or "").upper() == "DATE"]
    dates.extend(_find_dates(text))
    seen: set[str] = set()
    timeline: list[dict[str, Any]] = []
    for date_text in dates:
        if not date_text or date_text in seen:
            continue
        seen.add(str(date_text))
        evidence = next((sentence for sentence in sentences if str(date_text) in sentence), "")
        event = evidence or f"Reference to {date_text}"
        timeline.append({"date": str(date_text), "event": event[:220]})
    return timeline[:12]


def build_action_items(text: str, domain: str, red_flags: list[dict[str, str]], timeline: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for flag in red_flags[:5]:
        items.append(
            {
                "title": flag["title"],
                "action": flag["guidance"],
                "priority": "high" if flag.get("severity") == "high" else "medium",
            }
        )
    for event in timeline[:5]:
        items.append(
            {
                "title": f"Track date: {event['date']}",
                "action": event["event"],
                "priority": "medium" if domain == "general" else "high",
            }
        )
    if not items:
        items.append(
            {
                "title": "Review summary",
                "action": "Read the simplified explanation and verify important names, dates, and obligations.",
                "priority": "low",
            }
        )
    return items[:8]


def plain_language_summary(text: str, domain: str, subtype: str, entities: list[dict[str, Any]], red_flags: list[dict[str, str]]) -> dict[str, Any]:
    entity_counter = Counter(str(item.get("label") or "").upper() for item in entities)
    top_labels = ", ".join(f"{label} ({count})" for label, count in entity_counter.most_common(4)) or "No major entities"
    sentences = _sentence_split(text)
    headline = sentences[0][:220] if sentences else "Document received."
    summary_points = [
        f"This looks like a {subtype.replace('_', ' ')} in the {domain} domain.",
        f"The main extracted entity groups are {top_labels}.",
        f"The document opens with: {headline}",
    ]
    if red_flags:
        summary_points.append(f"There are {len(red_flags)} attention points that may need review.")
    else:
        summary_points.append("No strong risk clues were detected by the current rules.")
    return {
        "title": "Plain-language explanation",
        "short_summary": " ".join(summary_points[:2]),
        "bullet_points": summary_points,
    }


def grounded_answer(text: str, question: str) -> dict[str, Any]:
    def _norm(token: str) -> str:
        token = token.lower()
        for suffix in ("ing", "ed", "es", "s"):
            if token.endswith(suffix) and len(token) > len(suffix) + 2:
                return token[: -len(suffix)]
        return token

    q_tokens = {_norm(token) for token in re.findall(r"[A-Za-z0-9]+", question or "") if len(token) > 2}
    ranked: list[tuple[int, str]] = []
    for sentence in _sentence_split(text)[:50]:
        s_tokens = {_norm(token) for token in re.findall(r"[A-Za-z0-9]+", sentence)}
        overlap = len(q_tokens & s_tokens)
        if "when" in (question or "").lower() and _find_dates(sentence):
            overlap += 2
        if overlap:
            ranked.append((overlap, sentence))
    ranked.sort(key=lambda item: item[0], reverse=True)
    evidence = [sentence for _, sentence in ranked[:3]]
    if evidence:
        answer = "Based on the document, the strongest matching evidence is: " + " ".join(evidence[:2])
    else:
        answer = "I could not find a strong direct answer in the document text. Try asking with exact names, dates, medicines, or clauses."

    # Optional LLM refinement using the existing API-backed helper.
    try:
        from ai_helper import ask_ai

        llm_answer = ask_ai(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Answer the question using only the document evidence below. "
                        "If the evidence is insufficient, say so clearly.\n\n"
                        f"Question: {question}\n\n"
                        f"Evidence:\n- " + "\n- ".join(evidence[:3] if evidence else _sentence_split(text)[:3])
                    ),
                }
            ],
            system_prompt=(
                "You are a grounded document assistant. "
                "Use only the supplied evidence. "
                "Do not invent facts. "
                "Respond in clear, plain language."
            ),
        )
        if isinstance(llm_answer, str) and llm_answer and not llm_answer.startswith(("Error:", "Groq Error:", "Unexpected:", "❌")):
            answer = llm_answer.strip()
    except Exception:
        pass
    return {"answer": answer, "citations": evidence}


def compare_documents(text_a: str, text_b: str, analysis_a: dict[str, Any], analysis_b: dict[str, Any]) -> dict[str, Any]:
    entities_a = {f"{item.get('label')}::{str(item.get('text') or '').strip().lower()}" for item in analysis_a.get("entities", [])}
    entities_b = {f"{item.get('label')}::{str(item.get('text') or '').strip().lower()}" for item in analysis_b.get("entities", [])}
    only_a = sorted(entities_a - entities_b)
    only_b = sorted(entities_b - entities_a)
    similarity = SequenceMatcher(a=text_a or "", b=text_b or "").ratio()
    return {
        "similarity_score": round(similarity, 3),
        "domain_a": analysis_a.get("domain"),
        "domain_b": analysis_b.get("domain"),
        "entity_count_a": analysis_a.get("entity_count", 0),
        "entity_count_b": analysis_b.get("entity_count", 0),
        "only_in_a": only_a[:12],
        "only_in_b": only_b[:12],
        "summary": [
            f"Document A domain: {analysis_a.get('domain', 'unknown')}",
            f"Document B domain: {analysis_b.get('domain', 'unknown')}",
            f"Similarity score: {round(similarity * 100, 1)}%",
            f"Unique extracted items in A: {len(only_a)}",
            f"Unique extracted items in B: {len(only_b)}",
        ],
    }


def build_workspace_analysis(text: str, base_analysis: dict[str, Any]) -> dict[str, Any]:
    domain = str(base_analysis.get("domain") or "general")
    entities = base_analysis.get("entities", []) or []
    subtype = classify_document_subtype(text, domain)
    normalized_entities = normalize_entities(entities)
    red_flags = detect_red_flags(text, domain)
    timeline = build_timeline(text, entities)
    action_items = build_action_items(text, domain, red_flags, timeline)
    relations = extract_relations(text, entities)
    explanation = plain_language_summary(text, domain, subtype["subtype"], entities, red_flags)
    return {
        **base_analysis,
        "subtype": subtype["subtype"],
        "subtype_confidence": subtype["confidence"],
        "subtype_scores": subtype["scores"],
        "normalized_entities": normalized_entities,
        "red_flags": red_flags,
        "timeline": timeline,
        "action_items": action_items,
        "relations": relations,
        "plain_language": explanation,
    }
