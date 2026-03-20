# Resonance — Oral Narrative Preservation System
### A Multimodal AI Platform for Digital Heritage

---

## Quick Start

```bash
# Start everything (PostgreSQL, Redis, API, Frontend)
docker compose up -d

# View logs
docker compose logs -f api

# Open in browser
open http://localhost
```

The system automatically seeds 5 sample narratives on first run.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User's Browser                        │
│                  http://localhost                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Nginx (port 80)                       │
│  ┌─────────────────┐  ┌──────────────────────────────┐ │
│  │ /               │  │ /api/*                       │ │
│  │ Frontend files  │  │ Proxy to api:8000            │ │
│  └─────────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (port 8000)                │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Async SQLAlchemy ORM                               │ │
│  │ - Narrative, Theme, Transcript models              │ │
│  │ - NarratorProfile, FacialAnalysis models           │ │
│  │ - VocalAnalysis, MultimodalFusion models           │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│   PostgreSQL     │          │      Redis       │
│  (Docker volume) │          │  (Future: Celery)│
│  ✅ Persistent   │          │  ✅ Ready        │
└──────────────────┘          └──────────────────┘
```

---

## Project Structure

```
oral-narrative-project/
├── docker-compose.yml          # Docker orchestration
├── nginx/
│   └── nginx.conf              # Nginx reverse proxy config
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── model.py                # PyTorch multimodal fusion model
│   ├── config.py               # Environment configuration
│   ├── requirements.txt        # Python dependencies
│   ├── db/
│   │   └── init.sql            # PostgreSQL schema
│   ├── app/
│   │   ├── routers/            # API route handlers
│   │   │   ├── narratives.py
│   │   │   ├── upload.py
│   │   │   ├── search.py
│   │   │   └── stats.py
│   │   ├── services/           # Business logic
│   │   │   ├── narrative_service.py
│   │   │   ├── upload_service.py
│   │   │   ├── search_service.py
│   │   │   ├── stats_service.py
│   │   │   ├── facial_service.py
│   │   │   ├── audio_service.py
│   │   │   ├── fusion_service.py
│   │   │   └── archive_service.py
│   │   ├── models/             # SQLAlchemy ORM models
│   │   │   └── narrative.py
│   │   └── core/               # Core utilities
│   │       ├── database.py
│   │       └── seed.py
│   ├── tests/                  # Pytest tests
│   └── storage/                # Created at runtime
│       ├── videos/             # Uploaded video files
│       ├── audio/              # Extracted audio tracks
│       ├── archives/           # JSON archive entries
│       └── thumbnails/         # Video thumbnails
├── frontend/
│   ├── index.html              # Main HTML entry point
│   ├── css/                    # Stylesheets
│   └── js/                     # JavaScript modules
└── scripts/                    # Helper scripts
    ├── start-db.sh
    ├── stop-db.sh
    └── reset-db.sh
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

### Multimodal Fusion
- **PyTorch 2.x** — CrossAttention Transformer (3 fusion layers)
  - FacialEncoder: Linear projection + MultiheadAttention over frames
  - AudioEncoder: Conv1D + MultiheadAttention over audio segments
  - CrossModalAttention: Bidirectional face↔audio attention
  - EmotionHead: 7-class classification (joy/sadness/anger/fear/surprise/disgust/neutral)
  - NarratorIdentityHead: 512-dim L2-normalized embedding
- **scikit-learn** — StandardScaler, PCA, KMeans narrator clustering

### Transcription (ASR)
- **OpenAI Whisper** (large-v3) — word-level timestamps, multilingual

---

## Docker Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View API logs
docker compose logs -f api

# Reset database (WARNING: deletes all data)
docker compose down -v && docker compose up -d

# Connect to PostgreSQL
docker exec -it oral-narratives-db psql -U narrator -d oral_narratives

# Rebuild containers after code changes
docker compose build api && docker compose up -d api
```

---

## Development (Without Docker)

```bash
# 1. Start only the database
docker compose up -d db redis

# 2. Install dependencies
cd backend
pip install -r requirements.txt

# 3. Set environment variables
export DATABASE_URL=postgresql://narrator:narrator123@localhost:5432/oral_narratives

# 4. Run API server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 5. Serve frontend
python -m http.server 80 --directory frontend/

# 6. API documentation
open http://localhost:8000/docs
```

---

## Database Schema

| Table | Description |
|-------|-------------|
| `narratives` | Main narrative records |
| `themes` | Theme tags (many-to-many with narratives) |
| `narrative_themes` | Junction table |
| `transcripts` | ASR transcripts |
| `narrator_profiles` | Facial identity data |
| `facial_analysis` | Emotion timelines |
| `vocal_analysis` | Audio features |
| `multimodal_fusion` | Fused multimodal data |

---

## Testing

```bash
cd backend

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_narratives.py
```

Tests use an in-memory SQLite database for isolation.

---

## Production Notes

Current implementation status:

| Feature | Status |
|---------|--------|
| PostgreSQL persistence | ✅ Complete |
| Async SQLAlchemy | ✅ Complete |
| Nginx reverse proxy | ✅ Complete |
| Docker volumes | ✅ Complete |
| Real ML implementations | ✅ Complete |
| Celery task queue | 🔴 Redis ready, Celery not implemented |
| JWT authentication | 🔴 Not implemented |
| FAISS vector search | 🔴 Not implemented |

---

*"Every oral tradition carries the full weight of its teller — their identity, their trembling voice, the flash of sorrow or joy across their face. Resonance preserves all of it."*
