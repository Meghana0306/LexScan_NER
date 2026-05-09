"""
NERPredictor — loads all 3 models and runs inference
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

logger = logging.getLogger(__name__)

# ── Model paths ────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = BASE_DIR / "models"

MODEL_PATHS = {
    "general": MODELS_DIR / "general_best_model",
    "medical": MODELS_DIR / "medical_best_model",
    "legal":   MODELS_DIR / "legal_best_model",
}

# ── Domain auto-detection keywords ────────────────────────────────────────
MEDICAL_KEYWORDS = {
    "patient", "diagnosis", "disease", "treatment", "drug", "symptom",
    "hospital", "clinical", "physician", "medication", "surgery", "cancer",
    "infection", "therapy", "dose", "mg", "prescribed", "administered",
    "medical", "health", "condition", "syndrome", "disorder", "chronic",
}

LEGAL_KEYWORDS = {
    "defendant", "plaintiff", "court", "judge", "attorney", "lawsuit",
    "contract", "statute", "jurisdiction", "verdict", "testimony", "case",
    "legal", "law", "section", "pursuant", "counsel", "motion", "appeal",
    "filed", "trial", "evidence", "testimony", "damages", "liability",
}

SYMPTOM_HINTS = {
    "pain", "fever", "breath", "shortness of breath", "sweating", "myalgia",
    "nausea", "vomiting", "cough", "fatigue", "dizziness", "headache",
    "chest pain", "retro-orbital pain", "diaphoresis", "palpitations",
}

DRUG_HINTS = {
    "aspirin", "atorvastatin", "metoprolol", "paracetamol", "clopidogrel",
    "metformin", "ibuprofen", "amoxicillin", "insulin", "heparin",
    "statin", "nsaid", "acetaminophen",
}

PROCEDURE_HINTS = {
    "angioplasty", "angiography", "stent implantation", "stent placement",
    "stent", "implantation", "surgery", "procedure", "operation",
    "coronary angiography",
}

FINDING_HINTS = {
    "stenosis", "positive", "negative", "platelets", "count",
    "occlusion", "narrowing", "lesion", "infarction", "elevation",
}

LOW_VALUE_ENTITY_TEXT = {
    "at", "in", "of", "on", "to", "by", "and", "or", "with", "for",
}

MEDICAL_SPAN_PATTERNS = {
    "AGE": [
        re.compile(r"\bage\s*[:\-]?\s*(\d{1,3})\b", re.IGNORECASE),
        re.compile(r"\b(\d{1,3})\s*(?:years?\s*old|year-old)\b", re.IGNORECASE),
    ],
    "GENDER": [
        re.compile(r"\b(?:male|female|man|woman)\b", re.IGNORECASE),
    ],
    "DRUG": [
        re.compile(r"\b([A-Z][a-z]+(?:statin|pril|olol|mab|cillin|formin)\w*)\b"),
        re.compile(r"\b(?:aspirin|atorvastatin|metoprolol|paracetamol|clopidogrel|metformin|ibuprofen|insulin|heparin)\b", re.IGNORECASE),
    ],
    "PROCEDURE": [
        re.compile(r"\b(?:angioplasty|angiography|stent implantation|stent placement|coronary angiography|surgery|operation)\b", re.IGNORECASE),
    ],
    "SYMPTOM": [
        re.compile(r"\b(?:chest pain|shortness of breath|high-grade fever|fever|myalgia|retro-orbital pain|sweating|diaphoresis|fatigue|cough)\b", re.IGNORECASE),
    ],
    "FINDING": [
        re.compile(r"\b(?:stenosis(?:\s+in\s+the\s+left\s+anterior\s+descending\s+branch)?|NS1 Antigen Positive|platelets?\s+\d[\d,/.]*|ST-elevation myocardial infarction|left anterior descending branch stenosis)\b", re.IGNORECASE),
        re.compile(r"\b\d{1,3}%\s+stenosis\b", re.IGNORECASE),
    ],
}


class NERPredictor:
    """Loads and serves all 3 NER models."""

    def __init__(self):
        self.models:     Dict[str, AutoModelForTokenClassification] = {}
        self.tokenizers: Dict[str, AutoTokenizer] = {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Predictor initialised on device: {self.device}")

    # ── Loading ────────────────────────────────────────────────────────────
    def load_model(self, domain: str) -> bool:
        path = MODEL_PATHS.get(domain)
        if path is None:
            logger.error(f"Unknown domain: {domain}")
            return False
        if not path.exists():
            logger.warning(f"Model path not found: {path}")
            return False
        try:
            logger.info(f"Loading {domain} model from {path} ...")
            self.tokenizers[domain] = AutoTokenizer.from_pretrained(
                str(path), local_files_only=True)
            self.models[domain] = AutoModelForTokenClassification.from_pretrained(
                str(path), local_files_only=True).to(self.device)
            self.models[domain].eval()
            logger.info(f"  ✅ {domain} model loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to load {domain} model: {e}")
            return False

    def load_all_models(self):
        for domain in MODEL_PATHS:
            self.load_model(domain)
        logger.info(f"Loaded models: {list(self.models.keys())}")

    def get_loaded_models(self) -> List[str]:
        return list(self.models.keys())

    # ── Domain detection ───────────────────────────────────────────────────
    def detect_domain(self, text: str) -> str:
        words = set(text.lower().split())
        med_score  = len(words & MEDICAL_KEYWORDS)
        leg_score  = len(words & LEGAL_KEYWORDS)
        if med_score == 0 and leg_score == 0:
            return "general"
        return "medical" if med_score >= leg_score else "legal"

    def _normalize_entity(self, text: str, label: str, start: int, end: int, confidence: float) -> Optional[Dict]:
        entity_text = text[start:end].strip(" \t\n\r:,-()[]")
        if not entity_text:
            return None
        actual_start = text.find(entity_text, start, end + 4)
        if actual_start == -1:
            actual_start = start
        actual_end = actual_start + len(entity_text)
        return {
            "text": entity_text,
            "label": label,
            "start": actual_start,
            "end": actual_end,
            "confidence": round(float(confidence), 4),
        }

    def _dedupe_entities(self, entities: List[Dict]) -> List[Dict]:
        deduped: List[Dict] = []
        seen: set[tuple[int, int, str]] = set()
        for entity in sorted(entities, key=lambda item: (item["start"], item["end"], -item["confidence"])):
            normalized_text = entity["text"].strip().lower()
            if normalized_text in LOW_VALUE_ENTITY_TEXT:
                continue
            if len(normalized_text) <= 2 and entity["label"] in {"DISEASE", "SYMPTOM", "DRUG", "PROCEDURE", "FINDING"}:
                continue
            key = (entity["start"], entity["end"], entity["label"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(entity)
        return deduped

    def _medical_label_override(self, entity_text: str, label: str) -> str:
        lowered = entity_text.lower()
        if any(hint in lowered for hint in DRUG_HINTS):
            return "DRUG"
        if any(hint in lowered for hint in PROCEDURE_HINTS):
            return "PROCEDURE"
        if any(hint in lowered for hint in SYMPTOM_HINTS):
            return "SYMPTOM"
        if any(hint in lowered for hint in FINDING_HINTS):
            return "FINDING"
        return label

    def _apply_medical_postprocessing(self, text: str, entities: List[Dict]) -> List[Dict]:
        adjusted: List[Dict] = []
        for entity in entities:
            label = self._medical_label_override(entity["text"], entity["label"])
            adjusted.append({**entity, "label": label})

        for label, patterns in MEDICAL_SPAN_PATTERNS.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    normalized = self._normalize_entity(
                        text,
                        label,
                        match.start(),
                        match.end(),
                        0.88,
                    )
                    if normalized:
                        adjusted.append(normalized)

        adjusted = self._dedupe_entities(adjusted)
        return sorted(adjusted, key=lambda item: (item["start"], item["end"]))

    # ── Inference ──────────────────────────────────────────────────────────
    def predict(self, text: str, domain: str) -> List[Dict]:
        if domain not in self.models:
            available = list(self.models.keys())
            raise ValueError(
                f"Domain '{domain}' not loaded. Available: {available}")

        tokenizer = self.tokenizers[domain]
        model     = self.models[domain]
        id2label  = model.config.id2label

        # Tokenise — keep word IDs for alignment
        encoding = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            return_offsets_mapping=True,
        )
        offset_mapping = encoding.pop("offset_mapping")[0].tolist()
        input_ids      = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        with torch.no_grad():
            logits = model(input_ids=input_ids,
                           attention_mask=attention_mask).logits

        probs      = torch.softmax(logits, dim=-1)[0]
        pred_ids   = torch.argmax(probs, dim=-1).tolist()
        confidences = probs.max(dim=-1).values.tolist()

        # ── Decode tokens → character-level entities ───────────────────────
        raw_entities = []
        for idx, (pred_id, conf, (start, end)) in enumerate(
                zip(pred_ids, confidences, offset_mapping)):
            if start == end:          # special token
                continue
            label = id2label[pred_id]
            if label == "O":
                continue
            raw_entities.append({
                "label": label,
                "start": start,
                "end":   end,
                "conf":  conf,
            })

        # ── Merge consecutive B-/I- tokens into spans ─────────────────────
        entities = []
        i = 0
        while i < len(raw_entities):
            ent = raw_entities[i]
            label = ent["label"]

            if label.startswith("B-"):
                entity_type = label[2:]
                span_start  = ent["start"]
                span_end    = ent["end"]
                conf_scores = [ent["conf"]]
                j = i + 1
                while j < len(raw_entities):
                    nxt = raw_entities[j]
                    if nxt["label"] == f"I-{entity_type}":
                        span_end = nxt["end"]
                        conf_scores.append(nxt["conf"])
                        j += 1
                    else:
                        break
                entity_text = text[span_start:span_end].strip()
                if entity_text:
                    entities.append({
                        "text":       entity_text,
                        "label":      entity_type,
                        "start":      span_start,
                        "end":        span_end,
                        "confidence": round(
                            sum(conf_scores) / len(conf_scores), 4),
                    })
                i = j
            else:
                i += 1

        if domain == "medical":
            return self._apply_medical_postprocessing(text, entities)
        return entities
