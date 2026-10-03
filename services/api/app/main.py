from fastapi import FastAPI

from app.config import get_settings
from app.routers import health

settings = get_settings()

app = FastAPI(
    title="Manak Setu API",
    description="AI-powered recommendation engine for applicable Indian Standards (PS SIH26108)",
    version="0.1.0",
)

app.include_router(health.router, tags=["health"])


@app.get("/")
def root() -> dict:
    return {
        "service": "Manak Setu API",
        "status": "alive",
        "docs": "/docs",
        "stages": [
            "language",
            "decompose",
            "retrieve",
            "rerank",
            "graph",
            "version_guard",
            "certification",
            "guardrail",
        ],
    }
