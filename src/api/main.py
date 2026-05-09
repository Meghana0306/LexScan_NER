"""
Multi-Domain NER — FastAPI Server
Endpoints:
  POST /predict        — predict entities from text
  POST /predict/batch  — predict on multiple texts
  GET  /health         — health check
  GET  /models         — list loaded models
  GET  /docs           — auto-generated Swagger UI
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    PredictRequest, PredictResponse,
    BatchPredictRequest, BatchPredictResponse,
    HealthResponse, ModelsResponse,
)
from src.api.predictor import NERPredictor

logger = logging.getLogger(__name__)

# ── Global predictor instance ──────────────────────────────────────────────
predictor: NERPredictor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup, clean up on shutdown."""
    global predictor
    logger.info("Loading NER models...")
    predictor = NERPredictor()
    predictor.load_all_models()
    logger.info("All models loaded. API ready.")
    yield
    logger.info("Shutting down...")


# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Multi-Domain NER API",
    description="""
## Named Entity Recognition for Legal & Medical Documents

Extract entities from text across 3 domains:

- **Medical** — DISEASE, CHEMICAL, DRUG, SYMPTOM, PROCEDURE, ANATOMY
- **Legal**   — PERSON, ORG, COURT, DATE, LAW, CASE, LOCATION  
- **General** — PER, ORG, LOC, MISC

### Usage
1. Set `domain` to `medical`, `legal`, or `general`
2. Or use `auto` to let the API detect the domain automatically
3. Use `/predict/batch` for multiple texts at once
    """,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Check if the API and all models are running."""
    loaded = predictor.get_loaded_models() if predictor else []
    return HealthResponse(
        status="healthy" if loaded else "loading",
        models_loaded=loaded,
        version="1.0.0",
    )


@app.get("/models", response_model=ModelsResponse, tags=["System"])
async def list_models():
    """List all available models and their entity types."""
    return ModelsResponse(
        models={
            "medical": {
                "model": "BioBERT (dmis-lab/biobert-base-cased-v1.2)",
                "entities": ["DISEASE", "CHEMICAL", "DRUG", "SYMPTOM", "PROCEDURE", "ANATOMY", "AGE", "GENDER", "FINDING"],
                "description": "Trained on NCBI Disease + BC5CDR corpus",
                "test_f1": 0.8621,
            },
            "legal": {
                "model": "LegalBERT (nlpaueb/legal-bert-base-uncased)",
                "entities": ["PERSON", "ORG", "COURT", "DATE", "LAW", "CASE", "LOCATION"],
                "description": "Trained on synthetic legal corpus",
                "test_f1": 1.0000,
            },
            "general": {
                "model": "DistilBERT (distilbert-base-uncased)",
                "entities": ["PER", "ORG", "LOC", "MISC"],
                "description": "Trained on CoNLL-2003",
                "test_f1": 0.8958,
            },
        }
    )


@app.post("/predict", response_model=PredictResponse, tags=["NER"])
async def predict(request: PredictRequest):
    """
    Extract named entities from a single text.
    
    - **text**: Input text (max 10,000 characters)
    - **domain**: `medical`, `legal`, `general`, or `auto`
    """
    if not predictor:
        raise HTTPException(status_code=503, detail="Models not loaded yet")

    start = time.time()

    # Auto-detect domain if not specified
    domain = request.domain
    if domain == "auto":
        domain = predictor.detect_domain(request.text)

    try:
        entities = predictor.predict(request.text, domain)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")

    elapsed = round(time.time() - start, 3)

    return PredictResponse(
        text=request.text,
        domain=domain,
        entities=entities,
        entity_count=len(entities),
        processing_time_seconds=elapsed,
    )


@app.post("/predict/batch", response_model=BatchPredictResponse, tags=["NER"])
async def predict_batch(request: BatchPredictRequest):
    """
    Extract named entities from multiple texts at once.
    
    - **texts**: List of texts (max 50)
    - **domain**: Same domain applied to all texts
    """
    if not predictor:
        raise HTTPException(status_code=503, detail="Models not loaded yet")

    if len(request.texts) > 50:
        raise HTTPException(status_code=400, detail="Max 50 texts per batch")

    start = time.time()
    results = []

    for text in request.texts:
        domain = request.domain
        if domain == "auto":
            domain = predictor.detect_domain(text)
        try:
            entities = predictor.predict(text, domain)
            results.append({
                "text": text,
                "domain": domain,
                "entities": entities,
                "entity_count": len(entities),
            })
        except Exception as e:
            results.append({
                "text": text,
                "domain": domain,
                "entities": [],
                "entity_count": 0,
                "error": str(e),
            })

    elapsed = round(time.time() - start, 3)
    return BatchPredictResponse(
        results=results,
        total_texts=len(request.texts),
        processing_time_seconds=elapsed,
    )
