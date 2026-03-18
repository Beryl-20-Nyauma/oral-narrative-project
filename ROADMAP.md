# Roadmap - Oral Narrative Preservation System

## Completed ✅

- [x] PostgreSQL persistence with Docker volumes
- [x] Async SQLAlchemy ORM
- [x] Nginx reverse proxy (frontend on :80, API internal)
- [x] Docker Compose orchestration
- [x] CI/CD with GitHub Actions
- [x] Testing infrastructure (pytest + SQLite)
- [x] Python-based database seeding
- [x] Environment configuration (pydantic-settings)
- [x] Modular backend structure (routers/services/models)

---

## Remaining Work 📋

### High Priority - Core Functionality

| Task | Description | Files |
|------|-------------|-------|
| Real Facial Analysis | Replace mocked `analyze_facial_features()` with OpenCV + DeepFace | `backend/app/services/facial_service.py` |
| Real Audio Analysis | Replace mocked `analyze_audio_features()` with Librosa | `backend/app/services/audio_service.py` |
| Real Multimodal Fusion | Replace mocked `fuse_multimodal_features()` with PyTorch model | `backend/app/services/fusion_service.py` |
| Whisper Transcription | Integrate OpenAI Whisper for ASR | `backend/app/services/upload_service.py` |
| Celery Task Queue | Move video processing to background workers | New: `backend/app/tasks/` |

### Medium Priority - Face Recognition

| Task | Description | Files |
|------|-------------|-------|
| Face Embedding Storage | Store DeepFace embeddings in database | `backend/app/models/narrative.py` |
| FAISS Vector Index | Add similarity search for narrator matching | New: `backend/app/services/vector_service.py` |
| Narrator Identification API | `/api/identify` endpoint | `backend/app/routers/identify.py` |

### Low Priority - Production Hardening

| Task | Description |
|------|-------------|
| JWT Authentication | Login/register endpoints, protected routes |
| Rate Limiting | API protection against abuse |
| Structured Logging | JSON logs for production |
| Backup Scripts | Automated PostgreSQL backups |
| Monitoring | Prometheus/Grafana or similar |

---

## Current Limitations

| Area | Status |
|------|--------|
| Facial analysis | 🔴 Returns simulated data |
| Audio analysis | 🔴 Returns simulated data |
| Multimodal fusion | 🔴 Returns simulated data |
| Transcription | 🔴 Not implemented |
| Face recognition | 🔴 Not implemented |
| Authentication | 🔴 Not implemented |
| Task queue | 🔴 Redis ready, Celery not implemented |

---

## Performance Targets

| Metric | Target |
|--------|--------|
| API response time | < 100ms for reads |
| Video processing | < 30s for 1min video |
| Concurrent uploads | 10 simultaneous |
| Database queries | < 50ms average |

---

## Next Steps

1. **Test current implementation**: `docker compose up -d`
2. **Implement real ML services**: Start with `facial_service.py`
3. **Add Celery**: For background video processing
4. **Add FAISS**: For narrator similarity search
5. **Add JWT**: For multi-user support
