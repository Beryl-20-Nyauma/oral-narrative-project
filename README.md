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

### Narratives
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/narratives` | List all narratives (filter by narrator, emotion, theme) |
| `GET`  | `/api/narratives/{id}` | Get complete archive entry |
| `POST` | `/api/narratives/upload` | Upload video + trigger analysis pipeline |
| `GET`  | `/api/narratives/{id}/status` | Check processing progress |
| `GET`  | `/api/narratives/{id}/emotion-timeline` | Synchronized emotion data |
| `GET`  | `/api/narratives/{id}/narrator-profile` | Identity + vocal profile |
| `POST` | `/api/narratives/retry/{id}` | Retry failed processing |

### Narrators
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/narrators` | List all narrators |
| `GET`  | `/api/narrators/{id}` | Get narrator details |
| `POST` | `/api/narrators/register` | Register narrator with reference image |
| `POST` | `/api/narrators/identify` | Identify narrator from video/image |
| `POST` | `/api/narrators/rebuild-index` | Rebuild FAISS index |
| `PATCH` | `/api/narrators/{id}` | Rename narrator |
| `GET`  | `/api/narrators/{id}/narratives` | Get narrator's narratives |

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register new user |
| `POST` | `/api/auth/login` | Login (OAuth2 form) |
| `GET`  | `/api/auth/me` | Get current user |
| `POST` | `/api/auth/logout` | Logout |

### Search & Stats
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/search?q=...&field=...` | Full-text search |
| `GET`  | `/api/stats` | System-wide analytics |
| `GET`  | `/api/stats/benchmark` | Performance benchmarks |
| `GET`  | `/api/stats/health` | Health check with GPU info |

### Queue (Async Processing)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/queue/status` | Celery workers and queue status |
| `GET`  | `/api/queue/tasks/{task_id}` | Get task status |
| `POST` | `/api/queue/retry/{narrative_id}` | Retry failed task |

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

### Narrator Identification
- **FAISS** — Vector similarity search for face embeddings
  - IndexFlatIP for inner product similarity
  - 512-dimensional face embeddings from DeepFace
  - Auto-discovery of new narrators
  - Persistent index with mapping to database IDs

### Narrator Identification
- **FAISS** — Vector similarity search for face embeddings
- **DeepFace** — Face embedding extraction (512-dim vectors)
- Auto-discovery of returning narrators across videos

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
| `users` | User accounts (email, hashed password, admin flag) |
| `narrators` | Known narrators with face embeddings |
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

## Configuration

Environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `USE_SQLITE` | false | Use SQLite instead of PostgreSQL |
| `REDIS_URL` | — | Redis connection for Celery/rate limiting |
| `SECRET_KEY` | (dev key) | JWT signing key |
| `WHISPER_MODEL` | base | Whisper model (tiny/base/small/medium/large) |
| `WHISPER_DEVICE` | cpu | Device for Whisper (cpu/cuda) |
| `ENABLE_FACIAL_ANALYSIS` | true | Enable facial analysis |
| `ENABLE_AUDIO_ANALYSIS` | true | Enable audio analysis |
| `ENABLE_TRANSCRIPTION` | true | Enable ASR transcription |
| `ENABLE_FAISS_INDEXING` | true | Enable FAISS narrator matching |
| `RATE_LIMIT_ENABLED` | true | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | 100 | Max requests per window |
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_FORMAT` | console | Log format (console/json) |

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
| Celery task queue | ✅ Complete (Redis + Celery workers) |
| JWT authentication | ✅ Complete (register/login/me/logout) |
| FAISS vector search | ✅ Complete (narrator face matching) |
| Rate limiting | ✅ Complete (Redis-based) |
| Narrator identification | ✅ Complete (face recognition) |
| Performance benchmarks | ✅ Complete |
| GPU detection | ✅ Complete |

---

*"Every oral tradition carries the full weight of its teller — their identity, their trembling voice, the flash of sorrow or joy across their face. Resonance preserves all of it."*
