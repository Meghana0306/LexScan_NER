"""
scripts/validate_data.py
Validates all downloaded + processed data files.
Run after prepare_data.py to confirm everything is correct.
"""

import sys
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
logger = logging.getLogger(__name__)

CHECKS = {
    "data/raw/conll2003/conll2003_train.json":   ("general",  500),
    "data/raw/conll2003/conll2003_test.json":    ("general",  100),
    "data/raw/medical/ncbi_train.json":          ("medical",  100),
    "data/raw/medical/ncbi_test.json":           ("medical",   50),
    "data/raw/legal/legal_train.json":           ("legal",    100),
    "data/raw/legal/legal_test.json":            ("legal",     50),
    "data/processed/general/general_train.json": ("general",  100),
    "data/processed/medical/medical_train.json": ("medical",   50),
    "data/processed/legal/legal_train.json":     ("legal",     50),
}

def validate_raw(path: Path, domain: str):
    with open(path) as f:
        data = json.load(f)
    assert isinstance(data, list) and len(data) > 0, "Empty file"
    ex = data[0]
    assert "tokens"   in ex, "Missing 'tokens' key"
    assert "ner_tags" in ex, "Missing 'ner_tags' key"
    assert len(ex["tokens"]) == len(ex["ner_tags"]), "Token/tag length mismatch"
    return len(data)

def validate_processed(path: Path):
    with open(path) as f:
        data = json.load(f)
    assert isinstance(data, list) and len(data) > 0, "Empty file"
    ex = data[0]
    for key in ["input_ids", "attention_mask", "labels"]:
        assert key in ex, f"Missing '{key}'"
    assert len(ex["input_ids"]) == len(ex["labels"]), "input_ids/labels length mismatch"
    return len(data)

def main():
    logger.info("Validating data files …\n")
    passed = failed = 0

    for rel_path, (domain, min_count) in CHECKS.items():
        path = Path(rel_path)
        try:
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            if "processed" in rel_path:
                count = validate_processed(path)
            else:
                count = validate_raw(path, domain)

            if count < min_count:
                raise ValueError(f"Only {count} examples (expected ≥ {min_count})")

            logger.info(f"  ✅  {rel_path:55s}  {count:>6,} examples")
            passed += 1

        except Exception as e:
            logger.error(f"  ❌  {rel_path:55s}  FAILED: {e}")
            failed += 1

    logger.info(f"\n── Results: {passed} passed, {failed} failed ──")
    if failed == 0:
        logger.info("All checks passed! Ready for Phase 3 (training).")
    else:
        logger.warning("Fix the failed files before training.")
        sys.exit(1)

if __name__ == "__main__":
    main()
