# Roadmap - Oral Narrative Preservation System

**Last Updated:** 2026-03-20

---

## Summary

| Category | Done | Remaining |
|----------|------|-----------|
| Infrastructure | 9/9 | ✅ Complete |
| ML Core Services | 5/5 | ✅ Complete |
| ML Unit Tests | 5/5 | ✅ Complete |
| Integration Tests | 1/1 | ✅ Complete |
| Docker Optimization | 1/1 | ✅ Complete |
| Authentication | 1/1 | ✅ Complete |
| Rate Limiting | 1/1 | ✅ Complete |
| Performance | 1/1 | ✅ Complete |
| GPU Support | 1/1 | ✅ Complete |
| Logging | 1/1 | ✅ Complete |

---

## Completed ✅

### Infrastructure
- [x] PostgreSQL persistence with Docker volumes
- [x] Async SQLAlchemy ORM
- [x] Nginx reverse proxy (frontend on :80, API internal)
- [x] Docker Compose orchestration
- [x] CI/CD with GitHub Actions
- [x] Testing infrastructure (pytest + SQLite)
- [x] Python-based database seeding
- [x] Environment configuration (pydantic-settings)
- [x] Modular backend structure (routers/services/models)

### ML Services (Production Grade)
- [x] Transcription Service (Whisper ASR)
- [x] Facial Analysis (OpenCV + DeepFace)
- [x] Audio Analysis (Librosa + FFmpeg)
- [x] Multimodal Fusion
- [x] Upload Service Integration

### Authentication & Security
- [x] JWT Authentication (login/register/me endpoints)
- [x] Password hashing with bcrypt
- [x] Protected route dependencies
- [x] Rate limiting with Redis

### Performance & Monitoring
- [x] Performance benchmarks endpoint
- [x] System health check
- [x] GPU detection and utilization
- [x] Structured JSON logging

---

## New Features Added (2026-03-20)

### Face Recognition & Identification
| Feature | Status | Files |
|---------|--------|-------|
| `/api/narrators/identify` endpoint | ✅ Complete | `routers/narrators.py` |
| `extract_face_embedding_from_image()` | ✅ Complete | `services/narrator_service.py` |
| Auto-discovery of narrators | ✅ Complete | `services/narrator_service.py` |

### FAISS Vector Index
| Feature | Status | Files |
|---------|--------|-------|
| FAISS index service | ✅ Complete | `services/faiss_service.py` |
| Add/remove/search embeddings | ✅ Complete | `services/faiss_service.py` |
| `/api/narrators/rebuild-index` endpoint | ✅ Complete | `routers/narrators.py` |
| Integration with narrator service | ✅ Complete | `services/narrator_service.py` |

### JWT Authentication
| Feature | Status | Files |
|---------|--------|-------|
| User model | ✅ Complete | `models/narrative.py` |
| Auth service (hash/verify/jwt) | ✅ Complete | `services/auth_service.py` |
| `/api/auth/register` endpoint | ✅ Complete | `routers/auth.py` |
| `/api/auth/login` endpoint | ✅ Complete | `routers/auth.py` |
| `/api/auth/me` endpoint | ✅ Complete | `routers/auth.py` |
| Protected route dependencies | ✅ Complete | `routers/auth.py` |

### Rate Limiting
| Feature | Status | Files |
|---------|--------|-------|
| Redis-based rate limiter | ✅ Complete | `services/rate_limit_service.py` |
| Configurable limits | ✅ Complete | `config.py` |

### Performance Benchmarks
| Feature | Status | Files |
|---------|--------|-------|
| Benchmark service | ✅ Complete | `services/benchmark_service.py` |
| `/api/stats/benchmark` endpoint | ✅ Complete | `routers/stats.py` |
| `/api/stats/health` endpoint | ✅ Complete | `routers/stats.py` |

### GPU Support
| Feature | Status | Files |
|---------|--------|-------|
| GPU detection service | ✅ Complete | `services/gpu_service.py` |
| Device management | ✅ Complete | `services/gpu_service.py` |

### Structured Logging
| Feature | Status | Files |
|---------|--------|-------|
| JSON log formatter | ✅ Complete | `core/logging_config.py` |
| Console colored formatter | ✅ Complete | `core/logging_config.py` |
| Request logging | ✅ Complete | `core/logging_config.py` |

---

## API Endpoints Summary

### Narratives
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/narratives` | List all narratives |
| GET | `/api/narratives/{id}` | Get single narrative |
| POST | `/api/narratives/upload` | Upload video |
| GET | `/api/narratives/{id}/status` | Check processing |

### Narrators (New)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/narrators` | List narrators |
| GET | `/api/narrators/{id}` | Get narrator |
| POST | `/api/narrators/register` | Register narrator |
| POST | `/api/narrators/identify` | Identify from video/image |
| POST | `/api/narrators/rebuild-index` | Rebuild FAISS index |
| PATCH | `/api/narrators/{id}` | Rename narrator |

### Authentication (New)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/auth/logout` | Logout |

### Stats (Updated)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | System statistics |
| GET | `/api/stats/benchmark` | Performance benchmarks |
| GET | `/api/stats/health` | Health check |

---

## New Dependencies Added

| Package | Purpose |
|---------|---------|
| faiss-cpu | Vector similarity search |
| bcrypt | Password hashing |
| email-validator | Email validation |
| fastapi-limiter | Rate limiting |
| psutil | System monitoring |

---

## Database Schema Updates

### New Table: users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);
```

---

## Test Commands

```bash
# Run all tests
cd backend && pytest -v

# Run specific service tests
pytest tests/test_transcription_service.py -v
pytest tests/test_facial_service.py -v
pytest tests/test_audio_service.py -v
pytest tests/test_fusion_service.py -v

# Run integration test
pytest tests/test_pipeline_integration.py -v

# Run with coverage
pytest --cov=app/services tests/ -v
```

---

## Docker Commands

```bash
# Start all services
docker compose up -d

# Rebuild after code changes
docker compose build api && docker compose up -d api

# View API logs
docker compose logs -f api

# View Celery worker logs
docker compose logs -f worker

# Reset database
docker compose down -v && docker compose up -d
```

---

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (dev key) | JWT signing key |
| `REDIS_URL` | redis://redis:6379/0 | Redis connection |
| `RATE_LIMIT_ENABLED` | true | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | 100 | Max requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | 60 | Rate limit window |
| `ENABLE_GPU` | false | Enable GPU acceleration |
| `LOG_FORMAT` | console | 'console' or 'json' |
| `LOG_LEVEL` | INFO | Logging level |

---

*All planned features implemented. System ready for production deployment.*
