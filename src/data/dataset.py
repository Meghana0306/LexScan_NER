"""
dataset.py  —  PyTorch Dataset + DataLoader factory
Loads preprocessed JSON files (output of preprocessor.py)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
from torch.utils.data import Dataset, DataLoader, random_split

logger = logging.getLogger(__name__)


class ProcessedNERDataset(Dataset):
    """
    Loads already-tokenised NER data (output of preprocessor.py).
    Each record has: input_ids, attention_mask, token_type_ids, labels.
    """

    def __init__(self, json_path: str):
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {json_path}\n"
                                    "Run scripts/prepare_data.py first.")

        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self.examples: List[Dict[str, torch.Tensor]] = []
        for rec in raw:
            self.examples.append({
                "input_ids":      torch.tensor(rec["input_ids"],      dtype=torch.long),
                "attention_mask": torch.tensor(rec["attention_mask"], dtype=torch.long),
                "token_type_ids": torch.tensor(rec["token_type_ids"], dtype=torch.long),
                "labels":         torch.tensor(rec["labels"],         dtype=torch.long),
            })

        logger.info(f"Loaded {len(self.examples)} examples from {json_path}")

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return self.examples[idx]


# ──────────────────────────────────────────────────────────────────────────
def get_dataloaders(
    train_path: str,
    val_path: str,
    test_path: str,
    batch_size: int = 16,
    num_workers: int = 0,   # 0 = safe on Windows
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Build train / val / test DataLoaders from processed JSON files.
    """
    train_ds = ProcessedNERDataset(train_path)
    val_ds   = ProcessedNERDataset(val_path)
    test_ds  = ProcessedNERDataset(test_path)

    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True,  num_workers=num_workers
    )
    val_loader = DataLoader(
        val_ds,   batch_size=batch_size, shuffle=False, num_workers=num_workers
    )
    test_loader = DataLoader(
        test_ds,  batch_size=batch_size, shuffle=False, num_workers=num_workers
    )

    logger.info(
        f"DataLoaders ready — "
        f"train={len(train_ds)} | val={len(val_ds)} | test={len(test_ds)}"
    )
    return train_loader, val_loader, test_loader


# ──────────────────────────────────────────────────────────────────────────
def get_domain_dataloaders(domain: str, batch_size: int = 16) -> Tuple:
    """Convenience wrapper — pass domain name, get loaders."""
    base = Path("data/processed") / domain
    return get_dataloaders(
        train_path=str(base / f"{domain}_train.json"),
        val_path=str(base / f"{domain}_val.json"),
        test_path=str(base / f"{domain}_test.json"),
        batch_size=batch_size,
    )
