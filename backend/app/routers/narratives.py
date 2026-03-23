"""API route handlers for narratives."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.routers.auth import require_auth, require_admin
from app.models.narrative import Narrator, Narrative

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


@router.patch("/{narrative_id}/narrator")
async def assign_narrator(
    narrative_id: str,
    narrator_id: str,
    current_user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually assign a narrator to a narrative.
    
    Allows users to override auto-identification or correct mistakes.
    
    Args:
        narrative_id: UUID of narrative
        narrator_id: UUID of narrator to assign
        db: Database session
    
    Returns:
        Updated narrative with new narrator assignment
    """
    import uuid
    
    try:
        nid = uuid.UUID(narrative_id) if isinstance(narrative_id, str) else narrative_id
        narrator_uuid = uuid.UUID(narrator_id) if isinstance(narrator_id, str) else narrator_id
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    result = await db.execute(select(Narrative).where(Narrative.id == nid))
    narrative = result.scalar_one_or_none()
    
    if not narrative:
        raise HTTPException(status_code=404, detail="Narrative not found")
    
    result = await db.execute(select(Narrator).where(Narrator.id == narrator_uuid))
    narrator = result.scalar_one_or_none()
    
    if not narrator:
        raise HTTPException(status_code=404, detail="Narrator not found")
    
    narrative.narrator_id = narrator_uuid
    narrative.narrator_name = narrator.name
    await db.commit()
    
    return {
        "narrative_id": str(narrative.id),
        "narrator_id": str(narrator.id),
        "narrator_name": narrator.name,
        "message": f"Narrative assigned to {narrator.name}"
    }


@router.delete("/{narrative_id}")
async def delete_narrative(
    narrative_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Soft delete a narrative (Admin only).
    
    Args:
        narrative_id: UUID of narrative to delete
        current_user: Current authenticated admin user
        db: Database session
    
    Returns:
        Success message
    """
    try:
        nid = uuid.UUID(narrative_id) if isinstance(narrative_id, str) else narrative_id
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    result = await db.execute(select(Narrative).where(Narrative.id == nid))
    narrative = result.scalar_one_or_none()
    
    if not narrative:
        raise HTTPException(status_code=404, detail="Narrative not found")
    
    narrative.deleted_at = datetime.utcnow()
    await db.commit()
    
    return {
        "success": True,
        "message": f"Narrative '{narrative.title}' has been deleted (soft delete)"
    }
