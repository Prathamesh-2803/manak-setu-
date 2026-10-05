from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import ask, health, lint, map as mapper, search, stats

settings = get_settings()

app = FastAPI(
    title="Manak Setu API",
    description="AI-powered recommendation engine for applicable Indian Standards (PS SIH26108)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(search.router)
app.include_router(ask.router)
app.include_router(lint.router)
app.include_router(stats.router)
app.include_router(mapper.router)


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
