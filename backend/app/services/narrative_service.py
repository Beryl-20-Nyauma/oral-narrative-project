"""Business logic for narrative operations."""

from typing import Dict, Any, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import uuid

from app.models.narrative import (
    Narrative, Theme, NarratorProfile, FacialAnalysis,
    VocalAnalysis, MultimodalFusion
)


async def fetch_narratives(
    db: AsyncSession,
    narrator: Optional[str] = None,
    emotion: Optional[str] = None,
    theme: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Fetch narratives with optional filtering.
    
    Args:
        db: Database session
        narrator: Filter by narrator name
        emotion: Filter by dominant emotion
        theme: Filter by theme
        limit: Max results
        offset: Pagination offset
    
    Returns:
        Dict with narratives list and pagination info
    """
    query = (
        select(Narrative)
        .options(selectinload(Narrative.themes))
        .options(selectinload(Narrative.narrator_profile))
        .where(Narrative.status == "complete")
    )
    
    count_query = select(Narrative.id).where(Narrative.status == "complete")
    
    if narrator:
        query = query.where(Narrative.narrator_name.ilike(f"%{narrator}%"))
        count_query = count_query.where(Narrative.narrator_name.ilike(f"%{narrator}%"))
    
    if emotion:
        query = (
            query.join(NarratorProfile)
            .where(NarratorProfile.dominant_emotion.ilike(f"%{emotion}%"))
        )
        count_query = (
            count_query.join(NarratorProfile)
            .where(NarratorProfile.dominant_emotion.ilike(f"%{emotion}%"))
        )
    
    if theme:
        query = query.join(Narrative.themes).where(Theme.name.ilike(f"%{theme}%"))
        count_query = count_query.join(Narrative.themes).where(Theme.name.ilike(f"%{theme}%"))
    
    result = await db.execute(count_query)
    total = len(result.all())
    
    query = query.order_by(Narrative.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    narratives = result.scalars().all()
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "narratives": [_narrative_to_summary(n) for n in narratives]
    }


async def fetch_narrative_by_id(db: AsyncSession, narrative_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single narrative by ID."""
    try:
        nid = uuid.UUID(narrative_id) if isinstance(narrative_id, str) else narrative_id
    except (ValueError, AttributeError):
        return None
    
    query = (
        select(Narrative)
        .options(selectinload(Narrative.themes))
        .options(selectinload(Narrative.transcript))
        .options(selectinload(Narrative.narrator_profile))
        .options(selectinload(Narrative.facial_analysis))
        .options(selectinload(Narrative.vocal_analysis))
        .options(selectinload(Narrative.multimodal_fusion))
        .where(Narrative.id == nid)
    )
    result = await db.execute(query)
    narrative = result.scalar_one_or_none()
    
    if not narrative:
        return None
    
    return _narrative_to_full_dict(narrative)


async def get_narrative_status(db: AsyncSession, narrative_id: str) -> Dict[str, Any]:
    """Get processing status of a narrative."""
    try:
        nid = uuid.UUID(narrative_id) if isinstance(narrative_id, str) else narrative_id
    except (ValueError, AttributeError):
        return {"narrative_id": narrative_id, "status": "not_found"}
    
    query = select(Narrative).where(Narrative.id == nid)
    result = await db.execute(query)
    narrative = result.scalar_one_or_none()
    
    if not narrative:
        return {"narrative_id": narrative_id, "status": "not_found"}
    
    return {
        "narrative_id": narrative_id,
        "status": narrative.status,
        "progress": {
            "percentage": narrative.processing_progress or 0,
            "stage": narrative.processing_stage or "unknown",
        },
        "error": narrative.processing_error,
        "task_id": narrative.celery_task_id,
        "created_at": narrative.created_at.isoformat() if narrative.created_at else None,
        "updated_at": narrative.updated_at.isoformat() if narrative.updated_at else None,
    }


async def get_timeline(db: AsyncSession, narrative_id: str) -> Dict[str, Any]:
    """Get emotion timeline for a narrative."""
    try:
        nid = uuid.UUID(narrative_id) if isinstance(narrative_id, str) else narrative_id
    except (ValueError, AttributeError):
        return {"status": "not_found"}
    
    query = (
        select(Narrative)
        .options(selectinload(Narrative.facial_analysis))
        .options(selectinload(Narrative.vocal_analysis))
        .options(selectinload(Narrative.multimodal_fusion))
        .where(Narrative.id == nid)
    )
    result = await db.execute(query)
    narrative = result.scalar_one_or_none()
    
    if not narrative:
        return {"status": "not_found"}
    
    if narrative.status != "complete":
        return {"status": "processing", "message": "Analysis not yet complete"}
    
    facial = narrative.facial_analysis
    vocal = narrative.vocal_analysis
    fusion = narrative.multimodal_fusion
    
    return {
        "narrative_id": narrative_id,
        "facial_emotions": facial.emotion_timeline if facial else [],
        "vocal_features": vocal.pitch_timeline if vocal else [],
        "unified_timeline": fusion.unified_emotion_timeline if fusion else [],
    }


async def get_profile(db: AsyncSession, narrative_id: str) -> Dict[str, Any]:
    """Get narrator profile for a narrative."""
    try:
        nid = uuid.UUID(narrative_id) if isinstance(narrative_id, str) else narrative_id
    except (ValueError, AttributeError):
        return {"status": "not_found"}
    
    query = (
        select(Narrative)
        .options(selectinload(Narrative.narrator_profile))
        .options(selectinload(Narrative.vocal_analysis))
        .options(selectinload(Narrative.multimodal_fusion))
        .where(Narrative.id == nid)
    )
    result = await db.execute(query)
    narrative = result.scalar_one_or_none()
    
    if not narrative:
        return {"status": "not_found"}
    
    if narrative.status != "complete":
        return {"status": "processing"}
    
    profile = narrative.narrator_profile
    vocal = narrative.vocal_analysis
    fusion = narrative.multimodal_fusion
    
    return {
        "narrative_id": narrative_id,
        "narrator_identity": {
            "estimated_age": profile.estimated_age if profile else None,
            "age_range": profile.age_range if profile else None,
            "gender": profile.gender if profile else None,
            "gender_confidence": profile.gender_confidence if profile else None,
            "dominant_emotion": profile.dominant_emotion if profile else None,
            "emotion_distribution": profile.emotion_distribution if profile else {},
        },
        "vocal_profile": {
            "mean_pitch_hz": vocal.mean_pitch_hz if vocal else None,
            "speech_rate_wpm": vocal.speech_rate_wpm if vocal else None,
            "vocal_emotion_indicators": vocal.vocal_emotion_indicators if vocal else {},
        } if vocal else {},
        "emotion_congruence": fusion.emotion_congruence if fusion else {},
    }


def _narrative_to_summary(narrative: Narrative) -> Dict[str, Any]:
    """Convert narrative to summary dict."""
    return {
        "id": str(narrative.id),
        "title": narrative.title,
        "narrator_name": narrative.narrator_name,
        "duration_sec": narrative.duration_sec,
        "dominant_emotion": narrative.narrator_profile.dominant_emotion if narrative.narrator_profile else None,
        "created_at": narrative.created_at.isoformat() if narrative.created_at else None,
        "themes": [t.name for t in narrative.themes] if narrative.themes else [],
    }


def _narrative_to_full_dict(narrative: Narrative) -> Dict[str, Any]:
    """Convert narrative to full dict."""
    return {
        "archive_id": str(narrative.id),
        "status": narrative.status,
        "created_at": narrative.created_at.isoformat() if narrative.created_at else None,
        "narrative_metadata": {
            "title": narrative.title,
            "narrator_name": narrative.narrator_name,
            "location": narrative.location,
            "language": narrative.language,
            "duration_sec": narrative.duration_sec,
            "date_recorded": narrative.date_recorded,
            "themes": [t.name for t in narrative.themes] if narrative.themes else [],
        },
        "transcript": {
            "text": narrative.transcript.text if narrative.transcript else None,
            "word_count": narrative.transcript.word_count if narrative.transcript else 0,
            "confidence": narrative.transcript.confidence if narrative.transcript else None,
        } if narrative.transcript else None,
        "narrator": {
            "estimated_age": narrative.narrator_profile.estimated_age if narrative.narrator_profile else None,
            "age_range": narrative.narrator_profile.age_range if narrative.narrator_profile else None,
            "gender": narrative.narrator_profile.gender if narrative.narrator_profile else None,
            "gender_confidence": narrative.narrator_profile.gender_confidence if narrative.narrator_profile else None,
            "dominant_emotion": narrative.narrator_profile.dominant_emotion if narrative.narrator_profile else None,
            "emotion_distribution": narrative.narrator_profile.emotion_distribution if narrative.narrator_profile else {},
        } if narrative.narrator_profile else None,
        "facial_analysis": {
            "emotion_timeline": narrative.facial_analysis.emotion_timeline if narrative.facial_analysis else [],
            "expression_timeline": narrative.facial_analysis.expression_timeline if narrative.facial_analysis else [],
            "narrator_profile": {
                "estimated_age": narrative.narrator_profile.estimated_age if narrative.narrator_profile else None,
                "age_range": narrative.narrator_profile.age_range if narrative.narrator_profile else None,
                "gender": narrative.narrator_profile.gender if narrative.narrator_profile else None,
                "gender_confidence": narrative.narrator_profile.gender_confidence if narrative.narrator_profile else None,
                "detection_confidence": narrative.narrator_profile.detection_confidence if narrative.narrator_profile else None,
                "dominant_emotion_overall": narrative.narrator_profile.dominant_emotion if narrative.narrator_profile else None,
                "emotion_distribution": narrative.narrator_profile.emotion_distribution if narrative.narrator_profile else {},
                "facial_action_units": narrative.narrator_profile.facial_action_units if narrative.narrator_profile else {},
            },
        } if narrative.facial_analysis else None,
        "vocal_analysis": {
            "voice_activity_segments": narrative.vocal_analysis.voice_activity_segments if narrative.vocal_analysis else [],
            "pitch_timeline": narrative.vocal_analysis.pitch_timeline if narrative.vocal_analysis else [],
            "vocal_features": {
                "mean_pitch_hz": narrative.vocal_analysis.mean_pitch_hz if narrative.vocal_analysis else None,
                "pitch_range_hz": {
                    "min": narrative.vocal_analysis.pitch_range_min_hz if narrative.vocal_analysis else None,
                    "max": narrative.vocal_analysis.pitch_range_max_hz if narrative.vocal_analysis else None,
                },
                "pitch_variability_std": narrative.vocal_analysis.pitch_variability_std if narrative.vocal_analysis else None,
                "speech_rate_wpm": narrative.vocal_analysis.speech_rate_wpm if narrative.vocal_analysis else None,
                "pause_count": narrative.vocal_analysis.pause_count if narrative.vocal_analysis else None,
                "mean_pause_duration_sec": narrative.vocal_analysis.mean_pause_duration_sec if narrative.vocal_analysis else None,
                "vocal_emotion_indicators": narrative.vocal_analysis.vocal_emotion_indicators if narrative.vocal_analysis else {},
            },
            "audio_quality": {
                "sample_rate": narrative.vocal_analysis.sample_rate if narrative.vocal_analysis else None,
                "snr_db": narrative.vocal_analysis.snr_db if narrative.vocal_analysis else None,
            },
        } if narrative.vocal_analysis else None,
        "multimodal_fusion": {
            "unified_emotion_timeline": narrative.multimodal_fusion.unified_emotion_timeline if narrative.multimodal_fusion else [],
            "emotion_congruence": narrative.multimodal_fusion.emotion_congruence if narrative.multimodal_fusion else {},
            "narrator_vector": narrative.multimodal_fusion.narrator_vector if narrative.multimodal_fusion else {},
            "grad_cam_highlights": narrative.multimodal_fusion.grad_cam_highlights if narrative.multimodal_fusion else {},
            "fusion_method": narrative.multimodal_fusion.fusion_method if narrative.multimodal_fusion else None,
        } if narrative.multimodal_fusion else None,
        "search_index": {
            "narrator_name": narrative.narrator_name,
            "themes": [t.name for t in narrative.themes] if narrative.themes else [],
            "dominant_emotions": [narrative.narrator_profile.dominant_emotion] if narrative.narrator_profile and narrative.narrator_profile.dominant_emotion else [],
            "keywords": [],
        },
    }
