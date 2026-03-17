"""Business logic for upload operations."""

from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import uuid
import json
import asyncio

from config import get_settings
from app.models.narrative import (
    Narrative, Theme, Transcript, NarratorProfile,
    FacialAnalysis, VocalAnalysis, MultimodalFusion
)

settings = get_settings()
STORAGE_DIR = Path(settings.storage_dir)


async def process_upload(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    video: UploadFile,
    title: str,
    narrator_name: str,
    location: str,
    language: str,
    themes: str,
    transcript: str
) -> Dict[str, Any]:
    """
    Process video upload and trigger analysis pipeline.
    
    Args:
        db: Database session
        background_tasks: FastAPI background task manager
        video: Uploaded video file
        title: Narrative title
        narrator_name: Name of storyteller
        location: Recording location
        language: Language code
        themes: Comma-separated themes
        transcript: Optional transcript
    
    Returns:
        Dict with narrative_id and status
    """
    narrative_id = str(uuid.uuid4())
    
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "videos").mkdir(exist_ok=True)
    (STORAGE_DIR / "audio").mkdir(exist_ok=True)
    (STORAGE_DIR / "archives").mkdir(exist_ok=True)
    (STORAGE_DIR / "thumbnails").mkdir(exist_ok=True)
    
    video_path = STORAGE_DIR / "videos" / f"{narrative_id}.mp4"
    content = await video.read()
    with open(video_path, "wb") as f:
        f.write(content)
    
    theme_names = [t.strip() for t in themes.split(",") if t.strip()]
    theme_objs = await _get_or_create_themes(db, theme_names)
    
    narrative = Narrative(
        id=narrative_id,
        status="processing",
        title=title,
        narrator_name=narrator_name,
        location=location,
        language=language,
        duration_sec=0.0,
        date_recorded=datetime.now(timezone.utc).date().isoformat(),
        video_path=str(video_path),
    )
    narrative.themes = theme_objs
    
    db.add(narrative)
    await db.commit()
    
    background_tasks.add_task(
        run_analysis_pipeline,
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
    
    return {
        "narrative_id": narrative_id,
        "status": "processing",
        "message": "Narrative uploaded. Multimodal analysis in progress.",
        "estimated_completion_sec": 30
    }


async def _get_or_create_themes(db: AsyncSession, theme_names: list) -> list:
    """Get or create theme objects."""
    from app.models.narrative import Theme
    
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


async def run_analysis_pipeline(
    narrative_id: str,
    video_path: str,
    metadata: Dict
) -> None:
    """
    Run full multimodal analysis pipeline.
    
    Args:
        narrative_id: UUID of narrative
        video_path: Path to video file
        metadata: Narrative metadata
    """
    from app.core.database import async_session_factory
    
    if async_session_factory is None:
        return
    
    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(Narrative).where(Narrative.id == narrative_id)
            )
            narrative = result.scalar_one_or_none()
            
            if not narrative:
                return
            
            await asyncio.sleep(1)
            
            facial_data = _analyze_facial_features(video_path)
            await asyncio.sleep(1)
            
            audio_path = video_path.replace("/videos/", "/audio/").replace(".mp4", ".wav")
            audio_data = _analyze_audio_features(audio_path)
            await asyncio.sleep(1)
            
            fusion_data = _fuse_multimodal_features(
                facial_data, audio_data, metadata.get("transcript", "")
            )
            await asyncio.sleep(0.5)
            
            profile_data = facial_data["narrator_profile"]
            narrator_profile = NarratorProfile(
                narrative_id=narrative_id,
                identity_hash=f"hash-{narrative_id}",
                estimated_age=profile_data["estimated_age"],
                age_range=profile_data["age_range"],
                gender=profile_data["gender"],
                gender_confidence=profile_data["gender_confidence"],
                detection_confidence=profile_data["detection_confidence"],
                dominant_emotion=profile_data["dominant_emotion_overall"],
                emotion_distribution=profile_data["emotion_distribution"],
                facial_action_units=profile_data["facial_action_units"],
            )
            db.add(narrator_profile)
            
            facial_analysis = FacialAnalysis(
                narrative_id=narrative_id,
                emotion_timeline=facial_data["emotion_timeline"],
                expression_timeline=facial_data["expression_timeline"],
                grad_cam_path=facial_data.get("grad_cam_path"),
            )
            db.add(facial_analysis)
            
            vocal_features = audio_data["vocal_features"]
            vocal_analysis = VocalAnalysis(
                narrative_id=narrative_id,
                voice_activity_segments=audio_data["voice_activity_segments"],
                pitch_timeline=audio_data["pitch_timeline"],
                mean_pitch_hz=vocal_features["mean_pitch_hz"],
                pitch_range_min_hz=vocal_features["pitch_range_hz"]["min"],
                pitch_range_max_hz=vocal_features["pitch_range_hz"]["max"],
                pitch_variability_std=vocal_features["pitch_variability_std"],
                speech_rate_wpm=vocal_features["speech_rate_wpm"],
                pause_count=vocal_features["pause_count"],
                mean_pause_duration_sec=vocal_features["mean_pause_duration_sec"],
                sample_rate=audio_data["audio_quality"]["sample_rate"],
                snr_db=audio_data["audio_quality"]["snr_db"],
                vocal_emotion_indicators=vocal_features["vocal_emotion_indicators"],
            )
            db.add(vocal_analysis)
            
            multimodal_fusion = MultimodalFusion(
                narrative_id=narrative_id,
                unified_emotion_timeline=fusion_data["unified_emotion_timeline"],
                emotion_congruence=fusion_data["emotion_congruence"],
                narrator_vector=fusion_data["narrator_vector"],
                grad_cam_highlights=fusion_data["grad_cam_highlights"],
                fusion_method=fusion_data["fusion_method"],
            )
            db.add(multimodal_fusion)
            
            if metadata.get("transcript"):
                transcript = Transcript(
                    narrative_id=narrative_id,
                    text=metadata["transcript"],
                    word_count=len(metadata["transcript"].split()),
                    asr_model="manual",
                    confidence=1.0,
                )
                db.add(transcript)
            
            narrative.status = "complete"
            narrative.duration_sec = 14.8
            
            await db.commit()
            
        except Exception as e:
            narrative.status = "error"
            await db.commit()
            raise


def _analyze_facial_features(video_path: str) -> Dict[str, Any]:
    """Placeholder for facial analysis."""
    from app.services.facial_service import analyze_facial_features
    return analyze_facial_features(video_path)


def _analyze_audio_features(audio_path: str) -> Dict[str, Any]:
    """Placeholder for audio analysis."""
    from app.services.audio_service import analyze_audio_features
    return analyze_audio_features(audio_path)


def _fuse_multimodal_features(facial_data: Dict, audio_data: Dict, transcript: str) -> Dict[str, Any]:
    """Placeholder for multimodal fusion."""
    from app.services.fusion_service import fuse_multimodal_features
    return fuse_multimodal_features(facial_data, audio_data, transcript)
