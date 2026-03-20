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

from config import get_settings

settings = get_settings()

STORAGE_DIR = Path(settings.storage_dir)
STORAGE_DIR.mkdir(exist_ok=True)
(STORAGE_DIR / "videos").mkdir(exist_ok=True)
(STORAGE_DIR / "audio").mkdir(exist_ok=True)
(STORAGE_DIR / "archives").mkdir(exist_ok=True)
(STORAGE_DIR / "thumbnails").mkdir(exist_ok=True)


async def init_db():
    """Initialize database connection and create tables."""
    from app.core.database import init_db as db_init, async_session_factory
    
    if async_session_factory is None:
        print("⚠️ No DATABASE_URL configured - running without database")
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
        from app.services.rate_limit_service import init_rate_limiter as _init
        _init(settings.redis_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.logging_config import setup_logging
    setup_logging()
    
    await init_db()
    await init_rate_limiter()
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
        "status": "active"
    }


from app.routers import narratives, upload, search, stats, queue
from app.routers.queue import router as queue_router

app.include_router(narratives.router)
app.include_router(upload.router)
app.include_router(search.router)
app.include_router(stats.router)
app.include_router(queue_router)

try:
    from app.routers import auth, narrators
    if auth:
        app.include_router(auth.router)
    if narrators:
        app.include_router(narrators.router)
except ImportError:
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
