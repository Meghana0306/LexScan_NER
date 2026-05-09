"""
API Schemas — Pydantic models for request/response validation
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


# ── Request schemas ────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Text to extract entities from",
        examples=["The patient was diagnosed with diabetes mellitus type 2."]
    )
    domain: str = Field(
        default="auto",
        description="Domain: 'medical', 'legal', 'general', or 'auto'",
        examples=["medical"]
    )

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        allowed = {"medical", "legal", "general", "auto"}
        if v not in allowed:
            raise ValueError(f"domain must be one of {allowed}")
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("text cannot be empty or whitespace")
        return v.strip()


class BatchPredictRequest(BaseModel):
    texts: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of texts to process (max 50)",
    )
    domain: str = Field(
        default="auto",
        description="Domain applied to all texts",
    )

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        allowed = {"medical", "legal", "general", "auto"}
        if v not in allowed:
            raise ValueError(f"domain must be one of {allowed}")
        return v


# ── Response schemas ───────────────────────────────────────────────────────
class Entity(BaseModel):
    text: str       = Field(..., description="The entity text")
    label: str      = Field(..., description="Entity type e.g. DISEASE, PERSON")
    start: int      = Field(..., description="Start character index in original text")
    end: int        = Field(..., description="End character index in original text")
    confidence: float = Field(..., description="Model confidence score 0-1")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "text": "diabetes mellitus",
                "label": "DISEASE",
                "start": 30,
                "end": 47,
                "confidence": 0.98
            }]
        }
    }


class PredictResponse(BaseModel):
    text: str
    domain: str
    entities: List[Entity]
    entity_count: int
    processing_time_seconds: float


class BatchResult(BaseModel):
    text: str
    domain: str
    entities: List[Dict[str, Any]]
    entity_count: int
    error: Optional[str] = None


class BatchPredictResponse(BaseModel):
    results: List[BatchResult]
    total_texts: int
    processing_time_seconds: float


class HealthResponse(BaseModel):
    status: str
    models_loaded: List[str]
    version: str


class ModelsResponse(BaseModel):
    models: Dict[str, Dict[str, Any]]
