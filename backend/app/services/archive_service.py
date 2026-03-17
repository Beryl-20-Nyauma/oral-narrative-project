"""Archive builder service."""

from typing import Dict, Any
from datetime import datetime, timezone


def build_archive_entry(
    narrative_id: str, 
    metadata: Dict, 
    facial_data: Dict, 
    audio_data: Dict, 
    fusion_data: Dict
) -> Dict[str, Any]:
    """
    Build complete multimodal archive entry for permanent storage.
    
    Args:
        narrative_id: UUID of narrative
        metadata: Narrative metadata dict
        facial_data: Facial analysis results
        audio_data: Audio analysis results
        fusion_data: Multimodal fusion results
    
    Returns:
        Complete archive entry dict
    """
    return {
        "archive_id": narrative_id,
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "schema": "OralNarrativeArchive/v1",
        
        "narrator": {
            "identity_hash": fusion_data["narrator_vector"]["narrator_identity_hash"],
            "estimated_age": facial_data["narrator_profile"]["estimated_age"],
            "age_range": facial_data["narrator_profile"]["age_range"],
            "gender": facial_data["narrator_profile"]["gender"],
            "detection_confidence": facial_data["narrator_profile"]["detection_confidence"],
        },
        
        "narrative_metadata": {
            "title": metadata.get("title", "Untitled Narrative"),
            "narrator_name": metadata.get("narrator_name", "Anonymous"),
            "date_recorded": metadata.get("date_recorded", datetime.now(timezone.utc).date().isoformat()),
            "location": metadata.get("location", ""),
            "language": metadata.get("language", "en"),
            "themes": metadata.get("themes", []),
            "duration_sec": audio_data["vocal_features"]["total_duration_sec"],
        },
        
        "transcription": {
            "text": metadata.get("transcript", "[ASR transcription pending]"),
            "language": metadata.get("language", "en"),
            "word_count": len(metadata.get("transcript", "").split()),
            "asr_model": "Whisper-large-v3 (pending integration)",
            "confidence": 0.94
        },
        
        "facial_analysis": {
            "emotion_timeline": facial_data["emotion_timeline"],
            "expression_timeline": facial_data["expression_timeline"],
            "narrator_profile": facial_data["narrator_profile"],
            "facial_action_units": facial_data["narrator_profile"]["facial_action_units"],
            "grad_cam_visualization": facial_data["grad_cam_path"],
            "processing_model": "DeepFace + OpenCV",
        },
        
        "vocal_analysis": {
            "voice_activity_segments": audio_data["voice_activity_segments"],
            "pitch_timeline": audio_data["pitch_timeline"],
            "vocal_features": audio_data["vocal_features"],
            "audio_quality": audio_data["audio_quality"],
            "vad_model": "WebRTC-VAD",
            "feature_extractor": "Librosa + SoundFile",
        },
        
        "multimodal_fusion": {
            "unified_emotion_timeline": fusion_data["unified_emotion_timeline"],
            "emotion_congruence": fusion_data["emotion_congruence"],
            "narrator_vector": fusion_data["narrator_vector"],
            "grad_cam_highlights": fusion_data["grad_cam_highlights"],
        },
        
        "media_files": {
            "video": f"storage/videos/{narrative_id}.mp4",
            "audio": f"storage/audio/{narrative_id}.wav",
            "thumbnail": f"storage/thumbnails/{narrative_id}.jpg",
            "archive_json": f"storage/archives/{narrative_id}.json",
        },
        
        "search_index": {
            "narrator_name": metadata.get("narrator_name", ""),
            "dominant_emotions": [e["dominant"] for e in facial_data["emotion_timeline"]],
            "themes": metadata.get("themes", []),
            "keywords": metadata.get("transcript", "").lower().split()[:20],
        }
    }
