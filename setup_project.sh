#!/bin/bash
# ============================================================
# setup_project.sh
# Run this ONCE after cloning / creating the project.
# It sets up Git, virtual environment, installs deps, and DVC.
# ============================================================

set -e  # exit immediately if any command fails

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   Multi-Domain NER — Project Setup                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Git Init ─────────────────────────────────────────
echo "▶ Step 1: Initializing Git..."
git init
git config user.email "you@example.com"   # change this
git config user.name "Your Name"           # change this
echo "  ✅ Git initialized"

# ── Step 2: Virtual Environment ──────────────────────────────
echo ""
echo "▶ Step 2: Creating Python virtual environment..."
python3 -m venv venv
echo "  ✅ Virtual environment created in ./venv"
echo "  ➜  To activate: source venv/bin/activate (Linux/Mac)"
echo "  ➜  To activate: venv\\Scripts\\activate (Windows)"

# Activate for the rest of this script
source venv/bin/activate

# ── Step 3: Upgrade pip ───────────────────────────────────────
echo ""
echo "▶ Step 3: Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo "  ✅ pip upgraded"

# ── Step 4: Install requirements ─────────────────────────────
echo ""
echo "▶ Step 4: Installing requirements (this takes a few minutes)..."
pip install -r requirements.txt
echo "  ✅ All packages installed"

# ── Step 5: Download spaCy model ─────────────────────────────
echo ""
echo "▶ Step 5: Downloading spaCy English model..."
python -m spacy download en_core_web_sm
echo "  ✅ spaCy model downloaded"

# ── Step 6: Install project as editable package ──────────────
echo ""
echo "▶ Step 6: Installing project as editable package..."
pip install -e .
echo "  ✅ Project installed in editable mode"

# ── Step 7: DVC Init ─────────────────────────────────────────
echo ""
echo "▶ Step 7: Initializing DVC..."
dvc init
echo "  ✅ DVC initialized"

# ── Step 8: Create .env from example ─────────────────────────
echo ""
echo "▶ Step 8: Creating .env file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  ✅ .env created — EDIT IT with your actual values before running"
else
    echo "  ⚠️  .env already exists — skipping"
fi

# ── Step 9: Create outputs dir ───────────────────────────────
echo ""
echo "▶ Step 9: Creating output directories..."
mkdir -p outputs/models
mkdir -p outputs/training
mkdir -p outputs/evaluation
touch outputs/.gitkeep
echo "  ✅ Output directories created"

# ── Step 10: Pre-commit hooks ────────────────────────────────
echo ""
echo "▶ Step 10: Setting up pre-commit hooks..."
pre-commit install
echo "  ✅ Pre-commit hooks installed"

# ── Step 11: Initial git commit ──────────────────────────────
echo ""
echo "▶ Step 11: Initial Git commit..."
git add .
git commit -m "feat: initial project structure and configuration"
echo "  ✅ Initial commit done"

# ── Done ─────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✅ Setup complete!                                 ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Next steps:                                         ║"
echo "║  1. source venv/bin/activate                         ║"
echo "║  2. Edit .env with your values                       ║"
echo "║  3. Run: python scripts/verify_setup.py              ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
