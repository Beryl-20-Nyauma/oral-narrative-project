"""API route handlers for upload."""

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_db

router = APIRouter(prefix="/api/narratives", tags=["upload"])


@router.post("/upload")
async def upload_narrative(
    background_tasks: BackgroundTasks,
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
    
    Args:
        background_tasks: FastAPI background task manager
        video: Uploaded video file
        title: Narrative title
        narrator_name: Name of the storyteller
        location: Recording location
        language: Language code (default: en)
        themes: Comma-separated theme tags
        transcript: Optional transcript text
        db: Database session
    
    Returns:
        Dict with narrative_id and status
    """
    from app.services.upload_service import process_upload
    return await process_upload(
        db=db,
        background_tasks=background_tasks,
        video=video,
        title=title,
        narrator_name=narrator_name,
        location=location,
        language=language,
        themes=themes,
        transcript=transcript
    )
