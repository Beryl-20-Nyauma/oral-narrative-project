"""Tests for audio analysis service."""

import pytest
import os
import tempfile
import numpy as np
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.services.audio_service import (
    extract_audio_from_video,
    analyze_audio_features,
    _detect_voice_activity,
    _build_pitch_timeline,
    _extract_vocal_features,
    _assess_audio_quality,
    _count_pauses,
)


class TestExtractAudioFromVideo:
    """Tests for audio extraction from video."""

    @patch("app.services.audio_service.subprocess.run")
    def test_extract_audio_creates_output_dir(self, mock_run):
        """Should create output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "subdir", "audio.wav")
            
            extract_audio_from_video("/fake/video.mp4", output_path)
            
            assert os.path.exists(os.path.dirname(output_path))

    @patch("app.services.audio_service.subprocess.run")
    def test_extract_audio_calls_ffmpeg(self, mock_run):
        """Should call ffmpeg with correct arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "audio.wav")
            
            extract_audio_from_video("/input/video.mp4", output_path)
            
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "ffmpeg" in args
            assert "-i" in args
            assert "/input/video.mp4" in args
            assert output_path in args
            assert "-vn" in args
            assert "-acodec" in args
            assert "pcm_s16le" in args

    @patch("app.services.audio_service.subprocess.run")
    def test_extract_audio_handles_error(self, mock_run):
        """Should raise error if ffmpeg fails."""
        mock_run.side_effect = Exception("FFmpeg error")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(Exception, match="FFmpeg error"):
                extract_audio_from_video("/input/video.mp4", os.path.join(tmpdir, "audio.wav"))


class TestAnalyzeAudioFeatures:
    """Tests for audio feature analysis."""

    @patch("app.services.audio_service.librosa")
    def test_analyze_audio_features_success(self, mock_librosa):
        """Should return all expected features."""
        mock_y = np.random.randn(44100)
        mock_sr = 44100
        mock_librosa.load.return_value = (mock_y, mock_sr)
        mock_librosa.pyin.return_value = (
            np.array([200.0, np.nan, 210.0]),
            np.array([True, False, True]),
            np.array([0.9, 0.1, 0.8]),
        )
        mock_librosa.feature.rms.return_value = np.array([[0.1, 0.2, 0.1]])
        mock_librosa.feature.mfcc.return_value = np.random.randn(13, 10)
        mock_librosa.feature.spectral_centroid.return_value = np.array([[1000, 1100]])
        mock_librosa.feature.zero_crossing_rate.return_value = np.array([[0.05, 0.06]])
        mock_librosa.onset.onset_detect.return_value = np.array([0, 5, 10])
        mock_librosa.times_like.return_value = np.array([0.0, 0.5, 1.0])
        mock_librosa.frames_to_time.return_value = np.array([0.0, 0.5, 1.0])
        mock_librosa.note_to_hz.return_value = 65.41
        mock_librosa.hz_to_note.return_value = "C2"
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake audio")
            temp_path = f.name
        
        try:
            result = analyze_audio_features(temp_path)
            
            assert "voice_activity_segments" in result
            assert "pitch_timeline" in result
            assert "vocal_features" in result
            assert "audio_quality" in result
        finally:
            os.unlink(temp_path)


class TestDetectVoiceActivity:
    """Tests for voice activity detection."""

    @patch("app.services.audio_service.librosa")
    def test_detect_voice_activity_segments(self, mock_librosa):
        """Should detect voice activity segments."""
        mock_y = np.random.randn(44100)
        mock_sr = 44100
        
        mock_librosa.feature.rms.return_value = np.array([[0.05, 0.2, 0.2, 0.05, 0.3]])
        mock_librosa.times_like.return_value = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
        
        result = _detect_voice_activity(mock_y, mock_sr)
        
        assert isinstance(result, list)
        assert all("start" in s and "end" in s for s in result)

    @patch("app.services.audio_service.librosa")
    def test_detect_voice_activity_empty(self, mock_librosa):
        """Should return empty list for silent audio."""
        mock_y = np.zeros(44100)
        mock_sr = 44100
        
        mock_librosa.feature.rms.return_value = np.array([[0.0, 0.0, 0.0]])
        mock_librosa.times_like.return_value = np.array([0.0, 0.5, 1.0])
        
        result = _detect_voice_activity(mock_y, mock_sr)
        
        assert result == []


class TestBuildPitchTimeline:
    """Tests for pitch timeline building."""

    @patch("app.services.audio_service.librosa")
    def test_build_pitch_timeline(self, mock_librosa):
        """Should build pitch timeline from F0."""
        f0 = np.array([100.0, np.nan, 200.0, 150.0, np.nan, 250.0])
        mock_sr = 44100
        
        mock_librosa.times_like.return_value = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
        mock_librosa.hz_to_note.side_effect = lambda hz: f"Note_{int(hz)}"
        
        result = _build_pitch_timeline(f0, mock_sr)
        
        assert isinstance(result, list)
        for entry in result:
            assert "timestamp" in entry
            assert "hz" in entry
            assert "note" in entry

    @patch("app.services.audio_service.librosa")
    def test_build_pitch_timeline_filters_nan(self, mock_librosa):
        """Should filter out NaN pitch values."""
        f0 = np.array([np.nan, np.nan, np.nan])
        
        mock_librosa.times_like.return_value = np.array([0.0, 0.1, 0.2])
        
        result = _build_pitch_timeline(f0, 44100)
        
        assert result == []

    @patch("app.services.audio_service.librosa")
    def test_build_pitch_timeline_limits_entries(self, mock_librosa):
        """Should limit timeline to 50 entries."""
        f0 = np.array([100.0 + i for i in range(100)])
        
        mock_librosa.times_like.return_value = np.arange(100) * 0.1
        mock_librosa.hz_to_note.return_value = "C4"
        
        result = _build_pitch_timeline(f0, 44100)
        
        assert len(result) <= 50


class TestExtractVocalFeatures:
    """Tests for vocal feature extraction."""

    @patch("app.services.audio_service.librosa")
    def test_extract_vocal_features_success(self, mock_librosa):
        """Should extract all vocal features."""
        y = np.random.randn(44100)
        sr = 44100
        f0 = np.array([200.0, 210.0, 220.0])
        voiced = np.array([True, True, True])
        duration = 5.0
        
        mock_librosa.onset.onset_detect.return_value = np.array([0, 10, 20])
        mock_librosa.feature.mfcc.return_value = np.random.randn(13, 10)
        mock_librosa.feature.spectral_centroid.return_value = np.array([[1000, 1100, 1200]])
        mock_librosa.feature.zero_crossing_rate.return_value = np.array([[0.05, 0.06, 0.07]])
        
        result = _extract_vocal_features(y, sr, f0, voiced, duration)
        
        assert "mean_pitch_hz" in result
        assert "pitch_range_hz" in result
        assert "speech_rate_wpm" in result
        assert "mfcc_features" in result
        assert "vocal_emotion_indicators" in result

    @patch("app.services.audio_service.librosa")
    def test_extract_vocal_features_empty_f0(self, mock_librosa):
        """Should handle empty F0 array."""
        y = np.zeros(44100)
        sr = 44100
        f0 = np.array([np.nan, np.nan])
        voiced = np.array([False, False])
        duration = 5.0
        
        mock_librosa.onset.onset_detect.return_value = np.array([])
        mock_librosa.feature.mfcc.return_value = np.zeros((13, 10))
        mock_librosa.feature.spectral_centroid.return_value = np.array([[0, 0]])
        mock_librosa.feature.zero_crossing_rate.return_value = np.array([[0, 0]])
        
        result = _extract_vocal_features(y, sr, f0, voiced, duration)
        
        assert result["mean_pitch_hz"] == 0
        assert result["pitch_range_hz"]["min"] == 0
        assert result["pitch_range_hz"]["max"] == 0


class TestCountPauses:
    """Tests for pause counting."""

    def test_count_pauses_no_pauses(self):
        """Should return 0 when no pauses."""
        voiced = np.array([True, True, True, True])
        result = _count_pauses(voiced)
        assert result == 0

    def test_count_pauses_single_pause(self):
        """Should count single pause."""
        voiced = np.array([True, True, False, False, True, True])
        result = _count_pauses(voiced)
        assert result == 1

    def test_count_pauses_multiple(self):
        """Should count multiple pauses."""
        voiced = np.array([True, False, True, False, True, False, True])
        result = _count_pauses(voiced)
        assert result == 3

    def test_count_pauses_none(self):
        """Should return 0 for None input."""
        result = _count_pauses(None)
        assert result == 0


class TestAssessAudioQuality:
    """Tests for audio quality assessment."""

    def test_assess_audio_quality_good(self):
        """Should assess good quality audio."""
        y = np.random.randn(44100) * 0.5
        sr = 44100
        
        result = _assess_audio_quality(y, sr)
        
        assert result["sample_rate"] == 44100
        assert result["bit_depth"] == 16
        assert "snr_db" in result
        assert result["clipping_detected"] is False

    def test_assess_audio_quality_clipping(self):
        """Should detect clipping."""
        y = np.ones(44100)
        sr = 44100
        
        result = _assess_audio_quality(y, sr)
        
        assert result["clipping_detected"] is True

    def test_assess_audio_quality_silent(self):
        """Should handle silent audio."""
        y = np.zeros(44100)
        sr = 44100
        
        result = _assess_audio_quality(y, sr)
        
        assert result["snr_db"] == 0


class TestAnalyzeAudioFeaturesIntegration:
    """Integration-style tests for audio analysis."""

    @patch("app.services.audio_service.librosa")
    def test_full_analysis_returns_expected_structure(self, mock_librosa):
        """Should return all expected keys."""
        mock_y = np.random.randn(44100)
        mock_sr = 44100
        mock_librosa.load.return_value = (mock_y, mock_sr)
        mock_librosa.pyin.return_value = (
            np.array([200.0, 210.0]),
            np.array([True, True]),
            np.array([0.9, 0.8]),
        )
        mock_librosa.feature.rms.return_value = np.array([[0.1]])
        mock_librosa.feature.mfcc.return_value = np.random.randn(13, 5)
        mock_librosa.feature.spectral_centroid.return_value = np.array([[1000]])
        mock_librosa.feature.zero_crossing_rate.return_value = np.array([[0.05]])
        mock_librosa.onset.onset_detect.return_value = np.array([0, 5])
        mock_librosa.times_like.return_value = np.array([0.0, 0.5])
        mock_librosa.frames_to_time.return_value = np.array([0.0, 0.5])
        mock_librosa.note_to_hz.return_value = 65.41
        mock_librosa.hz_to_note.return_value = "C2"
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake audio")
            temp_path = f.name
        
        try:
            result = analyze_audio_features(temp_path)
            
            assert "voice_activity_segments" in result
            assert "pitch_timeline" in result
            assert "vocal_features" in result
            assert "audio_quality" in result
            
            vf = result["vocal_features"]
            assert "mean_pitch_hz" in vf
            assert "speech_rate_wpm" in vf
            assert "mfcc_features" in vf
            assert "vocal_emotion_indicators" in vf
            
            assert "arousal" in vf["vocal_emotion_indicators"]
            assert "valence" in vf["vocal_emotion_indicators"]
            assert "dominance" in vf["vocal_emotion_indicators"]
        finally:
            os.unlink(temp_path)
