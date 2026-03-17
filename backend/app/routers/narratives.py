"""API route handlers for narratives."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from app.core.database import get_db

router = APIRouter(prefix="/api/narratives", tags=["narratives"])


@router.get("")
async def list_narratives(
    narrator: Optional[str] = None,
    emotion: Optional[str] = None,
    theme: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all archived narratives with optional filtering.
    
    Args:
        narrator: Filter by narrator name
        emotion: Filter by dominant emotion
        theme: Filter by theme tag
        limit: Max results to return
        offset: Pagination offset
        db: Database session
    
    Returns:
        Dict with narratives list and pagination info
    """
    from app.services.narrative_service import fetch_narratives
    return await fetch_narratives(db, narrator, emotion, theme, limit, offset)


@router.get("/{narrative_id}")
async def get_narrative(
    narrative_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get complete archive entry for a narrative.
    
    Args:
        narrative_id: UUID of the narrative
        db: Database session
    
    Returns:
        Complete narrative data
    """
    from app.services.narrative_service import fetch_narrative_by_id
    narrative = await fetch_narrative_by_id(db, narrative_id)
    if not narrative:
        raise HTTPException(status_code=404, detail="Narrative not found")
    return narrative


@router.get("/{narrative_id}/status")
async def get_processing_status(
    narrative_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Check processing status of a narrative."""
    from app.services.narrative_service import get_narrative_status
    return await get_narrative_status(db, narrative_id)


@router.get("/{narrative_id}/emotion-timeline")
async def get_emotion_timeline(
    narrative_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get synchronized emotion timeline for a narrative."""
    from app.services.narrative_service import get_timeline
    return await get_timeline(db, narrative_id)


@router.get("/{narrative_id}/narrator-profile")
async def get_narrator_profile(
    narrative_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get extracted narrator identity and vocal profile."""
    from app.services.narrative_service import get_profile
    return await get_profile(db, narrative_id)
