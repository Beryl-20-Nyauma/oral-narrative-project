"""Database seeding for sample narratives."""

import asyncio
from datetime import date, datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.narrative import (
    Narrative, Theme, Transcript, NarratorProfile,
    FacialAnalysis, VocalAnalysis, MultimodalFusion
)
from app.services.facial_service import analyze_facial_features
from app.services.audio_service import analyze_audio_features
from app.services.fusion_service import fuse_multimodal_features


SAMPLE_NARRATIVE_IDS = [
    UUID("00000001-0000-0000-0000-000000000001"),
    UUID("00000002-0000-0000-0000-000000000001"),
    UUID("00000003-0000-0000-0000-000000000001"),
    UUID("00000004-0000-0000-0000-000000000001"),
    UUID("00000005-0000-0000-0000-000000000001"),
]

SAMPLE_NARRATIVES = [
    {
        "title": "The Day the River Flooded",
        "narrator_name": "Kirongosi A",
        "location": "Kakamega, Kenya",
        "themes": ["memory", "water", "community", "survival"],
        "transcript": "I remember it was the rainy season of 1987. The Subin River had been rising for days. My mother kept watch all night...",
        "date_recorded": date(2024, 1, 15),
    },
    {
        "title": "Songs My Grandmother Taught Me",
        "narrator_name": "Rose Anyango",
        "location": "Kisumu, Nyanza",
        "themes": ["music", "family", "tradition", "loss"],
        "transcript": "She would sit by the window every evening and hum these melodies. I didn't understand the words then, they were in Zapotec...",
        "date_recorded": date(2024, 2, 15),
    },
    {
        "title": "Working the Coal Mines",
        "narrator_name": "Davis Ongeri",
        "location": "Kisii, Kenya",
        "themes": ["labor", "history", "identity", "resistance"],
        "transcript": "My father went down at six in the morning and came up at four. Every day for forty years. We never asked him how it was down there...",
        "date_recorded": date(2024, 3, 15),
    },
    {
        "title": "First Night in a Strange Country",
        "narrator_name": "Nadia Beryl",
        "location": "Ngong, Kajiado",
        "themes": ["migration", "belonging", "hope", "displacement"],
        "transcript": "The apartment was so quiet. In Ngong, you always hear the neighbors, the street, the call to prayer. Here it was just silence...",
        "date_recorded": date(2024, 4, 15),
    },
    {
        "title": "My Mother's Kitchen Garden",
        "narrator_name": "Luwi Ochieng",
        "location": "Embu, Kenya",
        "themes": ["food", "memory", "healing", "place"],
        "transcript": "She planted everything by the phases of the moon. Turmeric here, ginger there, tulsi by the doorstep for protection...",
        "date_recorded": date(2024, 5, 15),
    },
]

ALL_THEMES = [
    "memory", "water", "community", "survival",
    "music", "family", "tradition", "loss",
    "labor", "history", "identity", "resistance",
    "migration", "belonging", "hope", "displacement",
    "food", "healing", "place",
]


async def seed_themes(db: AsyncSession) -> dict:
    """Seed themes and return name->id mapping."""
    theme_map = {}
    for theme_name in ALL_THEMES:
        result = await db.execute(select(Theme).where(Theme.name == theme_name))
        existing = result.scalar_one_or_none()
        if existing:
            theme_map[theme_name] = existing
        else:
            theme = Theme(name=theme_name)
            db.add(theme)
            theme_map[theme_name] = theme
    await db.commit()
    return theme_map


async def seed_narrative(
    db: AsyncSession,
    sample_data: dict,
    narrative_id: UUID,
    theme_map: dict
) -> Narrative:
    """Seed a single narrative with all related data."""
    
    result = await db.execute(select(Narrative).where(Narrative.id == narrative_id))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    
    narrative = Narrative(
        id=narrative_id,
        status="complete",
        title=sample_data["title"],
        narrator_name=sample_data["narrator_name"],
        location=sample_data["location"],
        language="en",
        duration_sec=14.8,
        date_recorded=sample_data["date_recorded"],
    )
    
    for theme_name in sample_data["themes"]:
        if theme_name in theme_map:
            narrative.themes.append(theme_map[theme_name])
    
    db.add(narrative)
    await db.flush()
    
    transcript = Transcript(
        narrative_id=narrative_id,
        text=sample_data["transcript"],
        word_count=len(sample_data["transcript"].split()),
        asr_model="whisper-large-v3",
        confidence=0.92,
    )
    db.add(transcript)
    
    facial_data = analyze_facial_features("sample.mp4")
    profile_data = facial_data["narrator_profile"]
    
    narrator_profile = NarratorProfile(
        narrative_id=narrative_id,
        identity_hash=f"hash-{str(narrative_id)[:8]}",
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
    
    audio_data = analyze_audio_features("sample.wav")
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
    
    fusion_data = fuse_multimodal_features(facial_data, audio_data, sample_data["transcript"])
    
    multimodal_fusion = MultimodalFusion(
        narrative_id=narrative_id,
        unified_emotion_timeline=fusion_data["unified_emotion_timeline"],
        emotion_congruence=fusion_data["emotion_congruence"],
        narrator_vector=fusion_data["narrator_vector"],
        grad_cam_highlights=fusion_data["grad_cam_highlights"],
        fusion_method=fusion_data["fusion_method"],
    )
    db.add(multimodal_fusion)
    
    await db.commit()
    return narrative


async def seed_database(db: AsyncSession) -> int:
    """Seed all sample data. Returns count of narratives seeded."""
    
    theme_map = await seed_themes(db)
    count = 0
    
    for i, sample_data in enumerate(SAMPLE_NARRATIVES):
        narrative = await seed_narrative(db, sample_data, SAMPLE_NARRATIVE_IDS[i], theme_map)
        if narrative:
            count += 1
    
    return count


async def is_database_seeded(db: AsyncSession) -> bool:
    """Check if database already has sample data."""
    result = await db.execute(select(Narrative).limit(1))
    return result.scalar_one_or_none() is not None


async def seed_demo_user(db: AsyncSession):
    """
    Create a demo user with admin privileges for testing purposes.
    
    Args:
        db: Database session
        
    Returns:
        The created User object with is_admin=True
    """
    from sqlalchemy import select
    from app.models.narrative import User
    from app.services.auth_service import hash_password
    
    result = await db.execute(select(User).where(User.email == "demo@oral-narrative.org"))
    existing = result.scalar_one_or_none()
    
    if existing:
        logger.info(f"Demo user already exists: {existing.email}")
        return existing
    
    user = User(
        email="demo@oral-narrative.org",
        hashed_password=hash_password("demo123"),
        full_name="Demo User",
        is_active=True,
        is_admin=True
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"Created demo user: {user.email}")
    return user
