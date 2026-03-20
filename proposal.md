# Oral Narrative Preservation System

A multimodal AI platform for archiving oral histories with facial analysis, voice features, and emotion detection.

---

## 1. Project Summary

Develop a production-ready system to capture, analyze, and archive oral narratives from video recordings. The system extracts facial features, vocal characteristics, and performs multimodal emotion fusion to create rich, searchable archives of African oral histories.

---

## 2. Scope of Work

### Completed ✅

| Feature | Status |
|---------|--------|
| PostgreSQL persistence | ✅ Done |
| Async SQLAlchemy ORM | ✅ Done |
| Docker Compose orchestration | ✅ Done |
| Nginx reverse proxy | ✅ Done |
| REST API endpoints | ✅ Done |
| Sample data seeding | ✅ Done |
| CI/CD pipeline | ✅ Done |
| Testing infrastructure | ✅ Done |

### ML Services ✅

| Feature | Status |
|---------|--------|
| Real facial analysis (OpenCV + DeepFace) | ✅ Complete |
| Real audio analysis (Librosa) | ✅ Complete |
| Real multimodal fusion | ✅ Complete |
| Whisper ASR transcription | ✅ Complete |
| Face recognition & identification | 🔴 Pending |
| Celery task queue | 🔴 Redis ready, Celery pending |

---

## 3. System Architecture

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
│  │ Processing Pipeline:                               │ │
│  │   Video → Frame Extraction → Facial Analysis       │ │
│  │        → Audio Extraction → Vocal Analysis         │ │
│  │        → ASR Transcription → Text                  │ │
│  │        → Multimodal Fusion → Archive Entry         │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│   PostgreSQL     │          │      Redis       │
│  (Persistent)    │          │  (Task Queue)    │
└──────────────────┘          └──────────────────┘
```

---

## 4. Components

### Backend Services

| Service | Purpose | Status |
|---------|---------|--------|
| `facial_service.py` | Face detection, emotion, age, gender | ✅ Complete |
| `audio_service.py` | Pitch, MFCC, speech rate, VAD | ✅ Complete |
| `fusion_service.py` | Cross-modal attention fusion | ✅ Complete |
| `transcription_service.py` | Whisper ASR transcription | ✅ Complete |
| `narrative_service.py` | CRUD operations | ✅ Working |
| `upload_service.py` | Video upload + pipeline trigger | ✅ Working |
| `search_service.py` | Full-text search | ✅ Working |
| `stats_service.py` | System analytics | ✅ Working |

### Database Models

| Model | Table | Description |
|-------|-------|-------------|
| `Narrative` | narratives | Main record |
| `Theme` | themes | Tags (many-to-many) |
| `Transcript` | transcripts | ASR output |
| `NarratorProfile` | narrator_profiles | Facial identity |
| `FacialAnalysis` | facial_analysis | Emotion timeline |
| `VocalAnalysis` | vocal_analysis | Audio features |
| `MultimodalFusion` | multimodal_fusion | Fused data |

---

## 5. API Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/narratives` | List all narratives | ✅ |
| GET | `/api/narratives/{id}` | Get single narrative | ✅ |
| POST | `/api/narratives/upload` | Upload video | ✅ |
| GET | `/api/narratives/{id}/status` | Check processing | ✅ |
| GET | `/api/narratives/{id}/emotion-timeline` | Emotion data | ✅ |
| GET | `/api/narratives/{id}/narrator-profile` | Identity profile | ✅ |
| GET | `/api/search` | Full-text search | ✅ |
| GET | `/api/stats` | System statistics | ✅ |
| POST | `/api/identify` | Face identification | 🔴 Pending |

---

## 6. Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.12+) |
| Database | PostgreSQL 15 + asyncpg |
| ORM | SQLAlchemy 2.0 (async) |
| Cache/Queue | Redis 7 (Celery pending) |
| Proxy | Nginx (Alpine) |
| Container | Docker Compose |
| CI/CD | GitHub Actions |

### ML/AI Stack (Pending Implementation)

| Component | Library |
|-----------|---------|
| Face Detection | OpenCV |
| Face Analysis | DeepFace |
| Audio Features | Librosa |
| Voice Activity | webrtcvad |
| ASR | OpenAI Whisper |
| Multimodal Fusion | PyTorch |
| Vector Search | FAISS (planned) |

---

## 7. Data Flow

```
Video Upload
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  1. Save video to storage/videos/{id}.mp4           │
│  2. Create Narrative record (status: processing)    │
│  3. Trigger background analysis pipeline            │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Background Pipeline (Pending: Celery)              │
│                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌───────────┐ │
│  │ Frame       │ → │ Facial      │ → │ Narrator  │ │
│  │ Extraction  │   │ Analysis    │   │ Profile   │ │
│  └─────────────┘   └─────────────┘   └───────────┘ │
│         │                                     │     │
│         ▼                                     ▼     │
│  ┌─────────────┐   ┌─────────────┐   ┌───────────┐ │
│  │ Audio       │ → │ Vocal       │ → │ Audio     │ │
│  │ Extraction  │   │ Analysis    │   │ Embedding │ │
│  └─────────────┘   └─────────────┘   └───────────┘ │
│         │                                     │     │
│         ▼                                     ▼     │
│  ┌─────────────┐   ┌─────────────┐                 │
│  │ Whisper     │ → │ Multimodal  │                 │
│  │ Transcribe  │   │ Fusion      │                 │
│  └─────────────┘   └─────────────┘                 │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  4. Save all analysis to database                   │
│  5. Update Narrative status to "complete"           │
│  6. Archive JSON to storage/archives/{id}.json      │
└─────────────────────────────────────────────────────┘
```

---

## 8. Face Recognition Module (From Original Proposal)

### Status: Not Implemented

The face recognition module will enable:

1. **Narrator Identification**
   - Extract face embeddings from video
   - Match against stored narrator profiles
   - Return best match with confidence score

2. **Profile Management**
   - Create narrator profiles with reference images
   - Store 512-dim embeddings in database
   - FAISS indexing for fast similarity search

3. **API Endpoints (Planned)**
   ```
   POST /api/identify     - Identify narrator from video
   POST /api/profiles     - Create narrator profile
   GET  /api/profiles/:id - Get profile details
   ```

---

## 9. Deployment

### Quick Start

```bash
# Start everything
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f api

# Test API
curl http://localhost/api/narratives
```

### Services

| Service | Port | Status |
|---------|------|--------|
| Frontend (Nginx) | 80 | ✅ Running |
| API (FastAPI) | 8000 (internal) | ✅ Running |
| PostgreSQL | 5432 (internal) | ✅ Running |
| Redis | 6379 (internal) | ✅ Running |

---

## 10. Risks & Mitigation

| Risk | Mitigation | Status |
|------|------------|--------|
| Low-quality video | Preprocessing & filtering | Pending |
| False face matches | Threshold tuning + multiple embeddings | Pending |
| Processing latency | Celery queue + batch processing | Pending |
| Scale | FAISS vector indexing | Pending |
| Data loss | Docker volumes + backups | ✅ Done |

---

## 11. Deliverables

| Deliverable | Status |
|-------------|--------|
| REST API | ✅ Complete |
| Database schema | ✅ Complete |
| Docker deployment | ✅ Complete |
| CI/CD pipeline | ✅ Complete |
| Frontend UI | ✅ Complete |
| Sample data seeding | ✅ Complete |
| Face recognition service | 🔴 Pending |
| Real ML implementations | ✅ Complete |
| Celery task queue | 🔴 Pending |

---

## 12. Success Criteria

| Criteria | Target | Status |
|----------|--------|--------|
| Data persistence | No data loss on restart | ✅ Met |
| API response time | < 100ms for reads | ✅ Met |
| System uptime | 99%+ with Docker | ✅ Met |
| Narrator identification | > 90% accuracy | 🔴 Pending |
| Video processing | < 30s for 1min video | 🔴 Pending |

---

## 13. Next Steps

1. **Implement face recognition**
   - Add embedding storage to database
   - Integrate FAISS for similarity search
   - Create `/api/identify` endpoint

2. **Add Celery task queue**
   - Move video processing to background workers
   - Enable progress tracking

3. **Add authentication**
   - JWT-based auth for protected routes
   - Multi-user support

4. **Performance optimization**
   - Benchmark processing times
   - Add GPU support for faster inference

---

*"Every oral tradition carries the full weight of its teller — their identity, their trembling voice, the flash of sorrow or joy across their face. This system preserves all of it."*
