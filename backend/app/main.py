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
from app.services.ai_service import _initialize_gemini

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 MindBridge AI starting up...")

    # Initialize AI components (heavy — load once)
    try:
        embedder.initialize()
        embedder.load_corpus(settings.CORPUS_PATH)
    except Exception as e:
        logger.error(f"Failed to initialize embedder: {e}")

    try:
        _initialize_gemini()
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")

    logger.info("✅ MindBridge AI ready!")
    yield

    logger.info("👋 MindBridge AI shutting down...")


app = FastAPI(
    title="MindBridge AI",
    description="Mental Health Support Platform — IEEE ICDSBS 2025 Research Implementation",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "name": "MindBridge AI",
        "version": "2.0.0",
        "status": "running",
        "corpus_loaded": embedder._loaded,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "embedder_loaded": embedder._loaded,
        "corpus_size": len(embedder.corpus_data),
    }
