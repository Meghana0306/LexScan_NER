"""
run_api.py — Start the FastAPI server
Usage:
    python run_api.py
Then open:
    http://localhost:8000/docs   ← Swagger UI (test the API here)
    http://localhost:8000/health ← Health check
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,       # auto-reload on code changes
        log_level="info",
    )
