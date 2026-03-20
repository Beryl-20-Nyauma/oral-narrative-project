"""API route handlers for upload."""

from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_db

router = APIRouter(prefix="/api/narratives", tags=["upload"])


@router.post("/upload")
async def upload_narrative(
    video: UploadFile = File(...),
    title: str = "Untitled Narrative",
    narrator_name: str = "Anonymous",
    location: str = "",
    language: str = "en",
    themes: str = "",
    transcript: str = "",
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Upload a video narrative and trigger full multimodal analysis pipeline.
    
    Processing is handled by Celery workers for reliability and scalability.
    
    Args:
        video: Uploaded video file (mp4, mov, avi, mkv, webm)
        title: Narrative title
        narrator_name: Name of the storyteller
        location: Recording location
        language: Language code (default: en)
        themes: Comma-separated theme tags
        transcript: Optional transcript text
        db: Database session
    
    Returns:
        Dict with narrative_id, task_id, and status_url for tracking progress
    """
    from app.services.upload_service import process_upload
    return await process_upload(
        db=db,
        video=video,
        title=title,
        narrator_name=narrator_name,
        location=location,
        language=language,
        themes=themes,
        transcript=transcript
    )


@router.post("/retry/{narrative_id}")
async def retry_processing(
    narrative_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retry a failed processing task.
    
    Args:
        narrative_id: UUID of the failed narrative
        db: Database session
    
    Returns:
        Dict with new task_id and status
    """
    from app.services.upload_service import retry_failed_task
    return await retry_failed_task(narrative_id, db)
