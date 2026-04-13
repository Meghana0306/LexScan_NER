# Multi-Domain Entity Extraction for Legal and Medical Documents

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.2-orange)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Transformers-yellow)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)
![MLflow](https://img.shields.io/badge/MLflow-2.11-blue)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

A production-grade Named Entity Recognition (NER) system for extracting entities from Legal and Medical documents using deep learning (BioBERT, LegalBERT, SpanBERT, BiLSTM-CRF) with a full MLOps pipeline.

---

## Project Structure

```
ner_project/
├── configs/
│   └── config.yaml           # All hyperparameters and settings
├── data/
│   ├── raw/                  # Raw datasets (tracked by DVC)
│   │   ├── legal/
│   │   └── medical/
│   ├── processed/            # Tokenized + tagged data
│   ├── splits/               # Train / val / test splits
│   └── annotations/         # Custom annotated docs (Label Studio)
├── src/
│   ├── data/                 # Dataset loading, preprocessing
│   ├── models/               # BioBERT, LegalBERT, SpanBERT, BiLSTM-CRF
│   ├── training/             # Training loops, callbacks
│   ├── evaluation/           # seqeval metrics, reports
│   ├── api/                  # FastAPI application
│   └── utils/                # Config loader, logging, helpers
├── notebooks/                # EDA and experiment notebooks
├── scripts/                  # CLI scripts (train, evaluate, preprocess)
├── tests/                    # pytest unit + integration tests
├── docker/                   # Dockerfile, docker-compose
├── .github/workflows/        # CI/CD pipelines
├── dvc.yaml                  # DVC pipeline definition
├── setup.py                  # Package installation
├── requirements.txt          # All dependencies
└── README.md
```

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/yourname/multi-domain-ner.git
cd multi-domain-ner

# 2. Run the setup script (creates venv, installs deps, inits git+dvc)
bash setup_project.sh

# 3. Activate environment
source venv/bin/activate

# 4. Edit .env with your values
nano .env

# 5. Verify everything is set up
python scripts/verify_setup.py
```

---

## Training

```bash
# Train medical NER (BioBERT)
python scripts/train.py --domain medical

# Train legal NER (LegalBERT)
python scripts/train.py --domain legal

# Run full DVC pipeline (all stages in order)
dvc repro
```

---

## Evaluation

```bash
python scripts/evaluate.py --domain medical
python scripts/evaluate.py --domain legal
```

---

## API

```bash
# Start the FastAPI server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# API docs available at:
# http://localhost:8000/docs
```

---

## Demo UI

```bash
streamlit run src/api/streamlit_app.py
```

---

## Docker

```bash
docker-compose up --build
```

---

## Models Used

| Model | Domain | Task |
|-------|--------|------|
| BioBERT (dmis-lab/biobert-base-cased-v1.2) | Medical | NER fine-tuning |
| LegalBERT (nlpaueb/legal-bert-base-uncased) | Legal | NER fine-tuning |
| SpanBERT (SpanBERT/spanbert-base-cased) | Both | Span extraction |
| BiLSTM-CRF | Both | Baseline |

---

## Entity Types

**Medical:** DISEASE, DRUG, DOSAGE, SYMPTOM, ANATOMY, PROCEDURE, LAB_VALUE, GENE_PROTEIN, TEMPORAL, PATIENT_ID

**Legal:** PARTY, JUDGE, COURT, STATUTE, CASE_NUM, JURISDICTION, CONTRACT_CLAUSE, LEGAL_ROLE, OBLIGATION, DATE, PENALTY, LOCATION

---

## MLOps

- **Experiment tracking:** MLflow
- **Data versioning:** DVC
- **Model registry:** MLflow Model Registry
- **Monitoring:** Prometheus + Grafana
- **CI/CD:** GitHub Actions
