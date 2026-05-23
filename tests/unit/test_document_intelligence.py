from services.document_intelligence import (
    build_workspace_analysis,
    classify_document_subtype,
    compare_documents,
    grounded_answer,
)


def test_classify_document_subtype_detects_contract():
    result = classify_document_subtype("This agreement includes termination and indemnity clauses.", "legal")
    assert result["subtype"] == "contract"


def test_grounded_answer_returns_citations():
    result = grounded_answer(
        "The contract renews on March 20, 2025. Payment is due within 15 days.",
        "When does it renew?",
    )
    assert "March 20, 2025" in result["answer"]
    assert result["citations"]


def test_build_workspace_analysis_adds_layers():
    base = {
        "text": "Patient has diabetes and follow-up on March 20, 2025.",
        "domain": "medical",
        "entities": [
            {"text": "diabetes", "label": "DISEASE"},
            {"text": "March 20, 2025", "label": "DATE"},
        ],
        "entity_count": 2,
    }
    out = build_workspace_analysis(base["text"], base)
    assert out["subtype"]
    assert out["plain_language"]["bullet_points"]
    assert out["timeline"]
    assert out["action_items"]


def test_compare_documents_detects_difference():
    a = {"domain": "legal", "entities": [{"text": "Court", "label": "COURT"}], "entity_count": 1}
    b = {"domain": "legal", "entities": [{"text": "Judge", "label": "JUDGE"}], "entity_count": 1}
    result = compare_documents("Court order", "Judge order", a, b)
    assert result["only_in_a"]
    assert result["only_in_b"]

