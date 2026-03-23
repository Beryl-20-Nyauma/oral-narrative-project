"""Narrator identification and auto-discovery service."""

import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.narrative import Narrator, Narrative

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.75


async def identify_or_create_narrator(
    db: AsyncSession,
    face_embedding: List[float],
    video_path: str,
    confidence_threshold: float = SIMILARITY_THRESHOLD,
    use_faiss: bool = True
) -> Tuple[Optional[Narrator], float]:
    """
    Identify narrator from face embedding or create new one.
    
    Auto-discovery flow:
    1. Try FAISS search first (if enabled and available)
    2. Fall back to brute-force comparison
    3. If match found (similarity > threshold): return existing narrator
    4. If no match: create new "Unknown #N" narrator
    
    Args:
        db: Database session
        face_embedding: 512-dim face embedding vector
        video_path: Path to video (for reference)
        confidence_threshold: Minimum similarity for match (default: 0.85)
        use_faiss: Whether to use FAISS for search (default: True)
    
    Returns:
        Tuple of (Narrator, confidence_score)
    """
    if not face_embedding:
        return None, 0.0
    
    best_match = None
    best_score = 0.0
    
    if use_faiss:
        try:
            from app.services.faiss_service import identify_with_faiss, load_index
            load_index()
            narrator_id, score = await identify_with_faiss(
                db, face_embedding, confidence_threshold
            )
            if narrator_id:
                result = await db.execute(
                    select(Narrator).where(Narrator.id == narrator_id)
                )
                best_match = result.scalar_one_or_none()
                best_score = score
        except Exception as e:
            logger.warning(f"FAISS search failed, falling back to brute-force: {e}")
    
    if not best_match:
        result = await db.execute(select(Narrator))
        narrators = result.scalars().all()
        
        for narrator in narrators:
            if not narrator.face_embedding:
                continue
            
            similarity = cosine_similarity(face_embedding, narrator.face_embedding)
            
            if similarity > best_score:
                best_score = similarity
                best_match = narrator
    
    if best_match and best_score >= confidence_threshold:
        logger.info(f"Matched narrator: {best_match.name} (confidence: {best_score:.2f})")
        best_match.last_seen_at = datetime.utcnow()
        best_match.narrative_count += 1
        await db.flush()
        return best_match, best_score
    
    new_narrator = await create_unknown_narrator(db, face_embedding, video_path)
    logger.info(f"Created new narrator: {new_narrator.id}")
    return new_narrator, 1.0


async def extract_and_save_face_thumbnail(
    video_path: str
) -> Optional[str]:
    """
    Extract and save face thumbnail from video.
    
    Args:
        video_path: Path to video file
    
    Returns:
        Path to saved face thumbnail or None if no face detected
    """
    from pathlib import Path
    from config import get_settings
    
    settings = get_settings()
    storage_dir = Path(settings.storage_dir)
    narrators_dir = storage_dir / "narrators"
    narrators_dir.mkdir(parents=True, exist_ok=True)
    
    import uuid
    
    try:
        import cv2
        from deepface import DeepFace
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_frame = int(total_frames * 0.5)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, sample_frame)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return None
        
        try:
            faces = DeepFace.extract_faces(
                frame,
                enforce_detection=False,
                detector_backend="opencv"
            )
            
            if faces and len(faces) > 0:
                face_img = faces[0]["face"]
                
                thumbnail_path = narrators_dir / f"{uuid.uuid4()}.jpg"
                cv2.imwrite(str(thumbnail_path), face_img)
                
                logger.info(f"Saved face thumbnail: {thumbnail_path}")
                return str(thumbnail_path)
            
        except Exception as e:
            logger.debug(f"Face extraction failed: {e}")
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to extract face thumbnail: {e}")
        return None


async def create_unknown_narrator(
    db: AsyncSession,
    face_embedding: List[float],
    reference_path: str
) -> Narrator:
    """
    Create a new unknown narrator.
    
    Args:
        db: Database session
        face_embedding: Face embedding vector
        reference_path: Path to reference video/image
    
    Returns:
        New Narrator instance
    """
    count_result = await db.execute(select(Narrator))
    existing_count = len(count_result.all())
    
    face_thumbnail_path = await extract_and_save_face_thumbnail(reference_path)
    
    narrator = Narrator(
        name=f"Unknown #{existing_count + 1}",
        face_embedding=face_embedding,
        reference_image_path=face_thumbnail_path or reference_path,
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
        narrative_count=1,
        named_by_user=False,
        metadata={"auto_created": True}
    )
    
    db.add(narrator)
    await db.flush()
    
    try:
        from app.services.faiss_service import add_embedding
        add_embedding(str(narrator.id), face_embedding)
    except Exception as e:
        logger.warning(f"Failed to add narrator to FAISS index: {e}")
    
    return narrator


async def register_narrator(
    db: AsyncSession,
    name: str,
    face_embedding: List[float],
    reference_path: str,
    metadata: Optional[Dict] = None
) -> Narrator:
    """
    Register a known narrator.
    
    Args:
        db: Database session
        name: Narrator name
        face_embedding: Face embedding vector
        reference_path: Path to reference image/video
        metadata: Optional metadata dict
    
    Returns:
        New Narrator instance
    """
    face_thumbnail_path = await extract_and_save_face_thumbnail(reference_path)
    
    narrator = Narrator(
        name=name,
        face_embedding=face_embedding,
        reference_image_path=face_thumbnail_path or reference_path,
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
        narrative_count=0,
        named_by_user=True,
        metadata=metadata or {}
    )
    
    db.add(narrator)
    await db.flush()
    
    try:
        from app.services.faiss_service import add_embedding
        add_embedding(str(narrator.id), face_embedding)
    except Exception as e:
        logger.warning(f"Failed to add narrator to FAISS index: {e}")
    
    return narrator


async def rename_narrator(
    db: AsyncSession,
    narrator_id: str,
    new_name: str
) -> Optional[Narrator]:
    """
    Rename a narrator (e.g., "Unknown #5" → "Mama Fatima").
    
    Also renumbers subsequent "Unknown #N" narrators to maintain order.
    
    Args:
        db: Database session
        narrator_id: UUID of narrator
        new_name: New name for narrator
    
    Returns:
        Updated Narrator or None if not found
    """
    result = await db.execute(
        select(Narrator).where(Narrator.id == narrator_id)
    )
    narrator = result.scalar_one_or_none()
    
    if not narrator:
        return None
    
    old_name = narrator.name
    
    narrator.name = new_name
    narrator.named_by_user = True
    await db.flush()
    
    logger.info(f"Renamed narrator from '{old_name}' to '{new_name}'")
    
    await renumber_unknown_narrators(db)
    
    return narrator


async def renumber_unknown_narrators(db: AsyncSession):
    """
    Renumber all "Unknown #N" narrators to maintain sequential order.
    
    Args:
        db: Database session
    """
    from sqlalchemy import func
    
    result = await db.execute(
        select(Narrator)
        .where(Narrator.name.like("Unknown #%"))
        .where(Narrator.named_by_user == False)
        .order_by(func.cast(func.regexp_replace(Narrator.name, r'[^0-9]', ''), int))
    )
    unknown_narrators = result.scalars().all()
    
    for index, narrator in enumerate(unknown_narrators, start=1):
        new_name = f"Unknown #{index}"
        if narrator.name != new_name:
            logger.info(f"Renarrating: {narrator.name} → {new_name}")
            narrator.name = new_name
    
    await db.flush()


async def get_narrator_with_narratives(
    db: AsyncSession,
    narrator_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get narrator details with their narratives.
    
    Args:
        db: Database session
        narrator_id: UUID of narrator
    
    Returns:
        Dict with narrator info and narratives list
    """
    result = await db.execute(
        select(Narrator).where(Narrator.id == narrator_id)
    )
    narrator = result.scalar_one_or_none()
    
    if not narrator:
        return None
    
    narratives_result = await db.execute(
        select(Narrative)
        .where(Narrative.narrator_id == narrator_id)
        .order_by(Narrative.created_at.desc())
    )
    narratives = narratives_result.scalars().all()
    
    return {
        "id": str(narrator.id),
        "name": narrator.name,
        "named_by_user": narrator.named_by_user,
        "narrative_count": narrator.narrative_count,
        "first_seen_at": narrator.first_seen_at.isoformat() if narrator.first_seen_at else None,
        "last_seen_at": narrator.last_seen_at.isoformat() if narrator.last_seen_at else None,
        "metadata": narrator.metadata or {},
        "narratives": [
            {
                "id": str(n.id),
                "title": n.title,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "duration_sec": n.duration_sec,
            }
            for n in narratives
        ]
    }


async def list_narrators(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List all narrators.
    
    Args:
        db: Database session
        limit: Max results
        offset: Pagination offset
    
    Returns:
        Dict with narrators list and pagination info
    """
    count_result = await db.execute(select(Narrator))
    total = len(count_result.all())
    
    result = await db.execute(
        select(Narrator)
        .order_by(Narrator.last_seen_at.desc())
        .offset(offset)
        .limit(limit)
    )
    narrators = result.scalars().all()
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "narrators": [
            {
                "id": str(n.id),
                "name": n.name,
                "named_by_user": n.named_by_user,
                "narrative_count": n.narrative_count,
                "first_seen_at": n.first_seen_at.isoformat() if n.first_seen_at else None,
                "last_seen_at": n.last_seen_at.isoformat() if n.last_seen_at else None,
            }
            for n in narrators
        ]
    }


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
    
    Returns:
        Similarity score between 0 and 1
    """
    try:
        a = np.array(vec1)
        b = np.array(vec2)
        
        if len(a) != len(b):
            return 0.0
        
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    except Exception as e:
        logger.warning(f"Similarity calculation failed: {e}")
        return 0.0


def extract_face_embedding(video_path: str) -> Optional[List[float]]:
    """
    Extract face embedding from video using DeepFace.
    
    Gets the most confident face from the video and returns
    its 512-dim embedding vector.
    
    Args:
        video_path: Path to video file
    
    Returns:
        512-dim embedding vector or None if no face found
    """
    try:
        from deepface import DeepFace
        import cv2
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning(f"Cannot open video: {video_path}")
            return None
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_frames = [int(total_frames * p) for p in [0.1, 0.3, 0.5, 0.7, 0.9]]
        
        best_embedding = None
        best_confidence = 0
        
        for frame_idx in sample_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue
            
            try:
                embedding_objs = DeepFace.represent(
                    frame,
                    enforce_detection=False,
                    detector_backend="opencv"
                )
                
                if embedding_objs:
                    embedding = embedding_objs[0]["embedding"]
                    confidence = embedding_objs[0].get("face_confidence", 0.5)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_embedding = embedding
                        
            except Exception as e:
                logger.debug(f"Frame {frame_idx} extraction failed: {e}")
                continue
        
        cap.release()
        
        if best_embedding:
            logger.info(f"Extracted face embedding (confidence: {best_confidence:.2f})")
            return best_embedding
        
        return None
        
    except Exception as e:
        logger.warning(f"Face embedding extraction failed: {e}")
        return None


async def extract_face_embedding_from_image(image_path: str) -> Optional[List[float]]:
    """
    Extract face embedding from a single image using DeepFace.
    
    Args:
        image_path: Path to image file
    
    Returns:
        512-dim embedding vector or None if no face found
    """
    try:
        from deepface import DeepFace
        
        embedding_objs = DeepFace.represent(
            image_path,
            enforce_detection=True,
            detector_backend="opencv"
        )
        
        if embedding_objs:
            embedding = embedding_objs[0]["embedding"]
            logger.info(f"Extracted face embedding from image: {image_path}")
            return embedding
        
        return None
        
    except Exception as e:
        logger.warning(f"Face embedding extraction from image failed: {e}")
        return None


async def identify_narrator(
    db: AsyncSession,
    video_path: Optional[str] = None,
    image_path: Optional[str] = None,
    confidence_threshold: float = SIMILARITY_THRESHOLD
) -> Dict[str, Any]:
    """
    Identify a narrator from video or image.
    
    Args:
        db: Database session
        video_path: Path to video file
        image_path: Path to image file
        confidence_threshold: Minimum similarity for match
    
    Returns:
        Dict with match result or None if no face detected
    """
    import uuid
    
    face_embedding = None
    
    if video_path:
        face_embedding = extract_face_embedding(video_path)
    elif image_path:
        face_embedding = await extract_face_embedding_from_image(image_path)
    
    if not face_embedding:
        return {
            "identified": False,
            "reason": "No face detected in provided media"
        }
    
    narrator, confidence = await identify_or_create_narrator(
        db=db,
        face_embedding=face_embedding,
        video_path=video_path or image_path or "",
        confidence_threshold=confidence_threshold
    )
    
    if not narrator:
        return {
            "identified": False,
            "reason": "Failed to create narrator profile"
        }
    
    await db.commit()
    
    return {
        "identified": True,
        "narrator_id": str(narrator.id),
        "name": narrator.name,
        "confidence": confidence,
        "is_new": not narrator.named_by_user and narrator.name.startswith("Unknown"),
        "narrative_count": narrator.narrative_count
    }


async def delete_narrator(
    db: AsyncSession,
    narrator_id: str
) -> Optional[Narrator]:
    """
    Soft delete a narrator by setting deleted_at timestamp.
    
    Args:
        db: Database session
        narrator_id: UUID of narrator to delete
    
    Returns:
        Deleted narrator or None if not found
    """
    result = await db.execute(
        select(Narrator).where(Narrator.id == narrator_id)
    )
    narrator = result.scalar_one_or_none()
    
    if not narrator:
        return None
    
    narrator.deleted_at = datetime.utcnow()
    await db.flush()
    
    logger.info(f"Soft deleted narrator: {narrator.name}")
    return narrator


async def restore_narrator(
    db: AsyncSession,
    narrator_id: str
) -> Optional[Narrator]:
    """
    Restore a soft-deleted narrator by clearing deleted_at timestamp.
    
    Args:
        db: Database session
        narrator_id: UUID of narrator to restore
    
    Returns:
        Restored narrator or None if not found
    """
    result = await db.execute(
        select(Narrator).where(Narrator.id == narrator_id)
    )
    narrator = result.scalar_one_or_none()
    
    if not narrator:
        return None
    
    narrator.deleted_at = None
    await db.flush()
    
    logger.info(f"Restored narrator: {narrator.name}")
    return narrator
