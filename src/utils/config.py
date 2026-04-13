"""
config.py
─────────
Load and access the master config.yaml from anywhere in the project.

Usage:
    from src.utils.config import load_config
    cfg = load_config()
    lr = cfg.training.learning_rate
"""

import os
from pathlib import Path
from omegaconf import OmegaConf, DictConfig
from loguru import logger


def get_project_root() -> Path:
    """Return the project root directory (where config.yaml lives)."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "configs" / "config.yaml").exists():
            return parent
    raise FileNotFoundError("Could not find project root with configs/config.yaml")


def load_config(config_path: str = None) -> DictConfig:
    """
    Load the master configuration file.

    Args:
        config_path: Optional path to config.yaml. If None, auto-detects.

    Returns:
        OmegaConf DictConfig object. Access like: cfg.training.learning_rate
    """
    if config_path is None:
        root = get_project_root()
        config_path = root / "configs" / "config.yaml"

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found at: {config_path}")

    cfg = OmegaConf.load(config_path)
    logger.info(f"Config loaded from: {config_path}")
    return cfg


def get_label_list(cfg: DictConfig, domain: str) -> list:
    """Return the list of IOB2 labels for a given domain."""
    if domain == "medical":
        return list(cfg.labels.medical)
    elif domain == "legal":
        return list(cfg.labels.legal)
    else:
        raise ValueError(f"Unknown domain: {domain}. Use 'medical' or 'legal'.")


def get_label2id(cfg: DictConfig, domain: str) -> dict:
    """Return label → id mapping dict."""
    labels = get_label_list(cfg, domain)
    return {label: idx for idx, label in enumerate(labels)}


def get_id2label(cfg: DictConfig, domain: str) -> dict:
    """Return id → label mapping dict."""
    labels = get_label_list(cfg, domain)
    return {idx: label for idx, label in enumerate(labels)}
