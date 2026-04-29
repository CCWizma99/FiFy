import asyncio
import sys

# Windows-specific event loop policy for Playwright subprocesses
# This MUST be set before any loops are created or uvicorn starts
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
import time

from backend.database import init_db
from backend.routers import admin, products, search
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────
    loop = asyncio.get_running_loop()
    logger.info(f"Starting FiFy backend (Loop: {type(loop).__name__})…")
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} | Status: {response.status_code} | Duration: {duration:.2f}s")
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"Unhandled Exception: {str(exc)}\n{traceback.format_exc()}"
    logger.error(error_msg)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)}
    )

app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "fify-backend"}
