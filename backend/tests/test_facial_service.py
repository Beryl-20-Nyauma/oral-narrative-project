"""Tests for facial analysis service."""

import pytest
import os
import tempfile
import numpy as np
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.services.facial_service import (
    FacialAnalyzer,
    analyze_facial_features,
)


class TestFacialAnalyzerInitialization:
    """Tests for FacialAnalyzer initialization."""

    def teardown_method(self):
        """Reset initialization state after each test."""
        FacialAnalyzer._initialized = False

    @patch("app.services.facial_service.DeepFace")
    def test_ensure_initialized(self, mock_deepface):
        """Should initialize DeepFace models on first call."""
        FacialAnalyzer._initialized = False
        FacialAnalyzer.ensure_initialized()
        
        mock_deepface.build_model.assert_called_once_with("Emotion")
        assert FacialAnalyzer._initialized is True

    @patch("app.services.facial_service.DeepFace")
    def test_ensure_initialized_only_once(self, mock_deepface):
        """Should only initialize once even if called multiple times."""
        FacialAnalyzer._initialized = False
        FacialAnalyzer.ensure_initialized()
        FacialAnalyzer.ensure_initialized()
        
        mock_deepface.build_model.assert_called_once()

    @patch("app.services.facial_service.DeepFace")
    def test_ensure_initialized_handles_error(self, mock_deepface, caplog):
        """Should handle initialization errors gracefully."""
        mock_deepface.build_model.side_effect = Exception("Init failed")
        FacialAnalyzer._initialized = False
        
        FacialAnalyzer.ensure_initialized()
        
        assert "deferred" in caplog.text


class TestFacialAnalyzerVideoValidation:
    """Tests for video file validation."""

    def teardown_method(self):
        """Reset state after each test."""
        FacialAnalyzer._initialized = False

    def test_analyze_video_file_not_found(self):
        """Should raise FileNotFoundError for missing video."""
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            FacialAnalyzer.analyze_video("/nonexistent/video.mp4")

    @patch("app.services.facial_service.cv2.VideoCapture")
    def test_analyze_video_cannot_open(self, mock_vc_class):
        """Should raise ValueError if video cannot be opened."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_vc_class.return_value = mock_cap
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Cannot open video"):
                FacialAnalyzer.analyze_video(temp_path)
        finally:
            os.unlink(temp_path)


class TestFacialAnalyzerFrameProcessing:
    """Tests for frame processing."""

    def teardown_method(self):
        """Reset state after each test."""
        FacialAnalyzer._initialized = False

    @patch("app.services.facial_service.DeepFace")
    @patch("app.services.facial_service.cv2.VideoCapture")
    def test_analyze_video_success(self, mock_vc_class, mock_deepface):
        """Should analyze video and return results."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: 30.0 if prop == 5 else 90  # fps=30, frames=90
        mock_cap.read.side_effect = [
            (True, np.zeros((100, 100, 3), dtype=np.uint8)),
            (True, np.zeros((100, 100, 3), dtype=np.uint8)),
            (False, None),
        ]
        mock_vc_class.return_value = mock_cap
        
        mock_deepface.analyze.return_value = [{
            "emotion": {"happy": 80, "sad": 5, "angry": 5, "fear": 2, "surprise": 3, "neutral": 3, "disgust": 2},
            "dominant_emotion": "happy",
            "age": 35,
            "dominant_gender": "Man",
        }]
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video")
            temp_path = f.name
        
        try:
            result = FacialAnalyzer.analyze_video(temp_path)
            
            assert "emotion_timeline" in result
            assert "expression_timeline" in result
            assert "narrator_profile" in result
            assert result["grad_cam_available"] is True
        finally:
            os.unlink(temp_path)

    @patch("app.services.facial_service.DeepFace")
    @patch("app.services.facial_service.cv2.VideoCapture")
    def test_analyze_video_no_faces(self, mock_vc_class, mock_deepface):
        """Should handle video with no detectable faces."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: 30.0 if prop == 5 else 90
        mock_cap.read.side_effect = [
            (True, np.zeros((100, 100, 3), dtype=np.uint8)),
            (False, None),
        ]
        mock_vc_class.return_value = mock_cap
        
        mock_deepface.analyze.side_effect = ValueError("No face detected")
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video")
            temp_path = f.name
        
        try:
            result = FacialAnalyzer.analyze_video(temp_path)
            
            assert result["narrator_profile"]["face_detected_frames"] == 0
            assert result["narrator_profile"]["gender"] == "unknown"
        finally:
            os.unlink(temp_path)


class TestAnalyzeFrame:
    """Tests for single frame analysis."""

    @patch("app.services.facial_service.DeepFace")
    def test_analyze_frame_success(self, mock_deepface):
        """Should return emotion data for valid frame."""
        mock_deepface.analyze.return_value = [{
            "emotion": {"happy": 70, "sad": 10, "angry": 5, "fear": 5, "surprise": 5, "neutral": 3, "disgust": 2},
            "dominant_emotion": "happy",
            "age": 42,
            "dominant_gender": "Woman",
        }]
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = FacialAnalyzer._analyze_frame(frame, 1.5, ["emotion", "age", "gender"])
        
        assert result is not None
        assert result["emotion"]["dominant"] == "happy"
        assert result["emotion"]["joy"] == 0.7
        assert result["age"] == 42
        assert result["gender"] == "woman"

    @patch("app.services.facial_service.DeepFace")
    def test_analyze_frame_no_face(self, mock_deepface):
        """Should return None when no face detected."""
        mock_deepface.analyze.side_effect = ValueError("No face")
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = FacialAnalyzer._analyze_frame(frame, 1.5, ["emotion"])
        
        assert result is None

    @patch("app.services.facial_service.DeepFace")
    def test_analyze_frame_list_result(self, mock_deepface):
        """Should handle list result from DeepFace."""
        mock_deepface.analyze.return_value = [{
            "emotion": {"happy": 60, "sad": 20, "angry": 5, "fear": 5, "surprise": 5, "neutral": 3, "disgust": 2},
            "dominant_emotion": "happy",
            "age": 30,
            "dominant_gender": "Man",
        }]
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = FacialAnalyzer._analyze_frame(frame, 0.0, ["emotion", "age", "gender"])
        
        assert result is not None


class TestBuildNarratorProfile:
    """Tests for narrator profile building."""

    def test_build_profile_with_data(self):
        """Should aggregate frame data into profile."""
        emotions = [
            {"joy": 0.6, "sadness": 0.1, "anger": 0.1, "fear": 0.05, "surprise": 0.1, "neutral": 0.03, "disgust": 0.02},
            {"joy": 0.7, "sadness": 0.1, "anger": 0.05, "fear": 0.05, "surprise": 0.05, "neutral": 0.03, "disgust": 0.02},
        ]
        ages = [35, 37]
        genders = ["man", "man"]
        
        result = FacialAnalyzer._build_narrator_profile(emotions, ages, genders, 2, 10)
        
        assert result["estimated_age"] == 36
        assert result["gender"] == "man"
        assert result["gender_confidence"] == 1.0
        assert result["dominant_emotion_overall"] == "joy"
        assert result["face_detected_frames"] == 2
        assert result["total_frames"] == 10
        assert result["detection_confidence"] == 0.2

    def test_build_profile_empty(self):
        """Should return empty profile for no data."""
        result = FacialAnalyzer._build_narrator_profile([], [], [], 0, 10)
        
        assert result["estimated_age"] == 0
        assert result["gender"] == "unknown"
        assert result["detection_confidence"] == 0.0

    def test_build_profile_mixed_genders(self):
        """Should handle mixed gender detections."""
        emotions = [{"joy": 0.5, "sadness": 0.1, "anger": 0.1, "fear": 0.1, "surprise": 0.1, "neutral": 0.05, "disgust": 0.05}]
        ages = [30]
        genders = ["man", "woman", "man"]
        
        result = FacialAnalyzer._build_narrator_profile(emotions, ages, genders, 3, 10)
        
        assert result["gender"] == "man"
        assert result["gender_confidence"] == pytest.approx(2/3, rel=0.1)


class TestEstimateActionUnits:
    """Tests for facial action unit estimation."""

    def test_estimate_action_units_joy(self):
        """Should estimate high cheek raiser for joy."""
        emotion_dist = {"joy": 0.8, "sadness": 0.05, "anger": 0.05, "fear": 0.02, "surprise": 0.05, "neutral": 0.02, "disgust": 0.01}
        
        result = FacialAnalyzer._estimate_action_units(emotion_dist)
        
        assert result["AU6_cheek_raiser"] > 0.5
        assert result["AU12_lip_corner_puller"] > 0.5

    def test_estimate_action_units_sadness(self):
        """Should estimate inner brow raise for sadness."""
        emotion_dist = {"joy": 0.05, "sadness": 0.7, "anger": 0.05, "fear": 0.1, "surprise": 0.05, "neutral": 0.03, "disgust": 0.02}
        
        result = FacialAnalyzer._estimate_action_units(emotion_dist)
        
        assert result["AU1_inner_brow_raise"] > 0.3
        assert result["AU17_chin_raiser"] > 0.2

    def test_estimate_action_units_surprise(self):
        """Should estimate brow raise for surprise."""
        emotion_dist = {"joy": 0.05, "sadness": 0.05, "anger": 0.05, "fear": 0.1, "surprise": 0.7, "neutral": 0.03, "disgust": 0.02}
        
        result = FacialAnalyzer._estimate_action_units(emotion_dist)
        
        assert result["AU2_outer_brow_raise"] > 0.5


class TestAnalyzeFacialFeaturesHelper:
    """Tests for analyze_facial_features convenience function."""

    def teardown_method(self):
        """Reset state after each test."""
        FacialAnalyzer._initialized = False

    @patch.object(FacialAnalyzer, "analyze_video")
    def test_analyze_facial_features_calls_analyzer(self, mock_analyze):
        """Should call FacialAnalyzer.analyze_video."""
        mock_analyze.return_value = {"emotion_timeline": [], "narrator_profile": {}}
        
        result = analyze_facial_features("/path/to/video.mp4")
        
        mock_analyze.assert_called_once_with("/path/to/video.mp4")
        assert "emotion_timeline" in result
