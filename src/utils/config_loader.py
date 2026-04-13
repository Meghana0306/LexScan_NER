"""
config_loader.py
================
Loads config.yaml and .env, provides a single Config object
used throughout the entire project.

Usage:
    from utils.config_loader import get_config

    cfg = get_config()
    print(cfg.project.name)
    print(cfg.training.learning_rate)
"""

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv
from loguru import logger


# ── Locate project root ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH  = PROJECT_ROOT / "configs" / "config.yaml"
ENV_PATH     = PROJECT_ROOT / ".env"


class DotDict:
    """
    Converts a nested dictionary into an object where keys
    are accessible as attributes.

    Example:
        d = DotDict({"training": {"lr": 2e-5}})
        d.training.lr  # → 2e-5
    """

    def __init__(self, data: Dict[str, Any]):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, DotDict(value))
            else:
                setattr(self, key, value)

    def __repr__(self):
        return f"DotDict({self.__dict__})"

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, DotDict):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result


def load_config(config_path: Path = CONFIG_PATH) -> DotDict:
    """
    Load and parse config.yaml into a DotDict object.

    Args:
        config_path: Path to the YAML config file.

    Returns:
        DotDict: Config accessible with dot notation.
    """
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at: {config_path}\n"
            f"Expected location: configs/config.yaml"
        )

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    logger.info(f"Config loaded from: {config_path}")
    return DotDict(raw)


def load_env(env_path: Path = ENV_PATH) -> None:
    """
    Load environment variables from .env file.

    Args:
        env_path: Path to the .env file.
    """
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger.info(f".env loaded from: {env_path}")
    else:
        logger.warning(
            f".env file not found at {env_path}. "
            f"Copy .env.example to .env and fill in your values."
        )


# ── Singleton config ─────────────────────────────────────────
_config: DotDict | None = None


def get_config(reload: bool = False) -> DotDict:
    """
    Get the global config singleton.
    Loads .env and config.yaml on first call.

    Args:
        reload: If True, reload config from disk.

    Returns:
        DotDict: The global config object.

    Example:
        cfg = get_config()
        lr  = cfg.training.learning_rate     # 2e-5
        dom = cfg.domains                    # ['medical', 'legal']
    """
    global _config
    if _config is None or reload:
        load_env()
        _config = load_config()
    return _config


def get_label2id(domain: str) -> Dict[str, int]:
    """
    Returns a mapping from entity label string → integer id.

    Args:
        domain: "medical" or "legal"

    Returns:
        dict: e.g. {"O": 0, "B-DISEASE": 1, "I-DISEASE": 2, ...}
    """
    cfg = get_config()
    labels = cfg.entity_labels.to_dict()[domain]
    return {label: idx for idx, label in enumerate(labels)}


def get_id2label(domain: str) -> Dict[int, str]:
    """
    Returns a mapping from integer id → entity label string.

    Args:
        domain: "medical" or "legal"

    Returns:
        dict: e.g. {0: "O", 1: "B-DISEASE", 2: "I-DISEASE", ...}
    """
    label2id = get_label2id(domain)
    return {v: k for k, v in label2id.items()}


if __name__ == "__main__":
    cfg = get_config()
    print(f"Project   : {cfg.project.name}")
    print(f"Version   : {cfg.project.version}")
    print(f"Domains   : {cfg.domains}")
    print(f"Med model : {cfg.models.medical_ner.model_name}")
    print(f"Law model : {cfg.models.legal_ner.model_name}")
    print(f"LR        : {cfg.training.learning_rate}")
    print(f"\nMedical labels ({len(cfg.entity_labels.medical)}):")
    print(cfg.entity_labels.medical)
