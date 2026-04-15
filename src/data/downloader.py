"""
Data Downloader for Multi-Domain NER Project
Downloads: CoNLL-2003 (general), MIT Movie/Restaurant (general),
           NCBI Disease (medical), BC5CDR (medical/chemical),
           and creates synthetic legal data.
"""

import os
import json
import random
import requests
import zipfile
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

# ── paths ──────────────────────────────────────────────────────────────────
RAW_DIR = Path("data/raw")
MEDICAL_DIR = RAW_DIR / "medical"
LEGAL_DIR   = RAW_DIR / "legal"
CONLL_DIR   = RAW_DIR / "conll2003"

for d in [MEDICAL_DIR, LEGAL_DIR, CONLL_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════
# 1.  CoNLL-2003  (via HuggingFace datasets — free, no login needed)
# ══════════════════════════════════════════════════════════════════════════
def download_conll2003() -> bool:
    """Download CoNLL-2003 via HuggingFace datasets library."""
    output = CONLL_DIR / "conll2003_train.json"
    if output.exists():
        logger.info("CoNLL-2003 already downloaded — skipping.")
        return True

    try:
        from datasets import load_dataset
        logger.info("Downloading CoNLL-2003 from HuggingFace …")
        ds = load_dataset("conll2003", trust_remote_code=True)

        label_names = ds["train"].features["ner_tags"].feature.names

        for split in ["train", "validation", "test"]:
            records = []
            for ex in ds[split]:
                records.append({
                    "tokens": ex["tokens"],
                    "ner_tags": [label_names[t] for t in ex["ner_tags"]],
                    "domain": "general"
                })
            out_path = CONLL_DIR / f"conll2003_{split}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            logger.info(f"  Saved {len(records)} {split} examples → {out_path}")

        return True

    except Exception as e:
        logger.error(f"CoNLL-2003 download failed: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════
# 2.  NCBI Disease Corpus  (medical — disease entities)
# ══════════════════════════════════════════════════════════════════════════
NCBI_URLS = {
    "train": "https://raw.githubusercontent.com/spyysalo/ncbi-disease/master/conll/train.tsv",
    "dev":   "https://raw.githubusercontent.com/spyysalo/ncbi-disease/master/conll/devel.tsv",
    "test":  "https://raw.githubusercontent.com/spyysalo/ncbi-disease/master/conll/test.tsv",
}

def parse_conll_tsv(lines: List[str]) -> List[Dict]:
    """Parse CoNLL-format TSV into list of {tokens, ner_tags} dicts."""
    sentences, tokens, tags = [], [], []
    for line in lines:
        line = line.strip()
        if not line:
            if tokens:
                sentences.append({"tokens": tokens, "ner_tags": tags, "domain": "medical"})
                tokens, tags = [], []
        else:
            parts = line.split()
            tokens.append(parts[0])
            # last column is the tag
            raw_tag = parts[-1]
            # normalise NCBI tags → standard IOB2
            if raw_tag == "O":
                tags.append("O")
            elif raw_tag.startswith("B-") or raw_tag.startswith("I-"):
                tags.append(raw_tag)
            else:
                tags.append("O")
    if tokens:
        sentences.append({"tokens": tokens, "ner_tags": tags, "domain": "medical"})
    return sentences


def download_ncbi_disease() -> bool:
    output = MEDICAL_DIR / "ncbi_train.json"
    if output.exists():
        logger.info("NCBI Disease already downloaded — skipping.")
        return True

    try:
        logger.info("Downloading NCBI Disease corpus …")
        for split, url in NCBI_URLS.items():
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            sentences = parse_conll_tsv(resp.text.splitlines())
            out_path = MEDICAL_DIR / f"ncbi_{split}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(sentences, f, indent=2)
            logger.info(f"  Saved {len(sentences)} {split} examples → {out_path}")
        return True

    except Exception as e:
        logger.error(f"NCBI download failed: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════
# 3.  BC5CDR  (chemical + disease — via HuggingFace)
# ══════════════════════════════════════════════════════════════════════════
def download_bc5cdr() -> bool:
    output = MEDICAL_DIR / "bc5cdr_train.json"
    if output.exists():
        logger.info("BC5CDR already downloaded — skipping.")
        return True

    try:
        from datasets import load_dataset
        logger.info("Downloading BC5CDR from HuggingFace …")
        ds = load_dataset("tner/bc5cdr", trust_remote_code=True)
        label_names = ds["train"].features["tags"].feature.names

        split_map = {"train": "train", "validation": "validation", "test": "test"}
        for hf_split, file_split in split_map.items():
            if hf_split not in ds:
                continue
            records = []
            for ex in ds[hf_split]:
                records.append({
                    "tokens":   ex["tokens"],
                    "ner_tags": [label_names[t] for t in ex["tags"]],
                    "domain":   "medical"
                })
            out_path = MEDICAL_DIR / f"bc5cdr_{file_split}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            logger.info(f"  Saved {len(records)} {file_split} examples → {out_path}")
        return True

    except Exception as e:
        logger.warning(f"BC5CDR download failed (will use NCBI only): {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════
# 4.  Synthetic Legal Data  (rule-based generator)
# ══════════════════════════════════════════════════════════════════════════
LEGAL_TEMPLATES = [
    ("The defendant {PERSON} was charged under Section {LAW} of the {LAW}.",
     ["O","O","B-PERSON","O","O","O","B-LAW","O","O","B-LAW","I-LAW","O"]),

    ("{PERSON} , representing {ORG} , filed a motion on {DATE} in {COURT} .",
     ["B-PERSON","O","O","B-ORG","O","O","O","O","O","B-DATE","O","B-COURT","I-COURT","O"]),

    ("The contract between {ORG} and {ORG} was executed on {DATE} .",
     ["O","O","O","B-ORG","O","B-ORG","O","O","O","B-DATE","O"]),

    ("Judge {PERSON} presided over the case at {COURT} .",
     ["O","B-PERSON","O","O","O","O","O","B-COURT","I-COURT","O"]),

    ("Pursuant to {LAW} , {ORG} was found liable for damages .",
     ["O","O","B-LAW","O","B-ORG","O","O","O","O","O","O"]),
]

PERSONS  = ["John Smith","Mary Johnson","Robert Williams","Sarah Davis","Michael Brown"]
ORGS     = ["Acme Corporation","Global Industries LLC","State Farm Insurance","Johnson & Associates"]
DATES    = ["January 15, 2023","March 3, 2022","December 12, 2021","July 4, 2020"]
COURTS   = ["Supreme Court","District Court","Court of Appeals","Federal Circuit"]
LAWS     = ["Title VII","Section 1983","the Civil Rights Act","the ADA","HIPAA"]

FILL = {"PERSON": PERSONS, "ORG": ORGS, "DATE": DATES, "COURT": COURTS, "LAW": LAWS}


def generate_legal_sentence() -> Dict:
    template, tag_template = random.choice(LEGAL_TEMPLATES)
    filled = template
    for key, values in FILL.items():
        filled = filled.replace("{" + key + "}", random.choice(values), 1)

    tokens = filled.split()
    # rebuild tags to match actual token count (simple alignment)
    # For synthetic data we use a smarter approach: re-tokenize
    ner_tags = []
    for tok in tokens:
        assigned = "O"
        for key, values in FILL.items():
            for val in values:
                val_tokens = val.split()
                if tok == val_tokens[0]:
                    assigned = f"B-{key}"
                elif tok in val_tokens[1:]:
                    assigned = f"I-{key}"
        ner_tags.append(assigned)

    return {"tokens": tokens, "ner_tags": ner_tags, "domain": "legal"}


def generate_legal_dataset(n: int = 2000) -> bool:
    output = LEGAL_DIR / "legal_train.json"
    if output.exists():
        logger.info("Legal dataset already generated — skipping.")
        return True

    logger.info(f"Generating {n} synthetic legal sentences …")
    random.seed(42)
    all_data = [generate_legal_sentence() for _ in range(n)]
    random.shuffle(all_data)

    splits = {"train": 0.7, "dev": 0.15, "test": 0.15}
    idx = 0
    for split, ratio in splits.items():
        count = int(n * ratio)
        chunk = all_data[idx: idx + count]
        idx += count
        out_path = LEGAL_DIR / f"legal_{split}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, indent=2)
        logger.info(f"  Saved {len(chunk)} {split} legal examples → {out_path}")

    return True


# ══════════════════════════════════════════════════════════════════════════
# 5.  Master download function
# ══════════════════════════════════════════════════════════════════════════
def download_all():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)s  %(message)s")
    logger.info("=" * 60)
    logger.info("  Multi-Domain NER — Data Download")
    logger.info("=" * 60)

    results = {
        "CoNLL-2003":    download_conll2003(),
        "NCBI Disease":  download_ncbi_disease(),
        "BC5CDR":        download_bc5cdr(),
        "Legal (synth)": generate_legal_dataset(n=2000),
    }

    logger.info("\n── Download Summary ──────────────────────")
    for name, ok in results.items():
        status = "✅  OK" if ok else "❌  FAILED"
        logger.info(f"  {name:20s}  {status}")
    logger.info("─" * 42)

    success = sum(results.values())
    logger.info(f"  {success}/{len(results)} datasets ready.")
    return results


if __name__ == "__main__":
    download_all()
