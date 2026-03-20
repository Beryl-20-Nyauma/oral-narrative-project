"""Business logic for upload operations."""

import logging
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import date
import uuid
import os

from config import get_settings
from app.models.narrative import Narrative, Theme

logger = logging.getLogger(__name__)

settings = get_settings()
STORAGE_DIR = Path(settings.storage_dir)

ALLOWED_VIDEO_FORMATS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
MAX_VIDEO_SIZE_MB = settings.max_upload_size_mb
MIN_DURATION_SEC = 2


async def process_upload(
    db: AsyncSession,
    video: UploadFile,
    title: str,
    narrator_name: str,
    location: str,
    language: str,
    themes: str,
    transcript: str
) -> Dict[str, Any]:
    """
    Process video upload and trigger Celery analysis pipeline.
    
    Args:
        db: Database session
        video: Uploaded video file
        title: Narrative title
        narrator_name: Name of storyteller
        location: Recording location
        language: Language code
        themes: Comma-separated themes
        transcript: Optional transcript
    
    Returns:
        Dict with narrative_id, status, and task_id
    """
    narrative_id = str(uuid.uuid4())
    
    _ensure_storage_dirs()
    
    video_path = STORAGE_DIR / "videos" / f"{narrative_id}.mp4"
    
    content = await video.read()
    
    validation_error = validate_video_upload(content, video.filename or "")
    if validation_error:
        return {
            "narrative_id": None,
            "status": "rejected",
            "error": validation_error
        }
    
    with open(video_path, "wb") as f:
        f.write(content)
    
    logger.info(f"Saved video to {video_path} ({len(content)} bytes)")
    
    theme_names = [t.strip() for t in themes.split(",") if t.strip()]
    theme_objs = await _get_or_create_themes(db, theme_names)
    
    narrative = Narrative(
        id=narrative_id,
        status="pending",
        title=title,
        narrator_name=narrator_name,
        location=location,
        language=language,
        duration_sec=0.0,
        date_recorded=date.today(),
        video_path=str(video_path),
        processing_progress=0,
        processing_stage="queued",
    )
    narrative.themes = theme_objs
    
    db.add(narrative)
    await db.commit()
    
    from app.core.tasks import process_video_task
    
    task = process_video_task.delay(
        narrative_id,
        str(video_path),
        {
            "title": title,
            "narrator_name": narrator_name,
            "location": location,
            "language": language,
            "themes": theme_names,
            "transcript": transcript,
        }
    )
    
    narrative.celery_task_id = task.id
    await db.commit()
    
    logger.info(f"Started Celery task {task.id} for narrative {narrative_id}")
    
    return {
        "narrative_id": narrative_id,
        "status": "pending",
        "task_id": task.id,
        "message": "Narrative uploaded. Processing queued.",
        "status_url": f"/api/narratives/{narrative_id}/status"
    }


def validate_video_upload(content: bytes, filename: str) -> Optional[str]:
    """
    Validate uploaded video file.
    
    Args:
        content: Raw file bytes
        filename: Original filename
    
    Returns:
        Error message if validation fails, None if valid
    """
    if not content:
        return "Empty file uploaded"
    
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > MAX_VIDEO_SIZE_MB:
        return f"File too large: {file_size_mb:.1f}MB (max {MAX_VIDEO_SIZE_MB}MB)"
    
    ext = os.path.splitext(filename)[1].lower()
    if ext and ext not in ALLOWED_VIDEO_FORMATS:
        return f"Invalid format: {ext}. Allowed: {', '.join(ALLOWED_VIDEO_FORMATS)}"
    
    video_signatures = [
        b'\x00\x00\x00\x1cftyp',
        b'\x00\x00\x00\x20ftyp',
        b'ftyp',
        b'\x1aE\xdf\xa3',
        b'RIFF',
        b'\x00\x00\x01\x00',
    ]
    
    is_valid_video = any(sig in content[:100] for sig in video_signatures)
    if not is_valid_video and len(content) > 1000:
        logger.warning(f"Video signature not recognized for {filename}")
    
    return None


def _ensure_storage_dirs():
    """Create storage directories if they don't exist."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "videos").mkdir(exist_ok=True)
    (STORAGE_DIR / "audio").mkdir(exist_ok=True)
    (STORAGE_DIR / "archives").mkdir(exist_ok=True)
    (STORAGE_DIR / "thumbnails").mkdir(exist_ok=True)


async def _get_or_create_themes(db: AsyncSession, theme_names: list) -> list:
    """Get or create theme objects."""
    themes = []
    for name in theme_names:
        result = await db.execute(select(Theme).where(Theme.name == name))
        theme = result.scalar_one_or_none()
        if not theme:
            theme = Theme(name=name)
            db.add(theme)
        themes.append(theme)
    await db.flush()
    return themes


async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get Celery task status.
    
    Args:
        task_id: Celery task ID
    
    Returns:
        Dict with task status info
    """
    from app.core.celery_app import celery_app
    
    result = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "error": str(result.result) if result.failed() else None,
    }


async def retry_failed_task(narrative_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Retry a failed processing task.
    
    Args:
        narrative_id: UUID of the narrative
        db: Database session
    
    Returns:
        Dict with new task info
    """
    nid = uuid.UUID(narrative_id) if isinstance(narrative_id, str) else narrative_id
    result = await db.execute(
        select(Narrative).where(Narrative.id == nid)
    )
    narrative = result.scalar_one_or_none()
    
    if not narrative:
        return {"error": "Narrative not found"}
    
    if narrative.status != "error":
        return {"error": f"Cannot retry: status is '{narrative.status}'"}
    
    if not narrative.video_path:
        return {"error": "No video path found"}
    
    from app.core.tasks import process_video_task
    
    narrative.status = "pending"
    narrative.processing_progress = 0
    narrative.processing_stage = "queued"
    narrative.processing_error = None
    
    task = process_video_task.delay(
        narrative_id,
        narrative.video_path,
        {
            "title": narrative.title,
            "narrator_name": narrative.narrator_name,
            "location": narrative.location or "",
            "language": narrative.language or "en",
            "themes": [t.name for t in narrative.themes] if narrative.themes else [],
            "transcript": "",
        }
    )
    
    narrative.celery_task_id = task.id
    await db.commit()
    
    return {
        "narrative_id": narrative_id,
        "task_id": task.id,
        "status": "retried",
        "message": "Processing restarted"
    }
