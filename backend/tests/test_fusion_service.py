"""Tests for multimodal fusion service."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.fusion_service import (
    fuse_multimodal_features,
    _align_and_fuse_timelines,
    _find_closest_emotion,
    _calculate_emotion_congruence,
    _interpret_congruence,
    _generate_narrator_vector,
)


class TestFuseMultimodalFeatures:
    """Tests for main fusion function."""

    def test_fuse_returns_expected_structure(self):
        """Should return all expected keys."""
        facial_data = {
            "emotion_timeline": [{"timestamp": 0.0, "dominant": "joy", "joy": 0.8}],
            "narrator_profile": {"dominant_emotion_overall": "joy", "estimated_age": 35, "gender": "woman"},
        }
        audio_data = {
            "voice_activity_segments": [{"start": 0.0, "end": 1.0, "active": True}],
            "vocal_features": {"vocal_emotion_indicators": {"arousal": 0.6}},
        }
        transcript = "Hello world"
        
        result = fuse_multimodal_features(facial_data, audio_data, transcript)
        
        assert "unified_emotion_timeline" in result
        assert "narrator_vector" in result
        assert "emotion_congruence" in result
        assert "fusion_method" in result
        assert "grad_cam_highlights" in result

    def test_fuse_with_empty_inputs(self):
        """Should handle empty input data."""
        facial_data = {"emotion_timeline": [], "narrator_profile": {}}
        audio_data = {"voice_activity_segments": [], "vocal_features": {}}
        transcript = ""
        
        result = fuse_multimodal_features(facial_data, audio_data, transcript)
        
        assert result["unified_emotion_timeline"] == []
        assert "narrator_vector" in result


class TestAlignAndFuseTimelines:
    """Tests for timeline alignment and fusion."""

    def test_align_with_matching_data(self):
        """Should align matching facial and audio data."""
        facial_data = {
            "emotion_timeline": [
                {"timestamp": 0.0, "dominant": "joy", "joy": 0.8, "sadness": 0.1, "neutral": 0.05, "surprise": 0.05},
                {"timestamp": 1.0, "dominant": "neutral", "joy": 0.1, "sadness": 0.1, "neutral": 0.7, "surprise": 0.1},
            ],
        }
        audio_data = {
            "voice_activity_segments": [
                {"start": 0.0, "end": 0.5, "active": True},
                {"start": 1.0, "end": 1.5, "active": True},
            ],
            "vocal_features": {"vocal_emotion_indicators": {"arousal": 0.5}},
        }
        
        result = _align_and_fuse_timelines(facial_data, audio_data)
        
        assert len(result) == 2
        assert result[0]["facial_emotion"] == "joy"
        assert result[1]["facial_emotion"] == "neutral"

    def test_align_with_empty_facial_timeline(self):
        """Should return empty list for no facial data."""
        facial_data = {"emotion_timeline": []}
        audio_data = {
            "voice_activity_segments": [{"start": 0.0, "end": 1.0, "active": True}],
            "vocal_features": {},
        }
        
        result = _align_and_fuse_timelines(facial_data, audio_data)
        
        assert result == []

    def test_align_skips_inactive_segments(self):
        """Should skip inactive voice segments."""
        facial_data = {
            "emotion_timeline": [{"timestamp": 0.0, "dominant": "joy", "joy": 0.8}],
        }
        audio_data = {
            "voice_activity_segments": [
                {"start": 0.0, "end": 0.5, "active": False},
                {"start": 0.5, "end": 1.0, "active": True},
            ],
            "vocal_features": {"vocal_emotion_indicators": {"arousal": 0.5}},
        }
        
        result = _align_and_fuse_timelines(facial_data, audio_data)
        
        assert len(result) == 1

    def test_align_calculates_multimodal_confidence(self):
        """Should calculate weighted confidence."""
        facial_data = {
            "emotion_timeline": [{"timestamp": 0.0, "dominant": "joy", "joy": 0.8, "sadness": 0.1, "neutral": 0.05, "surprise": 0.05}],
        }
        audio_data = {
            "voice_activity_segments": [{"start": 0.0, "end": 1.0, "active": True}],
            "vocal_features": {"vocal_emotion_indicators": {"arousal": 0.6}},
        }
        
        result = _align_and_fuse_timelines(facial_data, audio_data)
        
        assert "multimodal_confidence" in result[0]
        assert 0 <= result[0]["multimodal_confidence"] <= 1


class TestFindClosestEmotion:
    """Tests for finding closest emotion by timestamp."""

    def test_find_exact_match(self):
        """Should find exact timestamp match."""
        emotions = {0.0: {"dominant": "joy"}, 1.0: {"dominant": "sadness"}}
        
        result = _find_closest_emotion(0.0, emotions)
        
        assert result["dominant"] == "joy"

    def test_find_closest(self):
        """Should find closest timestamp."""
        emotions = {0.0: {"dominant": "joy"}, 2.0: {"dominant": "sadness"}}
        
        result = _find_closest_emotion(1.5, emotions)
        
        assert result["dominant"] == "sadness"

    def test_find_empty(self):
        """Should return empty dict for no emotions."""
        result = _find_closest_emotion(1.0, {})
        
        assert result == {}


class TestCalculateEmotionCongruence:
    """Tests for emotion congruence calculation."""

    def test_congruence_high_agreement(self):
        """Should show high agreement when aligned."""
        facial_data = {
            "emotion_timeline": [{"timestamp": 0.0, "dominant": "joy"}],
            "narrator_profile": {"dominant_emotion_overall": "joy"},
        }
        audio_data = {
            "vocal_features": {"vocal_emotion_indicators": {"arousal": 0.8}},
        }
        
        result = _calculate_emotion_congruence(facial_data, audio_data)
        
        assert "facial_vocal_agreement_score" in result
        assert "moments_of_high_congruence" in result
        assert "moments_of_divergence" in result
        assert "interpretation" in result

    def test_congruence_low_agreement(self):
        """Should show low agreement when misaligned."""
        facial_data = {
            "emotion_timeline": [{"timestamp": 0.0, "dominant": "sadness"}],
            "narrator_profile": {"dominant_emotion_overall": "sadness"},
        }
        audio_data = {
            "vocal_features": {"vocal_emotion_indicators": {"arousal": 0.9}},
        }
        
        result = _calculate_emotion_congruence(facial_data, audio_data)
        
        assert result["facial_vocal_agreement_score"] < 0.8

    def test_congruence_empty_data(self):
        """Should handle empty data gracefully."""
        facial_data = {"emotion_timeline": [], "narrator_profile": {}}
        audio_data = {"vocal_features": {}}
        
        result = _calculate_emotion_congruence(facial_data, audio_data)
        
        assert "facial_vocal_agreement_score" in result


class TestInterpretCongruence:
    """Tests for congruence interpretation."""

    def test_interpret_high(self):
        """Should interpret high congruence."""
        result = _interpret_congruence(0.9)
        assert "High emotional authenticity" in result

    def test_interpret_good(self):
        """Should interpret good congruence."""
        result = _interpret_congruence(0.7)
        assert "Good emotional coherence" in result

    def test_interpret_moderate(self):
        """Should interpret moderate congruence."""
        result = _interpret_congruence(0.5)
        assert "Moderate alignment" in result

    def test_interpret_low(self):
        """Should interpret low congruence."""
        result = _interpret_congruence(0.3)
        assert "Low alignment" in result


class TestGenerateNarratorVector:
    """Tests for narrator vector generation."""

    def test_generate_vector_structure(self):
        """Should return expected structure."""
        facial_data = {
            "narrator_profile": {
                "estimated_age": 45,
                "gender": "woman",
            },
        }
        audio_data = {
            "vocal_features": {
                "mean_pitch_hz": 200.0,
                "speech_rate_wpm": 130,
            },
        }
        transcript = "Hello world"
        
        result = _generate_narrator_vector(facial_data, audio_data, transcript)
        
        assert "facial_embedding_dim" in result
        assert "audio_embedding_dim" in result
        assert "fused_vector_dim" in result
        assert "model_architecture" in result
        assert "narrator_identity_hash" in result
        assert "demographics" in result
        assert "vocal_characteristics" in result

    def test_generate_vector_includes_demographics(self):
        """Should include demographic information."""
        facial_data = {
            "narrator_profile": {
                "estimated_age": 52,
                "gender": "man",
            },
        }
        audio_data = {"vocal_features": {}}
        transcript = ""
        
        result = _generate_narrator_vector(facial_data, audio_data, transcript)
        
        assert result["demographics"]["estimated_age"] == 52
        assert result["demographics"]["gender"] == "man"

    def test_generate_vector_includes_vocal(self):
        """Should include vocal characteristics."""
        facial_data = {"narrator_profile": {}}
        audio_data = {
            "vocal_features": {
                "mean_pitch_hz": 180.5,
                "speech_rate_wpm": 145,
            },
        }
        transcript = ""
        
        result = _generate_narrator_vector(facial_data, audio_data, transcript)
        
        assert result["vocal_characteristics"]["mean_pitch_hz"] == 180.5
        assert result["vocal_characteristics"]["speech_rate_wpm"] == 145

    def test_generate_vector_handles_missing_data(self):
        """Should handle missing data gracefully."""
        facial_data = {"narrator_profile": {}}
        audio_data = {"vocal_features": {}}
        transcript = ""
        
        result = _generate_narrator_vector(facial_data, audio_data, transcript)
        
        assert result["demographics"]["estimated_age"] is None
        assert result["demographics"]["gender"] is None


class TestFusionIntegration:
    """Integration tests for multimodal fusion."""

    def test_full_fusion_pipeline(self):
        """Should process complete pipeline."""
        facial_data = {
            "emotion_timeline": [
                {"timestamp": 0.0, "dominant": "joy", "joy": 0.7, "sadness": 0.1, "anger": 0.05, "fear": 0.05, "surprise": 0.05, "neutral": 0.05},
                {"timestamp": 1.0, "dominant": "joy", "joy": 0.6, "sadness": 0.15, "anger": 0.05, "fear": 0.05, "surprise": 0.1, "neutral": 0.05},
                {"timestamp": 2.0, "dominant": "neutral", "joy": 0.2, "sadness": 0.1, "anger": 0.05, "fear": 0.05, "surprise": 0.1, "neutral": 0.5},
            ],
            "narrator_profile": {
                "dominant_emotion_overall": "joy",
                "estimated_age": 40,
                "gender": "woman",
            },
        }
        audio_data = {
            "voice_activity_segments": [
                {"start": 0.0, "end": 0.8, "active": True},
                {"start": 1.0, "end": 1.8, "active": True},
                {"start": 2.0, "end": 2.5, "active": True},
            ],
            "vocal_features": {
                "vocal_emotion_indicators": {"arousal": 0.65},
                "mean_pitch_hz": 195.0,
                "speech_rate_wpm": 125,
            },
        }
        transcript = "This is a story about my grandmother."
        
        result = fuse_multimodal_features(facial_data, audio_data, transcript)
        
        assert len(result["unified_emotion_timeline"]) == 3
        assert result["narrator_vector"]["demographics"]["gender"] == "woman"
        assert "interpretation" in result["emotion_congruence"]
