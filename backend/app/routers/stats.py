"""API route handlers for statistics."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_db

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def get_system_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get system-wide statistics.
    
    Args:
        db: Database session
    
    Returns:
        Dict with narrative counts, durations, emotion distribution
    """
    from app.services.stats_service import calculate_stats
    return await calculate_stats(db)
