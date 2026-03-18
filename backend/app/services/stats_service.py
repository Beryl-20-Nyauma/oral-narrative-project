"""Business logic for statistics."""

from typing import Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.narrative import Narrative, NarratorProfile


async def calculate_stats(db: AsyncSession) -> Dict[str, Any]:
    """
    Calculate system-wide statistics.
    
    Args:
        db: Database session
    
    Returns:
        Dict with narrative counts, durations, emotion distribution
    """
    total_result = await db.execute(select(func.count(Narrative.id)))
    total_narratives = total_result.scalar() or 0
    
    complete_result = await db.execute(
        select(func.count(Narrative.id)).where(Narrative.status == "complete")
    )
    complete_count = complete_result.scalar() or 0
    
    processing_result = await db.execute(
        select(func.count(Narrative.id)).where(Narrative.status == "processing")
    )
    processing_count = processing_result.scalar() or 0
    
    duration_result = await db.execute(
        select(func.sum(Narrative.duration_sec)).where(Narrative.status == "complete")
    )
    total_duration = duration_result.scalar() or 0
    
    emotion_result = await db.execute(
        select(NarratorProfile.dominant_emotion, func.count(NarratorProfile.id))
        .join(Narrative)
        .where(Narrative.status == "complete")
        .group_by(NarratorProfile.dominant_emotion)
    )
    emotion_counts = {row[0]: row[1] for row in emotion_result.all() if row[0]}
    
    narrators_result = await db.execute(
        select(func.count(func.distinct(Narrative.narrator_name)))
        .where(Narrative.status == "complete")
    )
    unique_narrators = narrators_result.scalar() or 0
    
    return {
        "total_narratives": total_narratives,
        "complete": complete_count,
        "processing": processing_count,
        "total_duration_min": total_duration / 60,
        "emotion_distribution": emotion_counts,
        "unique_narrators": unique_narrators,
    }
