"""Celery tasks for video processing."""

import logging
from typing import Dict, Any, Optional
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.core.celery_app import celery_app
from app.core.database import async_session_factory
from app.models.narrative import (
    Narrative, Transcript, NarratorProfile,
    FacialAnalysis, VocalAnalysis, MultimodalFusion
)

logger = logging.getLogger(__name__)


class ProcessingProgress:
    """Track processing progress for status updates."""
    
    def __init__(self, narrative_id: str):
        self.narrative_id = narrative_id
        self.progress = 0
        self.stage = "initializing"
        self.error: Optional[str] = None
    
    def update(self, progress: int, stage: str):
        """Update progress (0-100)."""
        self.progress = progress
        self.stage = stage
        logger.info(f"Narrative {self.narrative_id}: {stage} ({progress}%)")
    
    def set_error(self, error: str):
        """Set error state."""
        self.error = error
        logger.error(f"Narrative {self.narrative_id}: ERROR - {error}")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_video_task(
    self,
    narrative_id: str,
    video_path: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process video with full multimodal analysis pipeline.
    
    Args:
        narrative_id: UUID of the narrative
        video_path: Path to uploaded video file
        metadata: Narrative metadata (title, narrator_name, language, etc.)
    
    Returns:
        Dict with processing results
    """
    logger.info(f"Starting video processing for narrative {narrative_id}")
    
    try:
        return asyncio.run(_process_video_async(narrative_id, video_path, metadata))
    except Exception as e:
        logger.exception(f"Video processing failed for narrative {narrative_id}")
        _update_narrative_status(narrative_id, "error", str(e))
        raise self.retry(exc=e)


async def _process_video_async(
    narrative_id: str,
    video_path: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Async video processing implementation."""
    
    if async_session_factory is None:
        raise RuntimeError("Database not configured")
    
    progress = ProcessingProgress(narrative_id)
    results = {
        "narrative_id": narrative_id,
        "stages_completed": [],
        "stages_failed": [],
        "warnings": []
    }
    
    async with async_session_factory() as db:
        try:
            narrative = await _get_narrative(db, narrative_id)
            if not narrative:
                raise ValueError(f"Narrative {narrative_id} not found")
            
            _update_narrative_status_sync(db, narrative, "processing", progress=0, stage="starting")
            
            audio_path = video_path.replace("/videos/", "/audio/").replace(".mp4", ".wav")
            
            progress.update(5, "extracting_audio")
            audio_extracted = await _extract_audio(video_path, audio_path)
            if not audio_extracted:
                results["warnings"].append("Audio extraction failed, using silent audio")
            
            progress.update(10, "analyzing_facial")
            facial_data = await _analyze_facial(video_path, results)
            if facial_data:
                results["stages_completed"].append("facial_analysis")
            else:
                results["stages_failed"].append("facial_analysis")
                results["warnings"].append("No face detected in video")
            
            progress.update(40, "analyzing_audio")
            audio_data = await _analyze_audio(audio_path, results)
            if audio_data:
                results["stages_completed"].append("audio_analysis")
            else:
                results["stages_failed"].append("audio_analysis")
                results["warnings"].append("Audio analysis failed")
            
            progress.update(60, "transcribing")
            transcript_data = await _transcribe(audio_path, metadata, results)
            if transcript_data:
                results["stages_completed"].append("transcription")
            else:
                results["stages_failed"].append("transcription")
                results["warnings"].append("Transcription failed")
            
            progress.update(80, "fusing_multimodal")
            fusion_data = await _fuse_multimodal(facial_data, audio_data, transcript_data, results)
            if fusion_data:
                results["stages_completed"].append("multimodal_fusion")
            
            progress.update(90, "saving_results")
            await _save_results(
                db, narrative, facial_data, audio_data, 
                transcript_data, fusion_data
            )
            
            _update_narrative_status_sync(db, narrative, "complete", progress=100, stage="complete")
            await db.commit()
            
            progress.update(100, "complete")
            results["status"] = "complete"
            
            logger.info(f"Processing complete for narrative {narrative_id}")
            return results
            
        except Exception as e:
            logger.exception(f"Error processing narrative {narrative_id}")
            progress.set_error(str(e))
            if narrative:
                _update_narrative_status_sync(db, narrative, "error", error=str(e))
                await db.commit()
            results["status"] = "error"
            results["error"] = str(e)
            raise


async def _get_narrative(db: AsyncSession, narrative_id: str) -> Optional[Narrative]:
    """Get narrative by ID."""
    result = await db.execute(
        select(Narrative).where(Narrative.id == narrative_id)
    )
    return result.scalar_one_or_none()


def _update_narrative_status_sync(
    db: AsyncSession,
    narrative: Narrative,
    status: str,
    progress: int = 0,
    stage: str = "",
    error: Optional[str] = None
):
    """Update narrative status synchronously."""
    narrative.status = status
    if hasattr(narrative, 'processing_progress'):
        narrative.processing_progress = progress
    if hasattr(narrative, 'processing_stage'):
        narrative.processing_stage = stage
    if error and hasattr(narrative, 'processing_error'):
        narrative.processing_error = error


def _update_narrative_status(
    narrative_id: str,
    status: str,
    error: Optional[str] = None
):
    """Update narrative status (for error handling outside async context)."""
    try:
        asyncio.run(_update_status_async(narrative_id, status, error))
    except Exception as e:
        logger.error(f"Failed to update narrative status: {e}")


async def _update_status_async(narrative_id: str, status: str, error: Optional[str]):
    """Async status update."""
    if async_session_factory is None:
        return
    
    async with async_session_factory() as db:
        narrative = await _get_narrative(db, narrative_id)
        if narrative:
            narrative.status = status
            if error and hasattr(narrative, 'processing_error'):
                narrative.processing_error = error
            await db.commit()


async def _extract_audio(video_path: str, audio_path: str) -> bool:
    """Extract audio from video. Returns True if successful."""
    try:
        from app.services.audio_service import extract_audio_from_video
        extract_audio_from_video(video_path, audio_path)
        return True
    except Exception as e:
        logger.warning(f"Audio extraction failed: {e}")
        return False


async def _analyze_facial(video_path: str, results: Dict) -> Optional[Dict]:
    """Analyze facial features with graceful failure."""
    try:
        from app.services.facial_service import analyze_facial_features
        return analyze_facial_features(video_path)
    except Exception as e:
        logger.warning(f"Facial analysis failed: {e}")
        return None


async def _analyze_audio(audio_path: str, results: Dict) -> Optional[Dict]:
    """Analyze audio features with graceful failure."""
    try:
        from app.services.audio_service import analyze_audio_features
        return analyze_audio_features(audio_path)
    except Exception as e:
        logger.warning(f"Audio analysis failed: {e}")
        return None


async def _transcribe(
    audio_path: str, 
    metadata: Dict, 
    results: Dict
) -> Optional[Dict]:
    """Transcribe audio with graceful failure."""
    try:
        if metadata.get("transcript"):
            return {
                "text": metadata["transcript"],
                "word_count": len(metadata["transcript"].split()),
                "confidence": 1.0,
                "model": "manual",
                "language": metadata.get("language", "en"),
                "segments": []
            }
        
        from app.services.transcription_service import WhisperTranscriber
        return WhisperTranscriber.transcribe(
            audio_path,
            language=metadata.get("language")
        )
    except Exception as e:
        logger.warning(f"Transcription failed: {e}")
        return None


async def _fuse_multimodal(
    facial_data: Optional[Dict],
    audio_data: Optional[Dict],
    transcript_data: Optional[Dict],
    results: Dict
) -> Optional[Dict]:
    """Fuse multimodal data with graceful failure."""
    try:
        from app.services.fusion_service import fuse_multimodal_features
        if facial_data and audio_data:
            transcript_text = transcript_data.get("text", "") if transcript_data else ""
            return fuse_multimodal_features(facial_data, audio_data, transcript_text)
        return None
    except Exception as e:
        logger.warning(f"Multimodal fusion failed: {e}")
        return None


async def _save_results(
    db: AsyncSession,
    narrative: Narrative,
    facial_data: Optional[Dict],
    audio_data: Optional[Dict],
    transcript_data: Optional[Dict],
    fusion_data: Optional[Dict]
):
    """Save all analysis results to database."""
    
    if facial_data:
        profile_data = facial_data.get("narrator_profile", {})
        narrator_profile = NarratorProfile(
            narrative_id=str(narrative.id),
            identity_hash=f"hash-{str(narrative.id)[:8]}",
            estimated_age=profile_data.get("estimated_age", 0),
            age_range=profile_data.get("age_range", "unknown"),
            gender=profile_data.get("gender", "unknown"),
            gender_confidence=profile_data.get("gender_confidence", 0),
            detection_confidence=profile_data.get("detection_confidence", 0),
            dominant_emotion=profile_data.get("dominant_emotion_overall", "neutral"),
            emotion_distribution=profile_data.get("emotion_distribution", {}),
            facial_action_units=profile_data.get("facial_action_units", {}),
        )
        db.add(narrator_profile)
        
        facial_analysis = FacialAnalysis(
            narrative_id=str(narrative.id),
            emotion_timeline=facial_data.get("emotion_timeline", []),
            expression_timeline=facial_data.get("expression_timeline", []),
            grad_cam_path=facial_data.get("grad_cam_path"),
        )
        db.add(facial_analysis)
    
    if audio_data:
        vocal_features = audio_data.get("vocal_features", {})
        vocal_analysis = VocalAnalysis(
            narrative_id=str(narrative.id),
            voice_activity_segments=audio_data.get("voice_activity_segments", []),
            pitch_timeline=audio_data.get("pitch_timeline", []),
            mean_pitch_hz=vocal_features.get("mean_pitch_hz", 0),
            pitch_range_min_hz=vocal_features.get("pitch_range_hz", {}).get("min", 0),
            pitch_range_max_hz=vocal_features.get("pitch_range_hz", {}).get("max", 0),
            pitch_variability_std=vocal_features.get("pitch_variability_std", 0),
            speech_rate_wpm=vocal_features.get("speech_rate_wpm", 0),
            pause_count=vocal_features.get("pause_count", 0),
            mean_pause_duration_sec=vocal_features.get("mean_pause_duration_sec", 0),
            sample_rate=audio_data.get("audio_quality", {}).get("sample_rate", 44100),
            snr_db=audio_data.get("audio_quality", {}).get("snr_db", 0),
            vocal_emotion_indicators=vocal_features.get("vocal_emotion_indicators", {}),
        )
        db.add(vocal_analysis)
        
        if vocal_features.get("total_duration_sec"):
            narrative.duration_sec = vocal_features["total_duration_sec"]
    
    if transcript_data:
        transcript = Transcript(
            narrative_id=str(narrative.id),
            text=transcript_data.get("text", ""),
            word_count=transcript_data.get("word_count", 0),
            asr_model=transcript_data.get("model", "unknown"),
            confidence=transcript_data.get("confidence", 0),
            language=transcript_data.get("language", "en"),
        )
        db.add(transcript)
    
    if fusion_data:
        multimodal_fusion = MultimodalFusion(
            narrative_id=str(narrative.id),
            unified_emotion_timeline=fusion_data.get("unified_emotion_timeline", []),
            emotion_congruence=fusion_data.get("emotion_congruence", {}),
            narrator_vector=fusion_data.get("narrator_vector", {}),
            grad_cam_highlights=fusion_data.get("grad_cam_highlights", {}),
            fusion_method=fusion_data.get("fusion_method", "weighted_fusion"),
        )
        db.add(multimodal_fusion)
