"""SQLAlchemy models for Oral Narrative Preservation System."""

from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Table, JSON, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, date
import uuid

from app.core.database import Base, GUID


class User(Base):
    __tablename__ = "users"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)


narrative_themes = Table(
    'narrative_themes',
    Base.metadata,
    Column('narrative_id', GUID(), ForeignKey('narratives.id', ondelete='CASCADE')),
    Column('theme_id', Integer, ForeignKey('themes.id', ondelete='CASCADE'))
)


class Narrator(Base):
    __tablename__ = "narrators"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), default="Unknown")
    face_embedding = Column(JSON)
    reference_image_path = Column(Text)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    narrative_count = Column(Integer, default=0)
    named_by_user = Column(Boolean, default=False)
    extra_data = Column(JSON)
    deleted_at = Column(DateTime, nullable=True)

    narratives = relationship("Narrative", back_populates="narrator")


class Narrative(Base):
    __tablename__ = "narratives"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    title = Column(String(500), nullable=False)
    narrator_name = Column(String(255))
    location = Column(String(255))
    language = Column(String(10), default="en")
    duration_sec = Column(Float, default=0.0)
    date_recorded = Column(Date)
    
    video_path = Column(Text)
    audio_path = Column(Text)
    thumbnail_path = Column(Text)
    archive_path = Column(Text)
    
    processing_progress = Column(Integer, default=0)
    processing_stage = Column(String(100), default="queued")
    processing_error = Column(Text)
    celery_task_id = Column(String(100))
    
    narrator_id = Column(GUID(), ForeignKey("narrators.id", ondelete="SET NULL"))
    narrator_match_confidence = Column(Float)
    deleted_at = Column(DateTime, nullable=True)

    themes = relationship("Theme", secondary=narrative_themes, back_populates="narratives")
    narrator = relationship("Narrator", back_populates="narratives")
    transcript = relationship("Transcript", uselist=False, back_populates="narrative")
    narrator_profile = relationship("NarratorProfile", uselist=False, back_populates="narrative")
    facial_analysis = relationship("FacialAnalysis", uselist=False, back_populates="narrative")
    vocal_analysis = relationship("VocalAnalysis", uselist=False, back_populates="narrative")
    multimodal_fusion = relationship("MultimodalFusion", uselist=False, back_populates="narrative")


class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    narratives = relationship("Narrative", secondary=narrative_themes, back_populates="themes")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    narrative_id = Column(GUID(), ForeignKey("narratives.id", ondelete="CASCADE"), unique=True)
    text = Column(Text)
    word_count = Column(Integer, default=0)
    language = Column(String(10), default="en")
    asr_model = Column(String(100))
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    narrative = relationship("Narrative", back_populates="transcript")


class NarratorProfile(Base):
    __tablename__ = "narrator_profiles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    narrative_id = Column(GUID(), ForeignKey("narratives.id", ondelete="CASCADE"), unique=True)
    identity_hash = Column(String(32))
    estimated_age = Column(Integer)
    age_range = Column(String(20))
    gender = Column(String(50))
    gender_confidence = Column(Float)
    detection_confidence = Column(Float)
    dominant_emotion = Column(String(50), index=True)
    emotion_distribution = Column(JSON)
    facial_action_units = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    narrative = relationship("Narrative", back_populates="narrator_profile")


class FacialAnalysis(Base):
    __tablename__ = "facial_analysis"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    narrative_id = Column(GUID(), ForeignKey("narratives.id", ondelete="CASCADE"), unique=True)
    emotion_timeline = Column(JSON)
    expression_timeline = Column(JSON)
    grad_cam_path = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    narrative = relationship("Narrative", back_populates="facial_analysis")


class VocalAnalysis(Base):
    __tablename__ = "vocal_analysis"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    narrative_id = Column(GUID(), ForeignKey("narratives.id", ondelete="CASCADE"), unique=True)
    voice_activity_segments = Column(JSON)
    pitch_timeline = Column(JSON)
    mean_pitch_hz = Column(Float)
    pitch_range_min_hz = Column(Float)
    pitch_range_max_hz = Column(Float)
    pitch_variability_std = Column(Float)
    speech_rate_wpm = Column(Float)
    pause_count = Column(Integer)
    mean_pause_duration_sec = Column(Float)
    sample_rate = Column(Integer)
    snr_db = Column(Float)
    vocal_emotion_indicators = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    narrative = relationship("Narrative", back_populates="vocal_analysis")


class MultimodalFusion(Base):
    __tablename__ = "multimodal_fusion"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    narrative_id = Column(GUID(), ForeignKey("narratives.id", ondelete="CASCADE"), unique=True)
    unified_emotion_timeline = Column(JSON)
    emotion_congruence = Column(JSON)
    narrator_vector = Column(JSON)
    grad_cam_highlights = Column(JSON)
    fusion_method = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    narrative = relationship("Narrative", back_populates="multimodal_fusion")
