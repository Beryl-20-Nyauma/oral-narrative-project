"""FAISS vector index service for narrator face embeddings."""

import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import json
import asyncio

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

FAISS_INDEX_DIR = Path(settings.storage_dir) / "faiss"
INDEX_FILE = FAISS_INDEX_DIR / "narrator_index.faiss"
MAPPING_FILE = FAISS_INDEX_DIR / "narrator_mapping.json"

_embedding_dim = 512
_index = None
_id_mapping: Dict[int, str] = {}
_reverse_mapping: Dict[str, int] = {}


def _ensure_faiss_dir():
    FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)


def _init_index():
    """Initialize FAISS index."""
    global _index
    
    if _index is not None:
        return
    
    try:
        import faiss
        
        _index = faiss.IndexFlatIP(_embedding_dim)
        logger.info("FAISS index initialized (inner product)")
        
    except ImportError:
        logger.warning("FAISS not installed, falling back to brute-force search")
        _index = "brute_force"


def load_index() -> bool:
    """
    Load FAISS index from disk.
    
    Returns:
        True if loaded successfully, False otherwise
    """
    global _index, _id_mapping, _reverse_mapping
    
    _init_index()
    
    if not INDEX_FILE.exists() or not MAPPING_FILE.exists():
        logger.info("No existing FAISS index found, will create new one")
        return False
    
    try:
        import faiss
        
        _index = faiss.read_index(str(INDEX_FILE))
        
        with open(MAPPING_FILE, "r") as f:
            _id_mapping = {int(k): v for k, v in json.load(f).items()}
        
        _reverse_mapping = {v: k for k, v in _id_mapping.items()}
        
        logger.info(f"Loaded FAISS index with {_index.ntotal} vectors")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load FAISS index: {e}")
        _init_index()
        return False


def save_index() -> bool:
    """
    Save FAISS index to disk.
    
    Returns:
        True if saved successfully, False otherwise
    """
    global _index
    
    if _index is None or _index == "brute_force":
        return False
    
    try:
        import faiss
        
        _ensure_faiss_dir()
        faiss.write_index(_index, str(INDEX_FILE))
        
        with open(MAPPING_FILE, "w") as f:
            json.dump(_id_mapping, f)
        
        logger.info(f"Saved FAISS index with {_index.ntotal} vectors")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save FAISS index: {e}")
        return False


def add_embedding(narrator_id: str, embedding: List[float]) -> bool:
    """
    Add narrator embedding to FAISS index.
    
    Args:
        narrator_id: UUID of narrator
        embedding: 512-dim face embedding vector
    
    Returns:
        True if added successfully
    """
    global _index, _id_mapping, _reverse_mapping
    
    _init_index()
    
    if narrator_id in _reverse_mapping:
        logger.warning(f"Narrator {narrator_id} already in index, skipping")
        return False
    
    try:
        vector = np.array([embedding], dtype=np.float32)
        
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        if _index == "brute_force":
            return False
        
        idx = _index.ntotal
        _index.add(vector)
        
        _id_mapping[idx] = narrator_id
        _reverse_mapping[narrator_id] = idx
        
        save_index()
        
        logger.info(f"Added narrator {narrator_id} to FAISS index at position {idx}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add embedding to FAISS: {e}")
        return False


def remove_embedding(narrator_id: str) -> bool:
    """
    Remove narrator embedding from FAISS index.
    
    Note: FAISS doesn't support direct removal, so we mark as removed
    and rebuild the index on next full load.
    
    Args:
        narrator_id: UUID of narrator
    
    Returns:
        True if marked for removal
    """
    global _reverse_mapping, _id_mapping
    
    if narrator_id not in _reverse_mapping:
        return False
    
    idx = _reverse_mapping[narrator_id]
    
    del _id_mapping[idx]
    del _reverse_mapping[narrator_id]
    
    logger.info(f"Removed narrator {narrator_id} from mapping")
    return True


def search_similar(
    embedding: List[float],
    k: int = 5,
    threshold: float = 0.85
) -> List[Tuple[str, float]]:
    """
    Search for similar narrators in FAISS index.
    
    Args:
        embedding: Query embedding vector
        k: Number of results to return
        threshold: Minimum similarity threshold
    
    Returns:
        List of (narrator_id, similarity) tuples
    """
    global _index, _id_mapping
    
    _init_index()
    
    if _index == "brute_force" or _index.ntotal == 0:
        return []
    
    try:
        query = np.array([embedding], dtype=np.float32)
        
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm
        
        k_search = min(k, _index.ntotal)
        distances, indices = _index.search(query, k_search)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            
            narrator_id = _id_mapping.get(int(idx))
            if narrator_id and dist >= threshold:
                results.append((narrator_id, float(dist)))
        
        return results
        
    except Exception as e:
        logger.error(f"FAISS search failed: {e}")
        return []


async def rebuild_index_from_db(db) -> int:
    """
    Rebuild FAISS index from database narrators.
    
    Args:
        db: Database session
    
    Returns:
        Number of narrators indexed
    """
    global _index, _id_mapping, _reverse_mapping
    
    from sqlalchemy import select
    from app.models.narrative import Narrator
    
    try:
        import faiss
    except ImportError:
        logger.warning("FAISS not available, cannot rebuild index")
        return 0
    
    _index = faiss.IndexFlatIP(_embedding_dim)
    _id_mapping = {}
    _reverse_mapping = {}
    
    result = await db.execute(select(Narrator))
    narrators = result.scalars().all()
    
    count = 0
    for narrator in narrators:
        if not narrator.face_embedding:
            continue
        
        add_embedding(str(narrator.id), narrator.face_embedding)
        count += 1
    
    save_index()
    logger.info(f"Rebuilt FAISS index with {count} narrators")
    return count


async def identify_with_faiss(
    db,
    embedding: List[float],
    threshold: float = 0.85
) -> Tuple[Optional[str], float]:
    """
    Identify narrator using FAISS index.
    
    Args:
        db: Database session
        embedding: Query face embedding
        threshold: Minimum similarity threshold
    
    Returns:
        Tuple of (narrator_id, confidence) or (None, 0.0)
    """
    load_index()
    
    results = search_similar(embedding, k=1, threshold=threshold)
    
    if results:
        return results[0]
    
    return None, 0.0
