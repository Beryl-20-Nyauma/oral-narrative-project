"""Quick test script for ML services."""

import sys
sys.path.insert(0, '.')

from app.services.facial_service import analyze_facial_features
from app.services.audio_service import analyze_audio_features, extract_audio_from_video
from app.services.transcription_service import WhisperTranscriber
from app.services.fusion_service import fuse_multimodal_features


def test_pipeline(video_path: str):
    """Test full pipeline on a video."""
    print(f"Testing: {video_path}")
    
    audio_path = video_path.replace('.mp4', '.wav')
    print("Extracting audio...")
    extract_audio_from_video(video_path, audio_path)
    
    print("Analyzing facial features...")
    facial_data = analyze_facial_features(video_path)
    print(f"  - Detected {facial_data['narrator_profile']['face_detected_frames']} frames with faces")
    
    print("Analyzing audio...")
    audio_data = analyze_audio_features(audio_path)
    print(f"  - Duration: {audio_data['vocal_features']['total_duration_sec']}s")
    print(f"  - Speech rate: {audio_data['vocal_features']['speech_rate_wpm']} WPM")
    
    print("Transcribing...")
    transcription = WhisperTranscriber.transcribe(audio_path)
    print(f"  - Text: {transcription['text'][:100]}...")
    print(f"  - Words: {transcription['word_count']}")
    
    print("Fusing modalities...")
    fusion_data = fuse_multimodal_features(facial_data, audio_data, transcription['text'])
    print(f"  - Congruence score: {fusion_data['emotion_congruence']['facial_vocal_agreement_score']}")
    
    print("\n✅ Pipeline test complete!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_pipeline(sys.argv[1])
    else:
        print("Usage: python test_ml_services.py <video_path>")
