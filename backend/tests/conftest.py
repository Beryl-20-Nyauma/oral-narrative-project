"""Pytest fixtures for Oral Narrative Preservation System tests."""

import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.narrative import (
    Narrative, Theme, NarratorProfile, FacialAnalysis,
    VocalAnalysis, MultimodalFusion, Transcript
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def sample_narrative(db_session):
    """Create a sample narrative for testing."""
    narrative = Narrative(
        id="test-0001",
        status="complete",
        title="Test Narrative",
        narrator_name="Test Narrator",
        location="Test Location",
        language="en",
        duration_sec=14.8,
        date_recorded="2024-01-15",
    )
    
    theme1 = Theme(name="memory")
    theme2 = Theme(name="test")
    narrative.themes = [theme1, theme2]
    
    db_session.add(narrative)
    await db_session.flush()
    
    narrator_profile = NarratorProfile(
        narrative_id="test-0001",
        identity_hash="test123",
        estimated_age=52,
        age_range="45-60",
        gender="woman",
        gender_confidence=0.94,
        detection_confidence=0.95,
        dominant_emotion="joy",
        emotion_distribution={"joy": 0.38, "neutral": 0.29},
        facial_action_units={"AU6_cheek_raiser": 0.42},
    )
    db_session.add(narrator_profile)
    
    facial_analysis = FacialAnalysis(
        narrative_id="test-0001",
        emotion_timeline=[{"timestamp": 0.0, "dominant": "joy", "joy": 0.68, "sadness": 0.05}],
        expression_timeline=[{"timestamp": 0.0, "smiling": True, "frowning": False}],
        grad_cam_path="grad_cam_test.png",
    )
    db_session.add(facial_analysis)
    
    vocal_analysis = VocalAnalysis(
        narrative_id="test-0001",
        voice_activity_segments=[{"start": 0.0, "end": 3.0, "active": True}],
        pitch_timeline=[{"timestamp": 0.0, "hz": 182.3, "note": "F#3"}],
        mean_pitch_hz=198.4,
        speech_rate_wpm=127,
        pause_count=3,
        mean_pause_duration_sec=0.5,
        sample_rate=44100,
        snr_db=28.4,
        vocal_emotion_indicators={"arousal": 0.62, "valence": 0.71},
    )
    db_session.add(vocal_analysis)
    
    multimodal_fusion = MultimodalFusion(
        narrative_id="test-0001",
        unified_emotion_timeline=[{"timestamp": 0.0, "fused_emotion_label": "joy"}],
        emotion_congruence={"facial_vocal_agreement_score": 0.78},
        narrator_vector={"narrator_identity_hash": "test123"},
        grad_cam_highlights={"high_attention_regions": ["eye area"]},
        fusion_method="Late fusion",
    )
    db_session.add(multimodal_fusion)
    
    transcript = Transcript(
        narrative_id="test-0001",
        text="This is a test transcript.",
        word_count=5,
        asr_model="whisper-base",
        confidence=0.94,
    )
    db_session.add(transcript)
    
    await db_session.commit()
    
    return narrative
