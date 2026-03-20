"""Integration tests for the full analysis pipeline."""

import pytest
import os
import tempfile
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import date

from app.services.upload_service import process_upload, run_analysis_pipeline
from app.models.narrative import (
    Narrative, Theme, NarratorProfile, FacialAnalysis,
    VocalAnalysis, MultimodalFusion, Transcript
)


class TestProcessUpload:
    """Tests for upload processing."""

    @pytest.mark.asyncio
    async def test_process_upload_creates_narrative(self, db_session):
        """Should create narrative record."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            temp_path = f.name
        
        class FakeUploadFile:
            filename = "test.mp4"
            async def read(self):
                return b"fake video content"
        
        try:
            from app.services.upload_service import process_upload
            from fastapi import BackgroundTasks
            
            bg_tasks = BackgroundTasks()
            
            with patch("app.services.upload_service.run_analysis_pipeline"):
                result = await process_upload(
                    db=db_session,
                    background_tasks=bg_tasks,
                    video=FakeUploadFile(),
                    title="Test Story",
                    narrator_name="Test Narrator",
                    location="Test Location",
                    language="en",
                    themes="memory, family",
                    transcript="",
                )
            
            assert "narrative_id" in result
            assert result["status"] == "processing"
        finally:
            os.unlink(temp_path)


class TestRunAnalysisPipeline:
    """Tests for the analysis pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_creates_all_records(self, db_session):
        """Should create all database records on successful processing."""
        narrative_id = str(uuid.uuid4())
        
        narrative = Narrative(
            id=narrative_id,
            status="processing",
            title="Test Story",
            narrator_name="Test Narrator",
            location="Test Location",
            language="en",
            duration_sec=0.0,
            date_recorded=date.today(),
            video_path="/tmp/test.mp4",
        )
        db_session.add(narrative)
        await db_session.commit()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "videos", f"{narrative_id}.mp4")
            audio_path = os.path.join(tmpdir, "audio", f"{narrative_id}.wav")
            os.makedirs(os.path.dirname(video_path), exist_ok=True)
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            
            with open(video_path, "wb") as f:
                f.write(b"fake video")
            with open(audio_path, "wb") as f:
                f.write(b"fake audio")
            
            with patch("app.services.upload_service.extract_audio_from_video") as mock_extract, \
                 patch("app.services.upload_service._analyze_facial_features") as mock_facial, \
                 patch("app.services.upload_service._analyze_audio_features") as mock_audio, \
                 patch("app.services.upload_service._fuse_multimodal_features") as mock_fusion, \
                 patch("app.services.upload_service.WhisperTranscriber") as mock_whisper, \
                 patch("app.services.upload_service.async_session_factory") as mock_factory:
                
                mock_facial.return_value = {
                    "emotion_timeline": [{"timestamp": 0.0, "dominant": "joy", "joy": 0.8, "sadness": 0.1, "anger": 0.05, "fear": 0.01, "surprise": 0.02, "neutral": 0.01, "disgust": 0.01}],
                    "expression_timeline": [{"timestamp": 0.0, "smiling": True}],
                    "narrator_profile": {
                        "estimated_age": 45,
                        "age_range": "38-53",
                        "gender": "woman",
                        "gender_confidence": 0.95,
                        "detection_confidence": 0.9,
                        "dominant_emotion_overall": "joy",
                        "emotion_distribution": {"joy": 0.8},
                        "facial_action_units": {"AU6_cheek_raiser": 0.7},
                    },
                    "grad_cam_path": "grad_cam_test.png",
                }
                
                mock_audio.return_value = {
                    "voice_activity_segments": [{"start": 0.0, "end": 1.0, "active": True}],
                    "pitch_timeline": [{"timestamp": 0.0, "hz": 200.0, "note": "G3"}],
                    "vocal_features": {
                        "mean_pitch_hz": 200.0,
                        "pitch_range_hz": {"min": 150.0, "max": 250.0},
                        "pitch_variability_std": 20.0,
                        "speech_rate_wpm": 120,
                        "pause_count": 3,
                        "mean_pause_duration_sec": 0.5,
                        "total_duration_sec": 5.0,
                        "vocal_emotion_indicators": {"arousal": 0.6, "valence": 0.7, "dominance": 0.5},
                    },
                    "audio_quality": {"sample_rate": 44100, "snr_db": 30.0},
                }
                
                mock_fusion.return_value = {
                    "unified_emotion_timeline": [{"timestamp": 0.0, "fused_emotion_label": "joy"}],
                    "emotion_congruence": {"facial_vocal_agreement_score": 0.85},
                    "narrator_vector": {"narrator_identity_hash": "abc123"},
                    "grad_cam_highlights": {"high_attention_regions": ["eyes"]},
                    "fusion_method": "Late fusion",
                }
                
                mock_whisper.transcribe.return_value = {
                    "text": "Hello world",
                    "word_count": 2,
                    "language": "en",
                    "confidence": 0.95,
                    "model": "whisper-base",
                }
                
                mock_session = AsyncMock()
                mock_session.execute.return_value.scalar_one_or_none.return_value = narrative
                mock_session.__aenter__.return_value = mock_session
                mock_session.__aexit__.return_value = None
                mock_factory.return_value = MagicMock(return_value=mock_session)
                
                await run_analysis_pipeline(
                    narrative_id,
                    video_path,
                    {
                        "title": "Test",
                        "narrator_name": "Test",
                        "location": "Test",
                        "language": "en",
                        "themes": [],
                        "transcript": "",
                    }
                )

    @pytest.mark.asyncio
    async def test_pipeline_handles_manual_transcript(self, db_session):
        """Should use manual transcript when provided."""
        narrative_id = str(uuid.uuid4())
        
        narrative = Narrative(
            id=narrative_id,
            status="processing",
            title="Test",
            narrator_name="Test",
            location="Test",
            language="en",
            duration_sec=0.0,
            date_recorded=date.today(),
            video_path="/tmp/test.mp4",
        )
        db_session.add(narrative)
        await db_session.commit()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "test.mp4")
            with open(video_path, "wb") as f:
                f.write(b"fake video")
            
            with patch("app.services.upload_service._analyze_facial_features") as mock_facial, \
                 patch("app.services.upload_service._analyze_audio_features") as mock_audio, \
                 patch("app.services.upload_service._fuse_multimodal_features") as mock_fusion, \
                 patch("app.services.upload_service.async_session_factory") as mock_factory, \
                 patch("app.services.upload_service.extract_audio_from_video"):
                
                mock_facial.return_value = {
                    "emotion_timeline": [],
                    "expression_timeline": [],
                    "narrator_profile": {
                        "estimated_age": 0,
                        "age_range": "unknown",
                        "gender": "unknown",
                        "gender_confidence": 0.0,
                        "detection_confidence": 0.0,
                        "dominant_emotion_overall": "neutral",
                        "emotion_distribution": {},
                        "facial_action_units": {},
                    },
                    "grad_cam_path": None,
                }
                
                mock_audio.return_value = {
                    "voice_activity_segments": [],
                    "pitch_timeline": [],
                    "vocal_features": {
                        "mean_pitch_hz": 0,
                        "pitch_range_hz": {"min": 0, "max": 0},
                        "pitch_variability_std": 0,
                        "speech_rate_wpm": 0,
                        "pause_count": 0,
                        "mean_pause_duration_sec": 0,
                        "total_duration_sec": 1.0,
                        "vocal_emotion_indicators": {},
                    },
                    "audio_quality": {"sample_rate": 44100, "snr_db": 0},
                }
                
                mock_fusion.return_value = {
                    "unified_emotion_timeline": [],
                    "emotion_congruence": {"facial_vocal_agreement_score": 0},
                    "narrator_vector": {"narrator_identity_hash": "test"},
                    "grad_cam_highlights": {},
                    "fusion_method": "Late fusion",
                }
                
                mock_session = AsyncMock()
                mock_session.execute.return_value.scalar_one_or_none.return_value = narrative
                mock_session.__aenter__.return_value = mock_session
                mock_session.__aexit__.return_value = None
                mock_factory.return_value = MagicMock(return_value=mock_session)
                
                await run_analysis_pipeline(
                    narrative_id,
                    video_path,
                    {
                        "title": "Test",
                        "narrator_name": "Test",
                        "location": "Test",
                        "language": "en",
                        "themes": [],
                        "transcript": "This is a manual transcript.",
                    }
                )
                
                transcript_arg = mock_fusion.call_args[0][2]
                assert transcript_arg == "This is a manual transcript."


class TestPipelineErrorHandling:
    """Tests for pipeline error handling."""

    @pytest.mark.asyncio
    async def test_pipeline_handles_missing_narrative(self, db_session):
        """Should handle missing narrative gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "test.mp4")
            with open(video_path, "wb") as f:
                f.write(b"fake video")
            
            with patch("app.services.upload_service.async_session_factory") as mock_factory:
                mock_session = AsyncMock()
                mock_session.execute.return_value.scalar_one_or_none.return_value = None
                mock_session.__aenter__.return_value = mock_session
                mock_session.__aexit__.return_value = None
                mock_factory.return_value = MagicMock(return_value=mock_session)
                
                await run_analysis_pipeline(
                    "nonexistent-id",
                    video_path,
                    {"transcript": ""}
                )


class TestServiceIntegration:
    """Tests for service-to-service integration."""

    def test_services_work_together(self):
        """Should verify services can be called in sequence."""
        from app.services.fusion_service import fuse_multimodal_features
        
        facial_result = {
            "emotion_timeline": [{"timestamp": 0.0, "dominant": "joy", "joy": 0.8, "sadness": 0.1, "anger": 0.02, "fear": 0.02, "surprise": 0.03, "neutral": 0.02, "disgust": 0.01}],
            "narrator_profile": {"dominant_emotion_overall": "joy", "estimated_age": 40, "gender": "woman"},
        }
        
        audio_result = {
            "voice_activity_segments": [{"start": 0.0, "end": 1.0, "active": True}],
            "vocal_features": {"vocal_emotion_indicators": {"arousal": 0.7}, "mean_pitch_hz": 200, "speech_rate_wpm": 130},
        }
        
        transcript = "This is a test transcript."
        
        fusion_result = fuse_multimodal_features(facial_result, audio_result, transcript)
        
        assert "unified_emotion_timeline" in fusion_result
        assert "emotion_congruence" in fusion_result
        assert "narrator_vector" in fusion_result
