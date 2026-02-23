# Resonance — Oral Narrative Preservation System
### A Multimodal AI Platform for Digital Heritage

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        RESONANCE SYSTEM OVERVIEW                          │
├─────────────────┬──────────────────────────────┬────────────────────────┤
│   INPUT LAYER   │     PROCESSING PIPELINE       │    OUTPUT / STORAGE    │
├─────────────────┼──────────────────────────────┼────────────────────────┤
│                 │                              │                        │
│  📹 Video       │  OpenCV → Frame extraction   │  🗄 Archive Entry:     │
│  Upload /       │  DeepFace → Facial attrs     │    • narrator_id       │
│  Recording      │   • Identity embedding        │    • emotion_timeline  │
│                 │   • Emotion distribution      │    • expression_log    │
│                 │   • Age / Gender              │    • facial_action_u.  │
│                 │   • Facial Action Units       │    • voice_features    │
│                 │   • Per-frame expression      │    • transcript        │
│                 │                              │    • grad_cam image    │
│  🎙 Audio       │  WebRTC-VAD → Segments       │    • narrator_vector   │
│  Extraction     │  Librosa + SoundFile →       │    • timestamp index   │
│  (from video)   │   • Pitch (F0) contour        │    • media files       │
│                 │   • MFCC fingerprint          │                        │
│                 │   • Speech rate / pauses      │  🔍 Search Index:     │
│                 │   • Energy / spectral         │    • narrator_name     │
│                 │   • VAD arousal/valence       │    • emotions          │
│                 │   • 128-dim audio embedding   │    • themes            │
│                 │                              │    • keywords          │
│  📝 Transcript  │  Whisper ASR (pending)        │                        │
│  (optional      │  → Word-level timestamps      │  📊 Analytics:        │
│   manual input) │  → Speaker diarization        │    • narrator cluster  │
│                 │                              │    • emotion heatmap   │
│                 │  ────────────────────────     │    • collection stats  │
│                 │                              │                        │
│                 │  PyTorch CrossAttn Fusion     │                        │
│                 │   • FacialEncoder [512→256]   │                        │
│                 │   • AudioEncoder [128→256]    │                        │
│                 │   • CrossModalAttention ×3    │                        │
│                 │   • EmotionHead → 7 classes   │                        │
│                 │   • IdentityHead → 512-emb    │                        │
│                 │                              │                        │
│                 │  pytorch-grad-cam             │                        │
│                 │   → Facial region saliency    │                        │
│                 │                              │                        │
│                 │  scikit-learn                 │                        │
│                 │   → Feature scaling           │                        │
│                 │   → PCA dimensionality red.   │                        │
│                 │   → Narrator clustering       │                        │
└─────────────────┴──────────────────────────────┴────────────────────────┘
```

---

## Project Structure

```
oral_narrative_system/
├── backend/
│   ├── main.py              # FastAPI application + REST endpoints
│   ├── model.py             # PyTorch multimodal fusion model
│   ├── requirements.txt     # All Python dependencies
│   └── storage/
│       ├── videos/          # Uploaded MP4/MOV files
│       ├── audio/           # Extracted WAV audio tracks
│       ├── thumbnails/      # Video thumbnail images
│       └── archives/        # JSON archive entries
│
├── frontend/
│   └── index.html           # Complete single-file frontend app
│
└── README.md
```

---

## REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/narratives` | List all narratives (filter by narrator, emotion, theme) |
| `GET`  | `/api/narratives/{id}` | Get complete archive entry |
| `POST` | `/api/narratives/upload` | Upload video + trigger analysis pipeline |
| `GET`  | `/api/narratives/{id}/status` | Check processing progress |
| `GET`  | `/api/narratives/{id}/emotion-timeline` | Synchronized emotion data |
| `GET`  | `/api/narratives/{id}/narrator-profile` | Identity + vocal profile |
| `GET`  | `/api/search?q=...&field=...` | Full-text search |
| `GET`  | `/api/stats` | System-wide analytics |

---

## AI Processing Stack

### Video / Facial Analysis
- **OpenCV** — frame extraction, face detection (Haar cascade / DNN)
- **DeepFace** — facial embeddings, emotion, age, gender, FACS action units
- **pytorch-grad-cam** — visualize which facial regions drive emotion classification

### Audio / Vocal Analysis
- **WebRTC-VAD** — real-time voice activity detection
- **Librosa** — pitch (PYIN), MFCC (13-128 coefficients), spectral centroid, chroma, ZCR
- **SoundFile** — audio I/O in WAV/FLAC formats
- **PyAudio** — microphone capture for live recording (optional)

### Multimodal Fusion
- **PyTorch 2.x** — CrossAttention Transformer (3 fusion layers)
  - FacialEncoder: Linear projection + MultiheadAttention over frames
  - AudioEncoder: Conv1D + MultiheadAttention over audio segments
  - CrossModalAttention: Bidirectional face↔audio attention
  - EmotionHead: 7-class classification (joy/sadness/anger/fear/surprise/disgust/neutral)
  - NarratorIdentityHead: 512-dim L2-normalized embedding
- **scikit-learn** — StandardScaler, PCA, KMeans narrator clustering
- **NumPy + pandas** — feature matrix construction, timeline alignment

### Transcription (ASR)
- **OpenAI Whisper** (large-v3) — word-level timestamps, multilingual
- Speaker diarization: pyannote.audio (optional integration)

---

## Archive Entry Schema (JSON)

```json
{
  "archive_id": "uuid4",
  "version": "1.0",
  "created_at": "ISO-8601",
  "schema": "OralNarrativeArchive/v1",
  
  "narrator": {
    "identity_hash": "16-char hex",
    "estimated_age": 52,
    "age_range": "45-60",
    "gender": "woman",
    "detection_confidence": 0.947
  },
  
  "narrative_metadata": {
    "title": "The Day the River Flooded",
    "narrator_name": "Kirongosi  A",
    "date_recorded": "2024-01-15",
    "location": "Kakamega, Kenya",
    "language": "en",
    "themes": ["memory", "water", "community"],
    "duration_sec": 874
  },
  
  "transcription": {
    "text": "Full ASR output…",
    "word_count": 312,
    "asr_model": "whisper-large-v3",
    "confidence": 0.94
  },
  
  "facial_analysis": {
    "emotion_timeline": [/* per-segment emotion probs */],
    "expression_timeline": [/* smiling, frowning, eyebrow… */],
    "narrator_profile": {/* aggregate stats */},
    "facial_action_units": {/* AU1, AU2, AU4, AU6, AU12… */},
    "grad_cam_visualization": "path/to/heatmap.png"
  },
  
  "vocal_analysis": {
    "voice_activity_segments": [/* VAD timeline */],
    "pitch_timeline": [/* F0 contour */],
    "vocal_features": {
      "mean_pitch_hz": 198.4,
      "speech_rate_wpm": 127,
      "pause_count": 3,
      "mfcc_features": [/* 13-dim */],
      "audio_embeddings": [/* 128-dim */],
      "vocal_emotion_indicators": {"arousal": 0.62, "valence": 0.71}
    }
  },
  
  "multimodal_fusion": {
    "unified_emotion_timeline": [/* face+voice synchronized */],
    "emotion_congruence": {
      "facial_vocal_agreement_score": 0.78,
      "interpretation": "High emotional authenticity"
    },
    "narrator_vector": {
      "fused_vector_dim": 640,
      "model_architecture": "CrossAttention Fusion Transformer"
    },
    "grad_cam_highlights": {
      "high_attention_regions": ["eye area", "mouth corners"]
    }
  },
  
  "media_files": {
    "video": "storage/videos/{id}.mp4",
    "audio": "storage/audio/{id}.wav",
    "thumbnail": "storage/thumbnails/{id}.jpg",
    "archive_json": "storage/archives/{id}.json"
  }
}
```

---

## PyTorch Model Architecture

```
MultimodalNarratorModel
├── FacialEncoder
│   ├── Linear(512 → 512) + LayerNorm + GELU + Dropout
│   ├── Linear(512 → 256) + LayerNorm
│   └── MultiheadAttention(256, heads=4) — temporal self-attention
│
├── AudioEncoder
│   ├── Conv1D(128→256, k=3) + BatchNorm + GELU
│   ├── Conv1D(256→256, k=5) + BatchNorm + GELU
│   └── MultiheadAttention(256, heads=4) — temporal self-attention
│
├── FusionLayers × 3 (CrossModalAttention)
│   ├── face_to_audio: MHA(256, heads=8) — face queries audio
│   ├── audio_to_face: MHA(256, heads=8) — audio queries face
│   └── FFN × 2 (hidden_dim × 4 expansion)
│
├── EmotionClassificationHead
│   ├── AdaptiveAvgPool1D → [B, 256] per modality
│   ├── Concat → [B, 512]
│   ├── Linear(512→256) + LayerNorm + GELU + Dropout
│   └── Linear(256→7) → emotion logits
│
└── NarratorIdentityHead
    ├── Mean pooling → [B, 512]
    ├── Linear(512→512) + GELU
    └── L2 normalize → 512-dim narrator embedding
    
Total parameters: ~4.2M
Grad-CAM target: FusionLayers[-1].face_to_audio
```

---

## Setup & Running

```bash
# 1. Clone and install
cd backend
pip install -r requirements.txt

# 2. Run API server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. Open frontend
open frontend/index.html
# Or serve statically:
python -m http.server 3000 --directory frontend/

# 4. API documentation
open http://localhost:8000/docs   # Swagger UI
```

---

## Production Deployment Notes

- **Media Storage**: Replace local filesystem with AWS S3 / GCS for scalability
- **Database**: Replace in-memory dict with PostgreSQL + pgvector for narrator embedding search
- **Processing Queue**: Use Celery + Redis for async heavy video processing jobs
- **Real-time Streaming**: WebSocket endpoint for live recording with frame-by-frame emotion feedback
- **Security**: Add JWT authentication for multi-user archive access control
- **Scale**: GPU-accelerated DeepFace + PyTorch inference via CUDA

---

*"Every oral tradition carries the full weight of its teller — their identity, their trembling voice, the flash of sorrow or joy across their face. Resonance preserves all of it."*
