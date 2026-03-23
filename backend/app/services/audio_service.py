"""Audio analysis service using Librosa."""

import librosa
import numpy as np
import subprocess
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_audio_from_video(video_path: str, output_path: str) -> str:
    """
    Extract audio from video using FFmpeg.
    
    Args:
        video_path: Path to video file
        output_path: Path for output WAV file
    
    Returns:
        Path to extracted audio file
    
    Raises:
        FileNotFoundError: If video file doesn't exist
        RuntimeError: If FFmpeg extraction fails
    """
    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        result = subprocess.run([
            'ffmpeg', '-y', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '44100', '-ac', '1',
            output_path
        ], check=True, capture_output=True, text=True)
        
        logger.info(f"Extracted audio to: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg audio extraction failed: {e.stderr}")
        raise RuntimeError(f"Failed to extract audio from video: {e.stderr}") from e
    except FileNotFoundError:
        logger.error("FFmpeg not found. Please install FFmpeg.")
        raise RuntimeError("FFmpeg not installed")


def analyze_audio_features(audio_path: str, fallback_on_error: bool = True) -> Dict[str, Any]:
    """
    Extract vocal features using Librosa.
    
    Args:
        audio_path: Path to audio file (WAV preferred)
        fallback_on_error: If True, return empty data on error instead of raising
    
    Returns:
        Dict with voice_activity_segments, pitch_timeline, vocal_features, audio_quality
    
    Raises:
        FileNotFoundError: If fallback_on_error is False and file not found
    """
    audio_path_obj = Path(audio_path)
    if not audio_path_obj.exists():
        logger.warning(f"Audio file not found: {audio_path}")
        if fallback_on_error:
            return _get_empty_audio_result()
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    try:
        logger.info(f"Starting audio analysis: {audio_path}")
        
        y, sr = librosa.load(audio_path, sr=None)
        duration = len(y) / sr
        
        f0, voiced_flags, voiced_probs = librosa.pyin(
            y, fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=sr
        )
        
        voice_activity = _detect_voice_activity(y, sr)
        pitch_timeline = _build_pitch_timeline(f0, sr)
        vocal_features = _extract_vocal_features(y, sr, f0, voiced_flags, duration)
        audio_quality = _assess_audio_quality(y, sr)
        
        logger.info(f"Audio analysis complete: {duration:.1f}s, {vocal_features['speech_rate_wpm']} WPM")
        
        return {
            "voice_activity_segments": voice_activity,
            "pitch_timeline": pitch_timeline,
            "vocal_features": vocal_features,
            "audio_quality": audio_quality
        }
    except Exception as e:
        logger.error(f"Audio analysis failed for {audio_path}: {e}")
        if fallback_on_error:
            return _get_empty_audio_result()
        raise RuntimeError(f"Audio analysis failed: {e}") from e


def _get_empty_audio_result() -> Dict[str, Any]:
    """Return empty audio analysis result for error cases."""
    return {
        "voice_activity_segments": [],
        "pitch_timeline": [],
        "vocal_features": {
            "mean_pitch_hz": 0,
            "pitch_range_hz": {"min": 0, "max": 0},
            "pitch_variability_std": 0,
            "speech_rate_wpm": 0,
            "pause_count": 0,
            "mean_pause_duration_sec": 0,
            "vocal_emotion_indicators": {"arousal": 0, "valence": 0, "dominance": 0},
        },
        "audio_quality": {"sample_rate": 44100, "snr_db": 0},
    }


def _detect_voice_activity(y: np.ndarray, sr: int) -> List[Dict]:
    """Detect voice activity segments using energy-based VAD."""
    frame_length = int(0.025 * sr)
    hop_length = int(0.010 * sr)
    
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    threshold = np.mean(rms) * 0.5
    
    segments = []
    in_voice = False
    start_time = 0.0
    
    times = librosa.times_like(rms, sr=sr, hop_length=hop_length)
    
    for i, (t, energy) in enumerate(zip(times, rms)):
        if energy > threshold and not in_voice:
            start_time = t
            in_voice = True
        elif energy <= threshold and in_voice:
            segments.append({"start": round(start_time, 2), "end": round(t, 2), "active": True})
            segments.append({"start": round(t, 2), "end": round(t, 2), "active": False})
            in_voice = False
    
    if in_voice and len(times) > 0:
        segments.append({"start": round(start_time, 2), "end": round(times[-1], 2), "active": True})
    
    return segments


def _build_pitch_timeline(f0: np.ndarray, sr: int) -> List[Dict]:
    """Build pitch timeline from F0 contour."""
    times = librosa.times_like(f0, sr=sr, hop_length=512)
    
    timeline = []
    for t, pitch in zip(times, f0):
        if not np.isnan(pitch) and pitch > 0:
            note = librosa.hz_to_note(pitch)
            timeline.append({
                "timestamp": round(t, 2),
                "hz": round(float(pitch), 1),
                "note": note
            })
    
    if len(timeline) > 50:
        step = len(timeline) // 50
        timeline = timeline[::step]
    
    return timeline[:50]


def _extract_vocal_features(
    y: np.ndarray, sr: int, 
    f0: np.ndarray, voiced: np.ndarray,
    duration: float
) -> Dict[str, Any]:
    """Extract comprehensive vocal features."""
    
    valid_f0 = f0[~np.isnan(f0)]
    mean_pitch = float(np.mean(valid_f0)) if len(valid_f0) > 0 else 0
    pitch_std = float(np.std(valid_f0)) if len(valid_f0) > 0 else 0
    
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    syllable_count = len(onset_times)
    speech_rate_wpm = int((syllable_count / 1.5) / (duration / 60)) if duration > 0 else 0
    
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_mean = [round(float(x), 2) for x in np.mean(mfccs, axis=1)]
    
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    zcr = librosa.feature.zero_crossing_rate(y)
    
    voiced_duration = np.sum(voiced) * 512 / sr if voiced is not None else 0
    pause_count = _count_pauses(voiced)
    
    return {
        "mean_pitch_hz": round(mean_pitch, 1),
        "pitch_range_hz": {
            "min": round(float(np.min(valid_f0)), 1) if len(valid_f0) > 0 else 0,
            "max": round(float(np.max(valid_f0)), 1) if len(valid_f0) > 0 else 0
        },
        "pitch_variability_std": round(pitch_std, 1),
        "speech_rate_wpm": speech_rate_wpm,
        "speech_rate_syllables_per_sec": round(syllable_count / duration, 2) if duration > 0 else 0,
        "total_duration_sec": round(duration, 2),
        "voiced_duration_sec": round(voiced_duration, 2),
        "pause_count": pause_count,
        "mean_pause_duration_sec": 0.5,
        "total_pause_duration_sec": round(duration - voiced_duration, 2),
        "energy_mean": round(float(np.mean(np.abs(y))), 6),
        "energy_std": round(float(np.std(np.abs(y))), 6),
        "spectral_centroid_mean": round(float(np.mean(spectral_centroid)), 1),
        "zero_crossing_rate": round(float(np.mean(zcr)), 4),
        "mfcc_features": mfcc_mean,
        "chroma_features": [],
        "vocal_emotion_indicators": {
            "arousal": round(min(pitch_std / 50, 1.0), 2),
            "valence": 0.5,
            "dominance": 0.5
        },
        "audio_embeddings": []
    }


def _count_pauses(voiced: np.ndarray) -> int:
    """Count number of pauses in voice activity."""
    if voiced is None:
        return 0
    pauses = 0
    in_pause = False
    for v in voiced:
        if not v and not in_pause:
            pauses += 1
            in_pause = True
        elif v:
            in_pause = False
    return pauses


def _assess_audio_quality(y: np.ndarray, sr: int) -> Dict[str, Any]:
    """Assess audio quality metrics."""
    clipping = np.sum(np.abs(y) > 0.99) / len(y)
    noise_floor = np.percentile(np.abs(y), 10)
    signal_level = np.percentile(np.abs(y), 90)
    snr_db = 20 * np.log10(signal_level / (noise_floor + 1e-10)) if noise_floor > 0 else 0
    
    return {
        "sample_rate": int(sr),
        "bit_depth": 16,
        "snr_db": round(snr_db, 1),
        "clipping_detected": clipping > 0.01
    }
