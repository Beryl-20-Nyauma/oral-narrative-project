"""
Oral Narrative Preservation System - FastAPI Backend
Multimodal analysis: video, audio, facial features, emotions
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path
import os
import logging

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

STORAGE_DIR = Path(settings.storage_dir)
STORAGE_DIR.mkdir(exist_ok=True)
(STORAGE_DIR / "videos").mkdir(exist_ok=True)
(STORAGE_DIR / "audio").mkdir(exist_ok=True)
(STORAGE_DIR / "archives").mkdir(exist_ok=True)
(STORAGE_DIR / "thumbnails").mkdir(exist_ok=True)

if settings.use_sqlite:
    Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)


def log_startup_info():
    """Log startup configuration."""
    from app.core.database import get_database_type
    
    db_type = get_database_type()
    async_mode = "enabled" if settings.async_processing and settings.redis_url else "disabled"
    
    print(f"\n{'='*60}")
    print(f"  {settings.app_name} v{settings.app_version}")
    print(f"{'='*60}")
    print(f"  Database: {db_type}")
    print(f"  Redis: {'connected' if settings.redis_url else 'not configured'}")
    print(f"  Async processing: {async_mode}")
    print(f"  Whisper model: {settings.whisper_model}")
    print(f"  Facial analysis: {'enabled' if settings.enable_facial_analysis else 'disabled'}")
    print(f"  Audio analysis: {'enabled' if settings.enable_audio_analysis else 'disabled'}")
    print(f"  Transcription: {'enabled' if settings.enable_transcription else 'disabled'}")
    if settings.lightweight_mode:
        print(f"  Mode: LIGHTWEIGHT (some ML features disabled)")
    print(f"{'='*60}\n")
    
    logger.info(f"Starting {settings.app_name} with database={db_type}, async={async_mode}")


async def init_db():
    """Initialize database connection and create tables."""
    from app.core.database import init_db as db_init, async_session_factory, get_database_type
    
    if async_session_factory is None:
        print("⚠️ No database configured")
        return
    
    await db_init()
    
    from app.core.seed import seed_database, is_database_seeded
    async with async_session_factory() as db:
        if not await is_database_seeded(db):
            print("🌱 Seeding sample data...")
            count = await seed_database(db)
            print(f"✅ Seeded {count} sample narratives")


async def init_rate_limiter():
    """Initialize rate limiter with Redis."""
    if settings.redis_url:
        try:
            from app.services.rate_limit_service import init_rate_limiter as _init
            _init(settings.redis_url)
            logger.info("Rate limiter initialized")
        except Exception as e:
            logger.warning(f"Rate limiter initialization failed: {e}")


async def init_ml_services():
    """Pre-initialize ML services if enabled."""
    if settings.lightweight_mode:
        logger.info("Lightweight mode - skipping ML pre-initialization")
        return
    
    if settings.enable_transcription:
        try:
            from app.services.transcription_service import WhisperTranscriber
            WhisperTranscriber.configure_from_settings()
            logger.info(f"Whisper configured: {settings.whisper_model}")
        except Exception as e:
            logger.warning(f"Transcription service initialization deferred: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.logging_config import setup_logging
    setup_logging()
    
    log_startup_info()
    await init_db()
    await init_rate_limiter()
    await init_ml_services()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Multimodal AI system for capturing and archiving oral narratives",
    version=settings.app_version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api")
async def api_root():
    return {
        "message": "Oral Narrative Preservation System API",
        "version": settings.app_version,
        "status": "active",
        "database": "sqlite" if settings.use_sqlite else "postgresql",
        "async_processing": settings.async_processing and bool(settings.redis_url)
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    from app.core.database import get_database_type
    return {
        "status": "healthy",
        "database": get_database_type(),
        "redis": "connected" if settings.redis_url else "not_configured"
    }


from app.routers import narratives, upload, search, stats

app.include_router(narratives)
app.include_router(upload)
app.include_router(search)
app.include_router(stats)

if settings.async_processing and settings.redis_url:
    try:
        from app.routers import queue
        app.include_router(queue)
        logger.info("Queue router enabled")
    except ImportError:
        logger.warning("Queue router not available")

try:
    from app.routers import auth, narrators
    if auth:
        app.include_router(auth)
    if narrators:
        app.include_router(narrators)
except ImportError:
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
