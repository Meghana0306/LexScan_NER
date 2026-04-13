# ══════════════════════════════════════════════════════
#  Makefile — run any task with a single command
#  Usage: make <target>
# ══════════════════════════════════════════════════════

.PHONY: help setup install lint test train-medical train-legal evaluate api streamlit clean

help:
	@echo ""
	@echo "  make setup           → create venv and install all dependencies"
	@echo "  make install         → install dependencies in existing venv"
	@echo "  make lint            → run black + isort + flake8"
	@echo "  make test            → run all pytest tests with coverage"
	@echo "  make train-medical   → train BioBERT on medical data"
	@echo "  make train-legal     → train LegalBERT on legal data"
	@echo "  make evaluate        → run evaluation on test sets"
	@echo "  make api             → start FastAPI server"
	@echo "  make streamlit       → start Streamlit demo UI"
	@echo "  make clean           → remove cache and temp files"
	@echo ""

setup:
	python -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	./venv/bin/python -m spacy download en_core_web_sm
	./venv/bin/python -m nltk.downloader punkt averaged_perceptron_tagger
	@echo "✅ Setup complete. Activate with: source venv/bin/activate"

install:
	pip install --upgrade pip
	pip install -r requirements.txt
	python -m spacy download en_core_web_sm

lint:
	black src/ tests/
	isort src/ tests/
	flake8 src/ tests/ --max-line-length=100

test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

train-medical:
	python scripts/train.py --domain medical --config configs/config.yaml

train-legal:
	python scripts/train.py --domain legal --config configs/config.yaml

evaluate:
	python scripts/evaluate.py --config configs/config.yaml

api:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

streamlit:
	streamlit run src/api/streamlit_app.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage
