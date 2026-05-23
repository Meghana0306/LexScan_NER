"""
run_api.py — Start the FastAPI server
Usage:
    python run_api.py
Then open:
    http://localhost:8000/docs   ← Swagger UI (test the API here)
    http://localhost:8000/health ← Health check
"""

import os

import uvicorn

if __name__ == "__main__":
    reload = os.getenv("API_RELOAD", "0").lower() in ("1", "true", "yes")
    uvicorn.run(
        "src.api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=reload,
        log_level="info",
    )
