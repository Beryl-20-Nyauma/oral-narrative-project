"""Tests for transcription service."""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.services.transcription_service import (
    WhisperTranscriber,
    transcribe_audio,
)


class TestWhisperTranscriberModelLoading:
    """Tests for model loading and configuration."""

    def teardown_method(self):
        """Reset model state after each test."""
        WhisperTranscriber._model = None
        WhisperTranscriber._model_name = "base"

    def test_default_model_name(self):
        """Should default to 'base' model."""
        assert WhisperTranscriber._model_name == "base"

    def test_set_valid_model_name(self):
        """Should accept valid model names."""
        for model in ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]:
            WhisperTranscriber._model = None
            WhisperTranscriber.set_model_name(model)
            assert WhisperTranscriber._model_name == model

    def test_set_invalid_model_name_raises(self):
        """Should raise ValueError for invalid model name."""
        with pytest.raises(ValueError, match="Invalid model"):
            WhisperTranscriber.set_model_name("invalid-model")

    def test_set_model_name_after_load_warns(self, caplog):
        """Should warn if model already loaded."""
        WhisperTranscriber._model = MagicMock()
        WhisperTranscriber.set_model_name("tiny")
        assert "already loaded" in caplog.text

    def test_is_loaded_returns_false_initially(self):
        """Should return False when model not loaded."""
        WhisperTranscriber._model = None
        assert WhisperTranscriber.is_loaded() is False

    def test_is_loaded_returns_true_after_load(self):
        """Should return True when model is loaded."""
        WhisperTranscriber._model = MagicMock()
        assert WhisperTranscriber.is_loaded() is True


class TestWhisperTranscriberTranscribe:
    """Tests for transcription functionality."""

    def teardown_method(self):
        """Reset model state after each test."""
        WhisperTranscriber._model = None
        WhisperTranscriber._model_name = "base"

    def test_transcribe_file_not_found(self):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            WhisperTranscriber.transcribe("/nonexistent/audio.wav")

    @patch("app.services.transcription_service.whisper")
    def test_transcribe_success(self, mock_whisper):
        """Should return transcription result."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "Hello world",
            "language": "en",
            "language_probability": 0.95,
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello world", "avg_logprob": -0.2, "no_speech_prob": 0.1, "tokens": []}
            ],
        }
        mock_whisper.load_model.return_value = mock_model
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake audio")
            temp_path = f.name
        
        try:
            result = WhisperTranscriber.transcribe(temp_path)
            
            assert result["text"] == "Hello world"
            assert result["word_count"] == 2
            assert result["language"] == "en"
            assert result["model"] == "whisper-base"
            assert "segments" in result
            assert "confidence" in result
        finally:
            os.unlink(temp_path)

    @patch("app.services.transcription_service.whisper")
    def test_transcribe_with_language(self, mock_whisper):
        """Should pass language option to model."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "Habari",
            "language": "sw",
            "language_probability": 0.99,
            "segments": [],
        }
        mock_whisper.load_model.return_value = mock_model
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake audio")
            temp_path = f.name
        
        try:
            result = WhisperTranscriber.transcribe(temp_path, language="sw")
            
            mock_model.transcribe.assert_called_once()
            call_kwargs = mock_model.transcribe.call_args[1]
            assert call_kwargs["language"] == "sw"
        finally:
            os.unlink(temp_path)

    @patch("app.services.transcription_service.whisper")
    def test_transcribe_empty_result(self, mock_whisper):
        """Should handle empty transcription."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "",
            "language": "en",
            "segments": [],
        }
        mock_whisper.load_model.return_value = mock_model
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake audio")
            temp_path = f.name
        
        try:
            result = WhisperTranscriber.transcribe(temp_path)
            
            assert result["text"] == ""
            assert result["word_count"] == 0
            assert result["confidence"] == 0.0
        finally:
            os.unlink(temp_path)

    @patch("app.services.transcription_service.whisper")
    def test_transcribe_failure_raises_runtime_error(self, mock_whisper):
        """Should raise RuntimeError on transcription failure."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = Exception("Transcription failed")
        mock_whisper.load_model.return_value = mock_model
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake audio")
            temp_path = f.name
        
        try:
            with pytest.raises(RuntimeError, match="Transcription failed"):
                WhisperTranscriber.transcribe(temp_path)
        finally:
            os.unlink(temp_path)


class TestSegmentProcessing:
    """Tests for segment processing helpers."""

    def test_process_segments_empty(self):
        """Should return empty list for no segments."""
        result = WhisperTranscriber._process_segments([])
        assert result == []

    def test_process_segments_filters_empty_text(self):
        """Should filter out segments with empty text."""
        segments = [
            {"start": 0.0, "end": 1.0, "text": "", "avg_logprob": -0.2, "no_speech_prob": 0.1},
            {"start": 1.0, "end": 2.0, "text": "Hello", "avg_logprob": -0.1, "no_speech_prob": 0.05},
        ]
        result = WhisperTranscriber._process_segments(segments)
        assert len(result) == 1
        assert result[0]["text"] == "Hello"

    def test_process_segments_rounds_values(self):
        """Should round timestamp and confidence values."""
        segments = [
            {"start": 0.123456, "end": 1.234567, "text": "Test", "avg_logprob": -0.123, "no_speech_prob": 0.0567, "tokens": []},
        ]
        result = WhisperTranscriber._process_segments(segments)
        
        assert result[0]["start"] == 0.12
        assert result[0]["end"] == 1.23


class TestConfidenceCalculation:
    """Tests for confidence calculation."""

    def test_calculate_confidence_empty(self):
        """Should return 0.0 for empty segments."""
        result = WhisperTranscriber._calculate_confidence([])
        assert result == 0.0

    def test_calculate_confidence_with_segments(self):
        """Should calculate confidence from log probabilities."""
        segments = [
            {"text": "Hello", "avg_logprob": -0.1},
            {"text": "World", "avg_logprob": -0.2},
        ]
        result = WhisperTranscriber._calculate_confidence(segments)
        assert 0.0 <= result <= 1.0

    def test_segment_confidence_high_logprob(self):
        """Should return high confidence for high log probability."""
        result = WhisperTranscriber._segment_confidence(avg_logprob=-0.1, no_speech_prob=0.1)
        assert result > 0.7

    def test_segment_confidence_low_logprob(self):
        """Should return low confidence for low log probability."""
        result = WhisperTranscriber._segment_confidence(avg_logprob=-1.0, no_speech_prob=0.1)
        assert result < 0.5


class TestTranscribeAudioHelper:
    """Tests for transcribe_audio convenience function."""

    def teardown_method(self):
        """Reset model state after each test."""
        WhisperTranscriber._model = None
        WhisperTranscriber._model_name = "base"

    @patch("app.services.transcription_service.whisper")
    def test_transcribe_audio_sets_model(self, mock_whisper):
        """Should set model name before transcription."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "", "language": "en", "segments": []}
        mock_whisper.load_model.return_value = mock_model
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake audio")
            temp_path = f.name
        
        try:
            transcribe_audio(temp_path, model="tiny")
            assert WhisperTranscriber._model_name == "tiny"
        finally:
            os.unlink(temp_path)
