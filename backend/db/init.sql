-- Oral Narrative Preservation System Database Schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Narratives table
CREATE TABLE narratives (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status VARCHAR(50) DEFAULT 'processing',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Metadata
    title VARCHAR(500) NOT NULL,
    narrator_name VARCHAR(255),
    location VARCHAR(255),
    language VARCHAR(10) DEFAULT 'en',
    duration_sec FLOAT DEFAULT 0.0,
    date_recorded DATE,
    
    -- File paths
    video_path TEXT,
    audio_path TEXT,
    thumbnail_path TEXT,
    archive_path TEXT
);

-- Themes (many-to-many)
CREATE TABLE themes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE narrative_themes (
    narrative_id UUID REFERENCES narratives(id) ON DELETE CASCADE,
    theme_id INTEGER REFERENCES themes(id) ON DELETE CASCADE,
    PRIMARY KEY (narrative_id, theme_id)
);

-- Transcripts
CREATE TABLE transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    narrative_id UUID REFERENCES narratives(id) ON DELETE CASCADE UNIQUE,
    text TEXT,
    word_count INTEGER DEFAULT 0,
    language VARCHAR(10) DEFAULT 'en',
    asr_model VARCHAR(100),
    confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Narrator profiles
CREATE TABLE narrator_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    narrative_id UUID REFERENCES narratives(id) ON DELETE CASCADE UNIQUE,
    identity_hash VARCHAR(32),
    estimated_age INTEGER,
    age_range VARCHAR(20),
    gender VARCHAR(50),
    gender_confidence FLOAT,
    detection_confidence FLOAT,
    dominant_emotion VARCHAR(50),
    emotion_distribution JSONB,
    facial_action_units JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Facial analysis
CREATE TABLE facial_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    narrative_id UUID REFERENCES narratives(id) ON DELETE CASCADE UNIQUE,
    emotion_timeline JSONB,
    expression_timeline JSONB,
    grad_cam_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vocal analysis
CREATE TABLE vocal_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    narrative_id UUID REFERENCES narratives(id) ON DELETE CASCADE UNIQUE,
    voice_activity_segments JSONB,
    pitch_timeline JSONB,
    mean_pitch_hz FLOAT,
    pitch_range_min_hz FLOAT,
    pitch_range_max_hz FLOAT,
    pitch_variability_std FLOAT,
    speech_rate_wpm FLOAT,
    pause_count INTEGER,
    mean_pause_duration_sec FLOAT,
    sample_rate INTEGER,
    snr_db FLOAT,
    vocal_emotion_indicators JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Multimodal fusion
CREATE TABLE multimodal_fusion (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    narrative_id UUID REFERENCES narratives(id) ON DELETE CASCADE UNIQUE,
    unified_emotion_timeline JSONB,
    emotion_congruence JSONB,
    narrator_vector JSONB,
    grad_cam_highlights JSONB,
    fusion_method VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_narratives_status ON narratives(status);
CREATE INDEX idx_narratives_narrator ON narratives(narrator_name);
CREATE INDEX idx_narratives_created ON narratives(created_at DESC);
CREATE INDEX idx_narrator_profiles_emotion ON narrator_profiles(dominant_emotion);
CREATE INDEX idx_transcripts_text ON transcripts USING gin(to_tsvector('english', text));

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_narratives_updated_at 
    BEFORE UPDATE ON narratives 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
