"""
Oral Narrative Preservation System - FastAPI Backend
Multimodal analysis: video, audio, facial features, emotions
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import json
import uuid
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

app = FastAPI(
    title="Oral Narrative Preservation System",
    description="Multimodal AI system for capturing and archiving oral narratives",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage directories
STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)
(STORAGE_DIR / "videos").mkdir(exist_ok=True)
(STORAGE_DIR / "audio").mkdir(exist_ok=True)
(STORAGE_DIR / "archives").mkdir(exist_ok=True)
(STORAGE_DIR / "thumbnails").mkdir(exist_ok=True)

# In-memory database (replace with PostgreSQL/MongoDB in production)
narratives_db: Dict[str, Dict] = {}


# ─────────────────────────────────────────────
# FACIAL ANALYSIS MODULE
# ─────────────────────────────────────────────

def analyze_facial_features(video_path: str) -> Dict[str, Any]:
    """
    Analyze facial features from video using OpenCV + DeepFace.
    Returns per-frame emotion timeline and aggregate narrator profile.
    
    In production: 
        import cv2
        from deepface import DeepFace
    """
    # Simulated realistic analysis pipeline
    # Replace with actual OpenCV + DeepFace processing
    
    emotions_timeline = []
    frame_count = 0
    
    # Simulate frame-by-frame analysis
    simulated_emotions = [
        {"timestamp": 0.0, "dominant": "neutral", "joy": 0.12, "sadness": 0.05, "anger": 0.02, "fear": 0.01, "surprise": 0.03, "neutral": 0.72, "disgust": 0.05},
        {"timestamp": 2.5, "dominant": "joy", "joy": 0.68, "sadness": 0.02, "anger": 0.01, "fear": 0.00, "surprise": 0.12, "neutral": 0.14, "disgust": 0.03},
        {"timestamp": 5.0, "dominant": "sadness", "joy": 0.05, "sadness": 0.71, "anger": 0.03, "fear": 0.08, "surprise": 0.02, "neutral": 0.08, "disgust": 0.03},
        {"timestamp": 7.5, "dominant": "neutral", "joy": 0.22, "sadness": 0.08, "anger": 0.05, "fear": 0.02, "surprise": 0.06, "neutral": 0.54, "disgust": 0.03},
        {"timestamp": 10.0, "dominant": "surprise", "joy": 0.18, "sadness": 0.03, "anger": 0.02, "fear": 0.05, "surprise": 0.58, "neutral": 0.12, "disgust": 0.02},
        {"timestamp": 12.5, "dominant": "joy", "joy": 0.75, "sadness": 0.01, "anger": 0.01, "fear": 0.00, "surprise": 0.08, "neutral": 0.13, "disgust": 0.02},
    ]
    
    facial_expressions = [
        {"timestamp": 0.0, "smiling": False, "frowning": False, "eyebrow_raised": False, "mouth_open": True},
        {"timestamp": 2.5, "smiling": True, "frowning": False, "eyebrow_raised": False, "mouth_open": True},
        {"timestamp": 5.0, "smiling": False, "frowning": True, "eyebrow_raised": False, "mouth_open": True},
        {"timestamp": 7.5, "smiling": False, "frowning": False, "eyebrow_raised": False, "mouth_open": True},
        {"timestamp": 10.0, "smiling": False, "frowning": False, "eyebrow_raised": True, "mouth_open": True},
        {"timestamp": 12.5, "smiling": True, "frowning": False, "eyebrow_raised": False, "mouth_open": True},
    ]

    # Aggregate narrator identity profile
    narrator_profile = {
        "estimated_age": 52,
        "age_range": "45-60",
        "gender": "woman",
        "gender_confidence": 0.94,
        "dominant_emotion_overall": "joy",
        "emotion_distribution": {
            "joy": 0.38,
            "neutral": 0.29,
            "sadness": 0.15,
            "surprise": 0.11,
            "anger": 0.04,
            "fear": 0.02,
            "disgust": 0.01
        },
        "face_detected_frames": 142,
        "total_frames": 150,
        "detection_confidence": 0.947,
        "facial_action_units": {
            "AU1_inner_brow_raise": 0.23,
            "AU2_outer_brow_raise": 0.31,
            "AU4_brow_lowerer": 0.18,
            "AU6_cheek_raiser": 0.42,
            "AU12_lip_corner_puller": 0.55,
            "AU17_chin_raiser": 0.12,
            "AU25_lips_part": 0.78,
        }
    }
    
    return {
        "emotion_timeline": simulated_emotions,
        "expression_timeline": facial_expressions,
        "narrator_profile": narrator_profile,
        "grad_cam_available": True,
        "grad_cam_path": f"grad_cam_{uuid.uuid4().hex[:8]}.png"
    }


# ─────────────────────────────────────────────
# AUDIO ANALYSIS MODULE
# ─────────────────────────────────────────────

def analyze_audio_features(audio_path: str) -> Dict[str, Any]:
    """
    Extract vocal features using Librosa + SoundFile + WebRTC-VAD.
    
    In production:
        import librosa
        import soundfile as sf
        import webrtcvad
    """
    
    # Simulated Librosa feature extraction
    voice_activity_segments = [
        {"start": 0.1, "end": 3.2, "active": True},
        {"start": 3.2, "end": 3.8, "active": False},  # pause
        {"start": 3.8, "end": 7.1, "active": True},
        {"start": 7.1, "end": 7.5, "active": False},  # pause
        {"start": 7.5, "end": 11.3, "active": True},
        {"start": 11.3, "end": 11.9, "active": False},  # pause
        {"start": 11.9, "end": 14.8, "active": True},
    ]
    
    pitch_timeline = [
        {"timestamp": 0.0, "hz": 182.3, "note": "F#3"},
        {"timestamp": 0.5, "hz": 195.1, "note": "G3"},
        {"timestamp": 1.0, "hz": 210.4, "note": "Ab3"},
        {"timestamp": 1.5, "hz": 198.7, "note": "G3"},
        {"timestamp": 2.0, "hz": 185.2, "note": "F#3"},
        {"timestamp": 2.5, "hz": 220.0, "note": "A3"},
        {"timestamp": 3.0, "hz": 245.6, "note": "B3"},
    ]
    
    vocal_features = {
        "mean_pitch_hz": 198.4,
        "pitch_range_hz": {"min": 142.3, "max": 312.8},
        "pitch_variability_std": 38.2,
        "speech_rate_wpm": 127,
        "speech_rate_syllables_per_sec": 3.8,
        "total_duration_sec": 14.8,
        "voiced_duration_sec": 11.4,
        "pause_count": 3,
        "mean_pause_duration_sec": 0.58,
        "total_pause_duration_sec": 1.73,
        "energy_mean": 0.0423,
        "energy_std": 0.0187,
        "spectral_centroid_mean": 1842.3,
        "zero_crossing_rate": 0.0821,
        "mfcc_features": [
            -312.4, 87.3, -42.1, 23.7, -15.2, 8.9, -4.1, 2.3, -1.8, 0.9,
            -0.7, 0.4, -0.2
        ],
        "chroma_features": [0.42, 0.31, 0.28, 0.19, 0.35, 0.22, 0.18, 0.41, 0.33, 0.27, 0.21, 0.38],
        "vocal_emotion_indicators": {
            "arousal": 0.62,   # high/low energy
            "valence": 0.71,   # positive/negative
            "dominance": 0.54
        },
        "audio_embeddings": [round(x * 0.01, 6) for x in range(-64, 64)]  # 128-dim embedding placeholder
    }
    
    return {
        "voice_activity_segments": voice_activity_segments,
        "pitch_timeline": pitch_timeline,
        "vocal_features": vocal_features,
        "audio_quality": {
            "sample_rate": 44100,
            "bit_depth": 16,
            "snr_db": 28.4,
            "clipping_detected": False
        }
    }


# ─────────────────────────────────────────────
# MULTIMODAL FUSION MODULE
# ─────────────────────────────────────────────

def fuse_multimodal_features(facial_data: Dict, audio_data: Dict, transcript: str) -> Dict[str, Any]:
    """
    Fuse facial + audio + text features using NumPy/pandas/PyTorch.
    
    In production:
        import numpy as np
        import pandas as pd
        from sklearn.preprocessing import StandardScaler
        import torch
        from pytorch_grad_cam import GradCAM
    """
    
    # Build synchronized emotion timeline by aligning video + audio timestamps
    unified_timeline = []
    facial_emotions = {e["timestamp"]: e for e in facial_data["emotion_timeline"]}
    
    for segment in audio_data["voice_activity_segments"]:
        if not segment["active"]:
            continue
        t = segment["start"]
        closest_facial = min(facial_emotions.keys(), key=lambda x: abs(x - t))
        facial_entry = facial_emotions[closest_facial]
        
        unified_timeline.append({
            "timestamp": t,
            "duration": segment["end"] - segment["start"],
            "facial_emotion": facial_entry["dominant"],
            "facial_confidence": max(facial_entry["joy"], facial_entry["sadness"], 
                                     facial_entry["neutral"], facial_entry["surprise"]),
            "voice_energy": round(0.3 + (t / 15) * 0.4, 3),
            "pitch_deviation": round(abs(198.4 - (180 + t * 3)) / 198.4, 3),
            "fused_emotion_label": facial_entry["dominant"],
            "multimodal_confidence": 0.85
        })
    
    # Narrator profile vector (for ML downstream tasks)
    narrator_vector = {
        "facial_embedding_dim": 512,
        "audio_embedding_dim": 128,
        "fused_vector_dim": 640,
        "model_architecture": "CrossAttention Fusion Transformer",
        "narrator_identity_hash": uuid.uuid4().hex[:16],
        "processing_framework": "PyTorch 2.x + scikit-learn"
    }
    
    # Emotion congruence analysis (face vs. voice agreement)
    emotion_congruence = {
        "facial_vocal_agreement_score": 0.78,
        "moments_of_high_congruence": [2.5, 12.5],
        "moments_of_divergence": [5.0],
        "interpretation": "High emotional authenticity — face and voice strongly aligned"
    }
    
    return {
        "unified_emotion_timeline": unified_timeline,
        "narrator_vector": narrator_vector,
        "emotion_congruence": emotion_congruence,
        "fusion_method": "Late fusion with attention weighting",
        "grad_cam_highlights": {
            "high_attention_regions": ["eye area", "mouth corners", "brow region"],
            "model_focus": "Periocular region dominant in emotion classification"
        }
    }


# ─────────────────────────────────────────────
# ARCHIVE BUILDER
# ─────────────────────────────────────────────

def build_archive_entry(narrative_id: str, metadata: Dict, facial_data: Dict, 
                         audio_data: Dict, fusion_data: Dict) -> Dict[str, Any]:
    """Build complete multimodal archive entry for permanent storage."""
    
    return {
        "archive_id": narrative_id,
        "version": "1.0",
        "created_at": datetime.utcnow().isoformat(),
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
            "date_recorded": metadata.get("date_recorded", datetime.utcnow().date().isoformat()),
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


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Oral Narrative Preservation System API", "version": "1.0.0", "status": "active"}


@app.get("/api/narratives")
async def list_narratives(
    narrator: Optional[str] = None,
    emotion: Optional[str] = None,
    theme: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List all archived narratives with optional filtering."""
    results = list(narratives_db.values())
    
    if narrator:
        results = [n for n in results if narrator.lower() in 
                   n.get("narrative_metadata", {}).get("narrator_name", "").lower()]
    if emotion:
        results = [n for n in results if emotion.lower() in 
                   [e.lower() for e in n.get("search_index", {}).get("dominant_emotions", [])]]
    if theme:
        results = [n for n in results if any(theme.lower() in t.lower() 
                   for t in n.get("search_index", {}).get("themes", []))]
    
    total = len(results)
    results = results[offset:offset + limit]
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "narratives": [{
            "id": n["archive_id"],
            "title": n["narrative_metadata"]["title"],
            "narrator_name": n["narrative_metadata"]["narrator_name"],
            "duration_sec": n["narrative_metadata"]["duration_sec"],
            "dominant_emotion": n["facial_analysis"]["narrator_profile"]["dominant_emotion_overall"],
            "created_at": n["created_at"],
            "themes": n["narrative_metadata"]["themes"],
        } for n in results]
    }


@app.get("/api/narratives/{narrative_id}")
async def get_narrative(narrative_id: str):
    """Get complete archive entry for a narrative."""
    if narrative_id not in narratives_db:
        raise HTTPException(status_code=404, detail="Narrative not found")
    return narratives_db[narrative_id]


@app.post("/api/narratives/upload")
async def upload_narrative(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    title: str = "Untitled Narrative",
    narrator_name: str = "Anonymous",
    location: str = "",
    language: str = "en",
    themes: str = "",
    transcript: str = ""
):
    """
    Upload a video narrative and trigger full multimodal analysis pipeline.
    """
    narrative_id = str(uuid.uuid4())
    
    # Save uploaded file
    video_path = STORAGE_DIR / "videos" / f"{narrative_id}.mp4"
    content = await video.read()
    with open(video_path, "wb") as f:
        f.write(content)
    
    metadata = {
        "title": title,
        "narrator_name": narrator_name,
        "location": location,
        "language": language,
        "themes": [t.strip() for t in themes.split(",") if t.strip()],
        "transcript": transcript,
        "date_recorded": datetime.utcnow().date().isoformat()
    }
    
    # Store pending status
    narratives_db[narrative_id] = {
        "archive_id": narrative_id,
        "status": "processing",
        "created_at": datetime.utcnow().isoformat(),
        "narrative_metadata": metadata,
    }
    
    # Trigger background processing
    background_tasks.add_task(process_narrative, narrative_id, str(video_path), metadata)
    
    return {
        "narrative_id": narrative_id,
        "status": "processing",
        "message": "Narrative uploaded. Multimodal analysis in progress.",
        "estimated_completion_sec": 30
    }


@app.get("/api/narratives/{narrative_id}/status")
async def get_processing_status(narrative_id: str):
    """Check processing status of a narrative."""
    if narrative_id not in narratives_db:
        raise HTTPException(status_code=404, detail="Narrative not found")
    
    entry = narratives_db[narrative_id]
    return {
        "narrative_id": narrative_id,
        "status": entry.get("status", "unknown"),
        "progress": entry.get("progress", {}),
        "created_at": entry.get("created_at"),
    }


@app.get("/api/narratives/{narrative_id}/emotion-timeline")
async def get_emotion_timeline(narrative_id: str):
    """Get synchronized emotion timeline for a narrative."""
    if narrative_id not in narratives_db:
        raise HTTPException(status_code=404, detail="Narrative not found")
    
    entry = narratives_db[narrative_id]
    if entry.get("status") != "complete":
        return {"status": "processing", "message": "Analysis not yet complete"}
    
    return {
        "narrative_id": narrative_id,
        "facial_emotions": entry["facial_analysis"]["emotion_timeline"],
        "vocal_features": entry["vocal_analysis"]["pitch_timeline"],
        "unified_timeline": entry["multimodal_fusion"]["unified_emotion_timeline"],
    }


@app.get("/api/narratives/{narrative_id}/narrator-profile")
async def get_narrator_profile(narrative_id: str):
    """Get extracted narrator identity and vocal profile."""
    if narrative_id not in narratives_db:
        raise HTTPException(status_code=404, detail="Narrative not found")
    
    entry = narratives_db[narrative_id]
    if entry.get("status") != "complete":
        return {"status": "processing"}
    
    return {
        "narrative_id": narrative_id,
        "narrator_identity": entry["narrator"],
        "vocal_profile": entry["vocal_analysis"]["vocal_features"],
        "emotion_congruence": entry["multimodal_fusion"]["emotion_congruence"],
    }


@app.get("/api/search")
async def search_narratives(q: str, field: str = "all"):
    """Full-text search across narratives by narrator, emotion, theme, or keyword."""
    results = []
    q_lower = q.lower()
    
    for narrative in narratives_db.values():
        if narrative.get("status") != "complete":
            continue
            
        index = narrative.get("search_index", {})
        matched = False
        
        if field in ("all", "narrator") and q_lower in index.get("narrator_name", "").lower():
            matched = True
        if field in ("all", "emotion") and any(q_lower in e for e in index.get("dominant_emotions", [])):
            matched = True
        if field in ("all", "theme") and any(q_lower in t.lower() for t in index.get("themes", [])):
            matched = True
        if field in ("all", "keyword") and any(q_lower in k for k in index.get("keywords", [])):
            matched = True
        
        if matched:
            results.append({
                "id": narrative["archive_id"],
                "title": narrative["narrative_metadata"]["title"],
                "narrator_name": narrative["narrative_metadata"]["narrator_name"],
                "dominant_emotion": narrative["facial_analysis"]["narrator_profile"]["dominant_emotion_overall"],
                "themes": narrative["narrative_metadata"]["themes"],
            })
    
    return {"query": q, "results": results, "count": len(results)}


@app.get("/api/stats")
async def get_system_stats():
    """Get system-wide statistics."""
    complete = [n for n in narratives_db.values() if n.get("status") == "complete"]
    
    emotion_counts = {}
    for n in complete:
        e = n.get("facial_analysis", {}).get("narrator_profile", {}).get("dominant_emotion_overall", "unknown")
        emotion_counts[e] = emotion_counts.get(e, 0) + 1
    
    return {
        "total_narratives": len(narratives_db),
        "complete": len(complete),
        "processing": len([n for n in narratives_db.values() if n.get("status") == "processing"]),
        "total_duration_min": sum(n.get("narrative_metadata", {}).get("duration_sec", 0) 
                                  for n in complete) / 60,
        "emotion_distribution": emotion_counts,
        "unique_narrators": len(set(n.get("narrative_metadata", {}).get("narrator_name", "") 
                                    for n in complete)),
    }


# ─────────────────────────────────────────────
# BACKGROUND PROCESSING PIPELINE
# ─────────────────────────────────────────────

async def process_narrative(narrative_id: str, video_path: str, metadata: Dict):
    """Full multimodal processing pipeline."""
    try:
        # Update progress
        narratives_db[narrative_id]["progress"] = {"stage": "facial_analysis", "pct": 10}
        await asyncio.sleep(1)  # Simulate processing time
        
        # Stage 1: Facial Analysis
        facial_data = analyze_facial_features(video_path)
        narratives_db[narrative_id]["progress"] = {"stage": "audio_analysis", "pct": 35}
        await asyncio.sleep(1)
        
        # Stage 2: Audio Analysis
        audio_path = video_path.replace("/videos/", "/audio/").replace(".mp4", ".wav")
        audio_data = analyze_audio_features(audio_path)
        narratives_db[narrative_id]["progress"] = {"stage": "multimodal_fusion", "pct": 65}
        await asyncio.sleep(1)
        
        # Stage 3: Multimodal Fusion
        fusion_data = fuse_multimodal_features(facial_data, audio_data, metadata.get("transcript", ""))
        narratives_db[narrative_id]["progress"] = {"stage": "archival", "pct": 85}
        await asyncio.sleep(0.5)
        
        # Stage 4: Build Archive Entry
        archive_entry = build_archive_entry(narrative_id, metadata, facial_data, audio_data, fusion_data)
        archive_entry["status"] = "complete"
        archive_entry["progress"] = {"stage": "complete", "pct": 100}
        
        # Save to JSON archive
        archive_path = STORAGE_DIR / "archives" / f"{narrative_id}.json"
        with open(archive_path, "w") as f:
            json.dump(archive_entry, f, indent=2)
        
        # Update in-memory DB
        narratives_db[narrative_id] = archive_entry
        
    except Exception as e:
        narratives_db[narrative_id]["status"] = "error"
        narratives_db[narrative_id]["error"] = str(e)


# ─────────────────────────────────────────────
# SEED DEMO DATA
# ─────────────────────────────────────────────

async def seed_demo_data():
    """Seed with realistic demo narratives for UI demonstration."""
    demo_narratives = [
        {
            "title": "The Day the River Flooded",
            "narrator_name": "Kirongosi  A",
            "location": "Kakamega, Kenya",
            "themes": ["memory", "water", "community", "survival"],
            "transcript": "I remember it was the rainy season of 1987. The Subin River had been rising for days. My mother kept watch all night..."
        },
        {
            "title": "Songs My Grandmother Taught Me",
            "narrator_name": " ROSE",
            "location": " Kisumu, Nyanza",
            "themes": ["music", "family", "tradition", "loss"],
            "transcript": "She would sit by the window every evening and hum these melodies. I didn't understand the words then, they were in Zapotec..."
        },
        {
            "title": "Working the Coal Mines",
            "narrator_name": "DAVIS ONGERI",
            "location": "KISII, KENYA",
            "themes": ["labor", "history", "identity", "resistance"],
            "transcript": "My father went down at six in the morning and came up at four. Every day for forty years. We never asked him how it was down there..."
        },
        {
            "title": "First Night in a Strange Country",
            "narrator_name": "NADIA BERYL",
            "location": "NGONG,→ KAJIADO",
            "themes": ["migration", "belonging", "hope", "displacement"],
            "transcript": "The apartment was so quiet. In NGONG,you always hear the neighbors, the street, the call to prayer. Here it was just silence..."
        },
        {
            "title": "My Mother's Kitchen Garden",
            "narrator_name": "LUWI 0",
            "location": "EMBU, KENYA",
            "themes": ["food", "memory", "healing", "place"],
            "transcript": "She planted everything by the phases of the moon. Turmeric here, ginger there, tulsi by the doorstep for protection..."
        }
    ]
    
    for i, demo in enumerate(demo_narratives):
        nid = f"demo-{i+1:04d}"
        meta = {**demo, "language": "en", "date_recorded": "2024-0{}-15".format(i+1)}
        
        facial_data = analyze_facial_features("demo.mp4")
        audio_data = analyze_audio_features("demo.wav")
        fusion_data = fuse_multimodal_features(facial_data, audio_data, demo["transcript"])
        archive = build_archive_entry(nid, meta, facial_data, audio_data, fusion_data)
        archive["status"] = "complete"
        narratives_db[nid] = archive


@app.on_event("startup")
async def startup():
    await seed_demo_data()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
