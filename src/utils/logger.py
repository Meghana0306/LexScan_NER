"""
logger.py
─────────
Centralised logging setup using loguru.
Import and call setup_logger() once at the start of any script.

Usage:
    from src.utils.logger import setup_logger
    logger = setup_logger()
    logger.info("Training started")
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_file: str = "logs/ner_project.log",
                 level: str = "INFO",
                 rotation: str = "10 MB",
                 retention: str = "1 week") -> "logger":
    """
    Configure loguru logger with console + file output.

    Args:
        log_file:  Path to log file
        level:     Logging level (DEBUG/INFO/WARNING/ERROR)
        rotation:  When to rotate log file (e.g. "10 MB", "1 day")
        retention: How long to keep old logs

    Returns:
        Configured logger instance
    """
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console handler — colourised, readable
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
               "<level>{message}</level>",
        colorize=True,
    )

    # File handler — full details
    logger.add(
        log_file,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
    )

    logger.info(f"Logger initialised — level={level}, file={log_file}")
    return logger
