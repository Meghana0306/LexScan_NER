"""
verify_setup.py
===============
Run this after setup to confirm every dependency is installed
and the project config loads correctly.

Usage:
    python scripts/verify_setup.py
"""

import sys
import importlib
from pathlib import Path


# ── Colour helpers ───────────────────────────────────────────
GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW= "\033[93m"
CYAN  = "\033[96m"
RESET = "\033[0m"

def ok(msg):  print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg):print(f"  {RED}❌ {msg}{RESET}")
def warn(msg):print(f"  {YELLOW}⚠️  {msg}{RESET}")
def info(msg):print(f"  {CYAN}ℹ️  {msg}{RESET}")


def check_python_version():
    print("\n── Python version ──────────────────────────────────")
    major, minor = sys.version_info[:2]
    if major == 3 and minor >= 10:
        ok(f"Python {major}.{minor} (>=3.10 required)")
    else:
        fail(f"Python {major}.{minor} — need Python 3.10+")


def check_imports():
    print("\n── Core packages ───────────────────────────────────")
    packages = {
        # (import_name, display_name)
        "torch":            "PyTorch",
        "transformers":     "Hugging Face Transformers",
        "datasets":         "Hugging Face Datasets",
        "tokenizers":       "Tokenizers",
        "spacy":            "spaCy",
        "nltk":             "NLTK",
        "seqeval":          "seqeval",
        "numpy":            "NumPy",
        "pandas":           "Pandas",
        "sklearn":          "scikit-learn",
        "fastapi":          "FastAPI",
        "uvicorn":          "Uvicorn",
        "pydantic":         "Pydantic",
        "mlflow":           "MLflow",
        "dvc":              "DVC",
        "psycopg2":         "psycopg2",
        "sqlalchemy":       "SQLAlchemy",
        "elasticsearch":    "Elasticsearch",
        "prometheus_client":"Prometheus client",
        "streamlit":        "Streamlit",
        "yaml":             "PyYAML",
        "dotenv":           "python-dotenv",
        "loguru":           "Loguru",
        "rich":             "Rich",
        "click":            "Click",
        "pytest":           "pytest",
        "fitz":             "PyMuPDF",
        "docx":             "python-docx",
    }

    failed = []
    for module, name in packages.items():
        try:
            importlib.import_module(module)
            ok(name)
        except ImportError:
            fail(f"{name}  →  pip install {module}")
            failed.append(name)

    return failed


def check_torch_gpu():
    print("\n── GPU / CUDA ───────────────────────────────────────")
    try:
        import torch
        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
            ok(f"CUDA available — {gpu}")
        else:
            warn("CUDA not available — running on CPU (training will be slow)")
    except ImportError:
        fail("PyTorch not installed")


def check_spacy_model():
    print("\n── spaCy model ─────────────────────────────────────")
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        ok("en_core_web_sm loaded successfully")
    except OSError:
        fail("en_core_web_sm not found — run: python -m spacy download en_core_web_sm")


def check_folder_structure():
    print("\n── Folder structure ────────────────────────────────")
    required = [
        "data/raw/legal",
        "data/raw/medical",
        "data/processed/legal",
        "data/processed/medical",
        "data/splits",
        "data/annotations",
        "src/data",
        "src/models",
        "src/training",
        "src/evaluation",
        "src/api",
        "src/utils",
        "configs",
        "notebooks",
        "tests/unit",
        "tests/integration",
        "scripts",
        "logs",
        "mlruns",
        "docker",
    ]
    root = Path(__file__).parent.parent
    for folder in required:
        path = root / folder
        if path.exists():
            ok(folder)
        else:
            fail(f"{folder}  — missing! run setup_project.sh")


def check_config():
    print("\n── Config file ─────────────────────────────────────")
    root = Path(__file__).parent.parent
    config_path = root / "configs" / "config.yaml"
    if not config_path.exists():
        fail("configs/config.yaml not found")
        return

    try:
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        ok(f"config.yaml loaded — project: {cfg['project']['name']}")
        ok(f"Domains: {cfg['domains']}")
        ok(f"Medical labels: {len(cfg['entity_labels']['medical'])} tags")
        ok(f"Legal labels:   {len(cfg['entity_labels']['legal'])} tags")
    except Exception as e:
        fail(f"Config load failed: {e}")


def check_env_file():
    print("\n── Environment file ─────────────────────────────────")
    root = Path(__file__).parent.parent
    env_path = root / ".env"
    if env_path.exists():
        ok(".env file found")
    else:
        warn(".env not found — copy .env.example to .env and fill in values")


def check_git_dvc():
    print("\n── Git & DVC ───────────────────────────────────────")
    import subprocess
    root = Path(__file__).parent.parent

    git_dir = root / ".git"
    if git_dir.exists():
        ok("Git repository initialized")
    else:
        warn("Git not initialized — run: git init")

    dvc_dir = root / ".dvc"
    if dvc_dir.exists():
        ok("DVC initialized")
    else:
        warn("DVC not initialized — run: dvc init")


if __name__ == "__main__":
    print(f"\n{CYAN}{'='*52}")
    print("  Multi-Domain NER — Setup Verification")
    print(f"{'='*52}{RESET}")

    check_python_version()
    failed = check_imports()
    check_torch_gpu()
    check_spacy_model()
    check_folder_structure()
    check_config()
    check_env_file()
    check_git_dvc()

    print(f"\n{CYAN}{'='*52}{RESET}")
    if failed:
        print(f"{RED}  ❌ {len(failed)} package(s) missing. Fix them above.{RESET}")
    else:
        print(f"{GREEN}  ✅ All checks passed! Ready to move to Phase 2.{RESET}")
    print(f"{CYAN}{'='*52}{RESET}\n")
