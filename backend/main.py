"""
backend/main.py
FastAPI application entry point.
Mounts all routers and starts APScheduler on startup.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routers import admin, products, search
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────
    logger.info("Starting FiFy backend…")
    init_db()
    logger.info("SQLite DB initialised.")
    yield
    # ── Shutdown ─────────────────────────────────────────
    logger.info("Shutting down FiFy backend.")


app = FastAPI(
    title="FiFy — Fashion RAG Search API",
    description="Multimodal fashion search via CLIP embeddings and Qdrant vector search.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "fify-backend"}
