# ML Infrastructure Report: Production Deployment

**Project:** Oral Narrative Preservation System  
**Date:** March 20, 2026  
**Context:** Production Deployment  
**Expected Volume:** Scalable (10s to 1000s of videos)

---

## Executive Summary

This is a **production-grade multimodal AI system** for archiving oral narratives. The system processes video recordings to extract facial features, vocal characteristics, and performs multimodal emotion fusion.

**Recommendation:** CPU processing for development/testing, GPU for production scale.

---

## 1. Project Context

| Factor | Value |
|--------|-------|
| Project Type | Production System |
| Primary Goal | Archive and analyze oral narratives |
| Expected Videos | Scalable (10s to 1000s) |
| Concurrent Users | Multiple users |
| Processing Time | Optimized for throughput |
| Budget | Variable based on scale |

---

## 2. Infrastructure Recommendations

### 2.1 Development/Testing

| Resource | Requirement | Notes |
|----------|-------------|-------|
| CPU | 4+ cores | Any modern machine |
| RAM | 8 GB minimum | 16 GB preferred |
| GPU | Optional | Speeds up processing 2-5x |
| Storage | 10-20 GB | For ML models and videos |

### 2.2 Production

| Resource | Requirement | Notes |
|----------|-------------|-------|
| CPU | 8+ cores | Server-grade recommended |
| RAM | 32 GB+ | For concurrent processing |
| GPU | NVIDIA GPU with 8GB+ VRAM | CUDA-enabled |
| Storage | SSD with 100GB+ | For video archives |

### 2.3 Cloud Options

| Provider | Instance Type | Cost/Month | Notes |
|----------|---------------|------------|-------|
| AWS | g5.xlarge (GPU) | ~$500 | Good for production |
| GCP | n1-standard-8 + T4 | ~$400 | Cost-effective GPU |
| Azure | Standard_NC6 | ~$450 | Similar specs |
| Local | Custom server | Variable | Best for privacy |

---

## 3. Processing Performance

### 3.1 CPU Processing Times

| Video Length | Processing Time | Notes |
|--------------|-----------------|-------|
| 30 seconds | ~30-45 seconds | CPU only |
| 1 minute | ~1-2 minutes | CPU only |
| 2 minutes | ~2-4 minutes | CPU only |
| 5 minutes | ~5-10 minutes | CPU only |

### 3.2 GPU Processing Times

| Video Length | Processing Time | Speedup |
|--------------|-----------------|---------|
| 30 seconds | ~10-15 seconds | 3x faster |
| 1 minute | ~20-30 seconds | 3x faster |
| 2 minutes | ~45-60 seconds | 3x faster |
| 5 minutes | ~2-3 minutes | 3x faster |

---

## 4. Cost Analysis

### 4.1 Self-Hosted (On-Premises)

| Component | Cost |
|-----------|------|
| Server hardware | $2,000-5,000 one-time |
| GPU (optional) | $500-2,000 one-time |
| Electricity | $50-100/month |
| Maintenance | Variable |

### 4.2 Cloud Deployment

| Scale | Monthly Cost | Notes |
|-------|--------------|-------|
| Small (<100 videos) | $100-300 | CPU instances |
| Medium (100-1000 videos) | $300-800 | Mixed CPU/GPU |
| Large (1000+ videos) | $800-2000 | GPU instances |

---

## 5. Model Selection

### 5.1 Whisper Model

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| tiny | 75 MB | Very fast | Lower | Testing |
| base | 150 MB | Fast | Good | Default |
| small | 500 MB | Medium | Better | Quality-focused |
| medium | 1.5 GB | Slow | Great | High accuracy |
| large | 3 GB | Very slow | Best | Maximum accuracy |

**Recommendation:** Use `base` for development, `small` for production.

### 5.2 DeepFace Backend

| Backend | Speed | Accuracy | Use Case |
|---------|-------|----------|----------|
| opencv | Fast | Good | Default |
| retinaface | Medium | Better | High accuracy |
| mtcnn | Slow | Best | Maximum accuracy |

### 5.3 Environment Variables

```env
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
DEEPFACE_BACKEND=opencv
DEEPFACE_ENFORCE_DETECTION=false
```

---

## 6. Scaling Strategy

### 6.1 Horizontal Scaling

- Use Celery + Redis for distributed task queue
- Multiple worker nodes for parallel processing
- Load balancer for API endpoints

### 6.2 Vertical Scaling

- Increase CPU cores for faster frame processing
- Add GPU for parallel ML inference
- More RAM for concurrent video handling

---

## 7. Production Checklist

### 7.1 Before Deployment

- [ ] Run `docker compose up -d` successfully
- [ ] Configure environment variables
- [ ] Set up SSL/TLS certificates
- [ ] Configure backup strategy
- [ ] Set up monitoring and alerts
- [ ] Test all API endpoints

### 7.2 Monitoring

| Metric | Tool | Alert Threshold |
|--------|------|-----------------|
| CPU usage | Prometheus | > 80% |
| Memory usage | Prometheus | > 85% |
| Disk usage | Prometheus | > 90% |
| API latency | Grafana | > 500ms |
| Error rate | Grafana | > 1% |

---

## 8. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Processing failures | Retry logic + error logging |
| Storage exhaustion | Auto-cleanup + alerts |
| Memory leaks | Container restart policies |
| GPU OOM | Batch size tuning |
| Network issues | Timeout handling + retries |

---

## 9. Summary

### Minimum Requirements

| Item | Specification |
|------|---------------|
| CPU | 4 cores |
| RAM | 8 GB |
| Storage | 20 GB SSD |
| GPU | Optional |

### Recommended Production Setup

| Item | Specification |
|------|---------------|
| CPU | 8+ cores |
| RAM | 32 GB |
| Storage | 100 GB+ SSD |
| GPU | NVIDIA T4 or better |
| Queue | Celery + Redis |
| Monitoring | Prometheus + Grafana |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────┐
│           PRODUCTION SPECS                       │
├─────────────────────────────────────────────────┤
│  Videos: Scalable (10s to 1000s)                │
│  CPU: 4+ cores (8+ recommended)                 │
│  RAM: 8 GB min (32 GB recommended)              │
│  GPU: Optional (2-5x speedup)                   │
│  Storage: 20 GB min (100 GB+ recommended)       │
│  Whisper model: base (small for production)     │
│  Queue: Celery + Redis (ready)                  │
└─────────────────────────────────────────────────┘
```

---

*Report prepared for: Production Deployment*
*Context: Oral Narrative Preservation System*
