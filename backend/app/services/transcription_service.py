"""Transcription service using faster-whisper (CTranslate2)."""

import logging
import threading
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Production-grade Whisper ASR transcription service.
    
    Uses faster-whisper (CTranslate2) for better performance and smaller footprint.
    Thread-safe singleton with lazy loading.
    """
    
    _model = None
    _model_name: str = "base"
    _device: str = "cpu"
    _compute_type: str = "int8"
    _lock: threading.Lock = threading.Lock()
    _configured: bool = False
    
    VALID_MODELS = ("tiny", "base", "small", "medium", "large-v2", "large-v3")
    
    @classmethod
    def configure_from_settings(cls) -> None:
        """Load configuration from settings."""
        if cls._configured:
            return
        try:
            from config import get_settings
            settings = get_settings()
            cls._model_name = settings.whisper_model
            cls._device = settings.whisper_device
            cls._compute_type = settings.whisper_compute_type
            cls._configured = True
            logger.info(f"Whisper configured: model={cls._model_name}, device={cls._device}, compute_type={cls._compute_type}")
        except Exception as e:
            logger.warning(f"Could not load settings, using defaults: {e}")
    
    @classmethod
    def set_model_name(cls, model_name: str) -> None:
        """
        Set the model name to use. Must be called before first transcription.
        
        Args:
            model_name: One of tiny, base, small, medium, large-v2, large-v3
        """
        if model_name not in cls.VALID_MODELS:
            raise ValueError(f"Invalid model '{model_name}'. Must be one of {cls.VALID_MODELS}")
        if cls._model is not None:
            logger.warning("Model already loaded. set_model_name() has no effect.")
            return
        cls._model_name = model_name
        logger.info(f"Whisper model set to: {model_name}")
    
    @classmethod
    def get_model(cls):
        """
        Get or lazily load the faster-whisper model.
        
        Thread-safe singleton initialization.
        
        Returns:
            Loaded faster-whisper WhisperModel instance
        """
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    if not cls._configured:
                        cls.configure_from_settings()
                    
                    from faster_whisper import WhisperModel
                    logger.info(f"Loading faster-whisper model: {cls._model_name}")
                    cls._model = WhisperModel(
                        cls._model_name,
                        device=cls._device,
                        compute_type=cls._compute_type
                    )
                    logger.info(f"faster-whisper model loaded successfully")
        return cls._model
    
    @classmethod
    def is_loaded(cls) -> bool:
        """Check if model is already loaded."""
        return cls._model is not None
    
    @classmethod
    def transcribe(
        cls,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        temperature: float = 0.0,
        best_of: int = 5,
        beam_size: int = 5,
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using faster-whisper ASR.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, M4A, etc.)
            language: Optional ISO 639-1 language code (e.g., 'en', 'sw', 'fr')
                      If None, Whisper will auto-detect language.
            task: Either "transcribe" or "translate" (translate to English)
            temperature: Sampling temperature (0.0 = greedy, higher = more random)
            best_of: Number of candidates for best-of sampling
            beam_size: Beam search width (higher = slower but more accurate)
        
        Returns:
            Dict containing:
                - text: Full transcription text
                - word_count: Number of words transcribed
                - language: Detected/specified language code
                - language_probability: Confidence in language detection
                - segments: List of timestamped segments
                - confidence: Overall transcription confidence (0.0-1.0)
                - duration_sec: Total audio duration
                - model: Model name used for transcription
        
        Raises:
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If transcription fails
        """
        import os
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Starting transcription: {audio_path}")
        logger.debug(f"Language: {language or 'auto-detect'}, Task: {task}")
        
        try:
            model = cls.get_model()
            
            segments_gen, info = model.transcribe(
                audio_path,
                language=language,
                task=task,
                temperature=temperature,
                best_of=best_of,
                beam_size=beam_size,
            )
            
            segments = cls._process_segments(list(segments_gen))
            
            text = " ".join(seg["text"] for seg in segments)
            word_count = len(text.split())
            
            language_code = info.language if hasattr(info, 'language') else language or "unknown"
            language_prob = info.language_probability if hasattr(info, 'language_probability') else 1.0
            
            confidence = cls._calculate_confidence(segments)
            duration_sec = segments[-1]["end"] if segments else 0.0
            
            logger.info(
                f"Transcription complete: {word_count} words, "
                f"{duration_sec:.1f}s duration, {language_code} ({confidence:.2f} confidence)"
            )
            
            return {
                "text": text,
                "word_count": word_count,
                "language": language_code,
                "language_probability": round(language_prob, 3),
                "segments": segments,
                "confidence": confidence,
                "duration_sec": round(duration_sec, 2),
                "model": f"faster-whisper-{cls._model_name}",
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {e}") from e
    
    @classmethod
    def _process_segments(cls, segments: List) -> List[Dict[str, Any]]:
        """
        Process raw faster-whisper segments into clean format.
        
        Args:
            segments: Raw segments from faster-whisper output
        
        Returns:
            Cleaned list of segment dicts with start, end, text, confidence
        """
        processed = []
        for seg in segments:
            if not seg.text or not seg.text.strip():
                continue
            
            start = round(seg.start, 2)
            end = round(seg.end, 2)
            text = seg.text.strip()
            
            avg_logprob = getattr(seg, 'avg_logprob', -0.5)
            no_speech_prob = getattr(seg, 'no_speech_prob', 0.0)
            confidence = cls._segment_confidence(avg_logprob, no_speech_prob)
            
            processed.append({
                "start": start,
                "end": end,
                "text": text,
                "confidence": round(confidence, 3),
                "tokens": list(seg.tokens) if hasattr(seg, 'tokens') else [],
            })
        
        return processed
    
    @classmethod
    def _calculate_confidence(cls, segments: List[Dict]) -> float:
        """
        Calculate overall transcription confidence from segment metrics.
        
        Args:
            segments: Processed segments
        
        Returns:
            Confidence score between 0 and 1
        """
        if not segments:
            return 0.0
        
        confidences = [seg.get("confidence", 0.5) for seg in segments]
        return round(sum(confidences) / len(confidences), 2)
    
    @classmethod
    def _segment_confidence(cls, avg_logprob: float, no_speech_prob: float) -> float:
        """
        Calculate confidence for a single segment.
        
        Args:
            avg_logprob: Average log probability of tokens
            no_speech_prob: Probability that segment contains no speech
        
        Returns:
            Segment confidence between 0 and 1
        """
        logprob_score = (avg_logprob + 1) / 1
        logprob_score = max(0.0, min(1.0, logprob_score))
        
        speech_score = 1.0 - no_speech_prob
        
        confidence = 0.7 * logprob_score + 0.3 * speech_score
        return max(0.0, min(1.0, confidence))


def transcribe_audio(
    audio_path: str,
    language: Optional[str] = None,
    model: str = "base",
) -> Dict[str, Any]:
    """
    Convenience function for audio transcription.
    
    Args:
        audio_path: Path to audio file
        language: Optional language code (e.g., 'en', 'sw')
        model: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
    
    Returns:
        Transcription result dict
    """
    WhisperTranscriber.set_model_name(model)
    return WhisperTranscriber.transcribe(audio_path, language=language)
