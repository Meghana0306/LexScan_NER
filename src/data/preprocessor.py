"""
Preprocessor for Multi-Domain NER
- Word-piece tokenization with IOB2 tag alignment
- Handles BERT / BioBERT / LegalBERT tokenizers
- Outputs HuggingFace-ready tensors
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import torch
from torch.utils.data import Dataset
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

# ── Label sets ─────────────────────────────────────────────────────────────
MEDICAL_LABELS = [
    "O",
    "B-DISEASE", "I-DISEASE",
    "B-CHEMICAL", "I-CHEMICAL",
    "B-DRUG", "I-DRUG",
    "B-SYMPTOM", "I-SYMPTOM",
    "B-PROCEDURE", "I-PROCEDURE",
    "B-ANATOMY", "I-ANATOMY",
]

LEGAL_LABELS = [
    "O",
    "B-PERSON", "I-PERSON",
    "B-ORG", "I-ORG",
    "B-COURT", "I-COURT",
    "B-DATE", "I-DATE",
    "B-LAW", "I-LAW",
    "B-CASE", "I-CASE",
    "B-LOCATION", "I-LOCATION",
]

GENERAL_LABELS = [
    "O",
    "B-PER", "I-PER",
    "B-ORG", "I-ORG",
    "B-LOC", "I-LOC",
    "B-MISC", "I-MISC",
]

DOMAIN_LABELS = {
    "medical": MEDICAL_LABELS,
    "legal":   LEGAL_LABELS,
    "general": GENERAL_LABELS,
}


def get_label_maps(domain: str) -> Tuple[Dict, Dict]:
    """Return (label2id, id2label) for a domain."""
    labels = DOMAIN_LABELS[domain]
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for i, l in enumerate(labels)}
    return label2id, id2label


def normalise_tag(tag: str, domain: str) -> str:
    """Map dataset-specific tags to our unified label set."""
    label2id, _ = get_label_maps(domain)

    # exact match first
    if tag in label2id:
        return tag

    # CoNLL → general
    mapping = {
        "B-PER": "B-PER", "I-PER": "I-PER",
        "B-PERSON": "B-PER", "I-PERSON": "I-PER",
        "B-ORG": "B-ORG", "I-ORG": "I-ORG",
        "B-LOC": "B-LOC", "I-LOC": "I-LOC",
        "B-MISC": "B-MISC", "I-MISC": "I-MISC",
        # NCBI → medical
        "B-Disease": "B-DISEASE", "I-Disease": "I-DISEASE",
        "B-Chemical": "B-CHEMICAL", "I-Chemical": "I-CHEMICAL",
        # BC5CDR
        "B-disease": "B-DISEASE", "I-disease": "I-DISEASE",
        "B-chemical": "B-CHEMICAL", "I-chemical": "I-CHEMICAL",
    }
    mapped = mapping.get(tag, "O")
    # verify it exists in this domain's labels
    return mapped if mapped in label2id else "O"


# ══════════════════════════════════════════════════════════════════════════
# Core alignment function
# ══════════════════════════════════════════════════════════════════════════
def align_labels_with_tokens(
    tokens: List[str],
    ner_tags: List[str],
    tokenizer,
    label2id: Dict[str, int],
    max_length: int = 512,
    domain: str = "general",
) -> Dict:
    """
    Tokenise a word list and align NER tags with word-pieces.
    Sub-words get label -100 (ignored in loss) except the first sub-word
    which inherits the word's label.
    Returns a dict ready for model input.
    """
    encoding = tokenizer(
        tokens,
        is_split_into_words=True,
        max_length=max_length,
        truncation=True,
        padding="max_length",
        return_tensors="pt",
    )

    word_ids = encoding.word_ids(batch_index=0)
    labels = []
    prev_word_id = None

    for word_id in word_ids:
        if word_id is None:
            # [CLS] / [SEP] / padding
            labels.append(-100)
        elif word_id != prev_word_id:
            # first sub-word of a word → use real label
            raw_tag = ner_tags[word_id] if word_id < len(ner_tags) else "O"
            norm_tag = normalise_tag(raw_tag, domain)
            labels.append(label2id.get(norm_tag, 0))
        else:
            # subsequent sub-words → -100 (ignore)
            labels.append(-100)
        prev_word_id = word_id

    return {
        "input_ids":      encoding["input_ids"].squeeze(0),
        "attention_mask": encoding["attention_mask"].squeeze(0),
        "token_type_ids": encoding.get("token_type_ids",
                          torch.zeros_like(encoding["input_ids"])).squeeze(0),
        "labels":         torch.tensor(labels, dtype=torch.long),
    }


# ══════════════════════════════════════════════════════════════════════════
# PyTorch Dataset
# ══════════════════════════════════════════════════════════════════════════
class NERDataset(Dataset):
    """
    PyTorch Dataset for token-classification (NER).
    Loads a JSON file of {tokens, ner_tags, domain} records.
    """

    def __init__(
        self,
        json_path: str,
        tokenizer_name: str,
        domain: str,
        max_length: int = 512,
        cache_dir: Optional[str] = None,
    ):
        self.domain = domain
        self.max_length = max_length
        self.label2id, self.id2label = get_label_maps(domain)

        logger.info(f"Loading tokenizer: {tokenizer_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_name,
            cache_dir=cache_dir,
            use_fast=True,
        )

        logger.info(f"Loading dataset: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self.examples = []
        skipped = 0
        for rec in raw:
            tokens   = rec.get("tokens", [])
            ner_tags = rec.get("ner_tags", [])
            if not tokens or len(tokens) != len(ner_tags):
                skipped += 1
                continue
            self.examples.append((tokens, ner_tags))

        logger.info(
            f"  Loaded {len(self.examples)} examples "
            f"(skipped {skipped} malformed) from {json_path}"
        )

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> Dict:
        tokens, ner_tags = self.examples[idx]
        return align_labels_with_tokens(
            tokens=tokens,
            ner_tags=ner_tags,
            tokenizer=self.tokenizer,
            label2id=self.label2id,
            max_length=self.max_length,
            domain=self.domain,
        )


# ══════════════════════════════════════════════════════════════════════════
# Preprocessing pipeline — batch-process raw JSONs → processed JSONs
# ══════════════════════════════════════════════════════════════════════════
def preprocess_split(
    input_path: Path,
    output_path: Path,
    tokenizer_name: str,
    domain: str,
    max_length: int = 512,
):
    """Tokenise + align a raw JSON split and save processed version."""
    label2id, _ = get_label_maps(domain)

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, use_fast=True)

    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    processed = []
    for rec in raw:
        tokens   = rec.get("tokens", [])
        ner_tags = rec.get("ner_tags", [])
        if not tokens or len(tokens) != len(ner_tags):
            continue

        enc = align_labels_with_tokens(
            tokens=tokens,
            ner_tags=ner_tags,
            tokenizer=tokenizer,
            label2id=label2id,
            max_length=max_length,
            domain=domain,
        )
        # convert tensors → lists for JSON serialisation
        processed.append({
            "input_ids":      enc["input_ids"].tolist(),
            "attention_mask": enc["attention_mask"].tolist(),
            "token_type_ids": enc["token_type_ids"].tolist(),
            "labels":         enc["labels"].tolist(),
            "domain":         domain,
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed, f)

    logger.info(f"  Processed {len(processed)} examples → {output_path}")


def run_preprocessing():
    """Run full preprocessing pipeline for all datasets."""
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)s  %(message)s")

    RAW       = Path("data/raw")
    PROCESSED = Path("data/processed")

    configs = [
        # (input_glob_pattern, domain, tokenizer)
        {
            "files": [
                (RAW / "conll2003" / "conll2003_train.json",      "train"),
                (RAW / "conll2003" / "conll2003_validation.json",  "val"),
                (RAW / "conll2003" / "conll2003_test.json",        "test"),
            ],
            "domain":    "general",
            "tokenizer": "distilbert-base-uncased",
            "out_dir":   PROCESSED / "general",
        },
        {
            "files": [
                (RAW / "medical" / "ncbi_train.json", "train"),
                (RAW / "medical" / "ncbi_dev.json",   "val"),
                (RAW / "medical" / "ncbi_test.json",  "test"),
            ],
            "domain":    "medical",
            "tokenizer": "dmis-lab/biobert-base-cased-v1.2",
            "out_dir":   PROCESSED / "medical",
        },
        {
            "files": [
                (RAW / "legal" / "legal_train.json", "train"),
                (RAW / "legal" / "legal_dev.json",   "val"),
                (RAW / "legal" / "legal_test.json",  "test"),
            ],
            "domain":    "legal",
            "tokenizer": "nlpaueb/legal-bert-base-uncased",
            "out_dir":   PROCESSED / "legal",
        },
    ]

    for cfg in configs:
        domain = cfg["domain"]
        logger.info(f"\n{'='*50}")
        logger.info(f"  Processing domain: {domain.upper()}")
        logger.info(f"{'='*50}")
        for src_path, split in cfg["files"]:
            if not src_path.exists():
                logger.warning(f"  Missing: {src_path} — skipping")
                continue
            out_path = cfg["out_dir"] / f"{domain}_{split}.json"
            preprocess_split(
                input_path=src_path,
                output_path=out_path,
                tokenizer_name=cfg["tokenizer"],
                domain=domain,
            )

    logger.info("\n✅  Preprocessing complete.")


if __name__ == "__main__":
    run_preprocessing()
