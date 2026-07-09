"""
MindBridge AI — FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.api.v1.router import api_router
from app.ws.chat_ws import router as ws_router
from app.services.embedder import embedder
from app.services.classifier_service import classifier_service
from app.services.ai_service import _initialize_gemini
from app.services.memory_service import memory_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    logger.info("🚀 MindBridge AI starting up...")

    # ── Sentence Transformer + corpus ────────────────────────────────────────
    try:
        embedder.initialize()
        embedder.load_corpus(settings.CORPUS_PATH)
    except Exception as e:
        logger.error(f"Failed to initialize embedder: {e}")

    # ── Trained classifier (non-fatal — falls back to cosine similarity) ─────
    try:
        classifier_service.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize classifier: {e}")

    # ── Gemini API ────────────────────────────────────────────────────────────
    try:
        _initialize_gemini()
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")

    # ── Redis memory (non-fatal — chat still works without memory) ───────────
    try:
        await memory_service.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize MemoryService: {e}")

    logger.info("✅ MindBridge AI ready!")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("👋 MindBridge AI shutting down...")
    await memory_service.close()


app = FastAPI(
    title="MindBridge AI",
    description="Mental Health Support Platform — IEEE ICDSBS 2025 Research Implementation",
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "name": "MindBridge AI",
        "version": "2.1.0",
        "status": "running",
        "corpus_loaded": embedder._loaded,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """
    Health check endpoint.
    Returns status of all major subsystems so the review panel can verify
    each component is operational at a glance.
    """
    memory_ok = await memory_service.ping()

    return {
        "status": "healthy",
        # ── NLP / ML ─────────────────────────────────────────────────────────
        "embedder_loaded"      : embedder._loaded,
        "corpus_size"          : len(embedder.corpus_data),
        "classifier_loaded"    : classifier_service._loaded,
        "classifier_categories": (
            classifier_service.categories if classifier_service._loaded else []
        ),
        # ── Memory ───────────────────────────────────────────────────────────
        "redis_connected"      : memory_ok,
        "memory_ttl_hours"     : settings.MEMORY_TTL_SECONDS // 3600,
    }
