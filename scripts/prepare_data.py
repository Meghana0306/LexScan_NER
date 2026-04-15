"""
scripts/prepare_data.py
=======================
Run this ONE script to do ALL of Phase 2:
  1. Download all datasets
  2. Preprocess + tokenise for BERT
  3. Print dataset statistics

Usage:
    python scripts/prepare_data.py
    python scripts/prepare_data.py --skip-download   (if data already downloaded)
    python scripts/prepare_data.py --domain medical  (only one domain)
"""

import sys
import argparse
import logging
from pathlib import Path

# ── make sure src/ is on the path ─────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data.downloader   import download_all
from src.data.preprocessor import run_preprocessing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_stats():
    """Print record counts for every processed file."""
    import json
    processed = Path("data/processed")
    if not processed.exists():
        logger.warning("data/processed/ not found — run preprocessing first.")
        return

    logger.info("\n── Dataset Statistics ─────────────────────────────")
    total = 0
    for domain_dir in sorted(processed.iterdir()):
        if not domain_dir.is_dir():
            continue
        logger.info(f"  {domain_dir.name.upper()}")
        for jf in sorted(domain_dir.glob("*.json")):
            with open(jf) as f:
                n = len(json.load(f))
            logger.info(f"    {jf.name:35s}  {n:>6,} examples")
            total += n
    logger.info(f"  {'TOTAL':35s}  {total:>6,} examples")
    logger.info("─" * 52)


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Data Pipeline")
    parser.add_argument("--skip-download",   action="store_true",
                        help="Skip downloading datasets")
    parser.add_argument("--skip-preprocess", action="store_true",
                        help="Skip preprocessing step")
    args = parser.parse_args()

    logger.info("╔══════════════════════════════════════════╗")
    logger.info("║  Multi-Domain NER  —  Phase 2: Data      ║")
    logger.info("╚══════════════════════════════════════════╝\n")

    # Step 1 — Download
    if not args.skip_download:
        logger.info("STEP 1: Downloading datasets …\n")
        results = download_all()
        failed = [k for k, v in results.items() if not v]
        if failed:
            logger.warning(f"Some downloads failed: {failed}")
            logger.warning("Continuing with available data …")
    else:
        logger.info("STEP 1: Skipped (--skip-download)")

    # Step 2 — Preprocess
    if not args.skip_preprocess:
        logger.info("\nSTEP 2: Preprocessing + tokenising …\n")
        run_preprocessing()
    else:
        logger.info("STEP 2: Skipped (--skip-preprocess)")

    # Step 3 — Stats
    logger.info("\nSTEP 3: Dataset statistics")
    print_stats()

    logger.info("\n✅  Phase 2 complete!")
    logger.info("    Next: open Google Colab and run Phase 3 (training).")


if __name__ == "__main__":
    main()
