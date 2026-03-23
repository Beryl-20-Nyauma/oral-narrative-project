"""API route handlers for narrators."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List

from app.core.database import get_db
from app.routers.auth import require_auth, require_admin

router = APIRouter(prefix="/api/narrators", tags=["narrators"])


@router.get("")
async def list_narrators(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all known narrators.
    
    Args:
        limit: Max results to return
        offset: Pagination offset
        db: Database session
    
    Returns:
        Dict with narrators list
    """
    from app.services.narrator_service import list_narrators as _list_narrators
    return await _list_narrators(db, limit, offset)


@router.get("/{narrator_id}")
async def get_narrator(
    narrator_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get narrator details with their narratives.
    
    Args:
        narrator_id: UUID of narrator
        db: Database session
    
    Returns:
        Dict with narrator info and their narratives
    """
    from app.services.narrator_service import get_narrator_with_narratives
    narrator = await get_narrator_with_narratives(db, narrator_id)
    if not narrator:
        raise HTTPException(status_code=404, detail="Narrator not found")
    return narrator


@router.patch("/{narrator_id}")
async def rename_narrator(
    narrator_id: str,
    name: str = Form(...),
    current_user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Rename a narrator (e.g., "Unknown #5" → "Mama Fatima").
    
    Args:
        narrator_id: UUID of narrator
        name: New name for narrator
        db: Database session
    
    Returns:
        Updated narrator info
    """
    from app.services.narrator_service import rename_narrator as _rename_narrator
    narrator = await _rename_narrator(db, narrator_id, name)
    if not narrator:
        raise HTTPException(status_code=404, detail="Narrator not found")
    return {
        "id": str(narrator.id),
        "name": narrator.name,
        "named_by_user": narrator.named_by_user,
        "message": f"Narrator renamed to '{name}'"
    }


@router.post("/register")
async def register_narrator(
    name: str = Form(...),
    reference_image: UploadFile = File(...),
    current_user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Register a new narrator with a reference image.
    
    Args:
        name: Narrator name
        reference_image: Reference face image
        db: Database session
    
    Returns:
        New narrator info
    """
    from app.services.narrator_service import (
        register_narrator as _register_narrator,
        extract_face_embedding_from_image
    )
    from pathlib import Path
    from config import get_settings
    import uuid
    
    settings = get_settings()
    
    storage_dir = Path(settings.storage_dir)
    narrators_dir = storage_dir / "narrators"
    narrators_dir.mkdir(parents=True, exist_ok=True)
    
    image_path = narrators_dir / f"{uuid.uuid4()}.jpg"
    content = await reference_image.read()
    with open(image_path, "wb") as f:
        f.write(content)
    
    embedding = await extract_face_embedding_from_image(str(image_path))
    if embedding is None:
        raise HTTPException(
            status_code=400, 
            detail="No face detected in reference image"
        )
    
    narrator = await _register_narrator(
        db=db,
        name=name,
        face_embedding=embedding,
        reference_path=str(image_path),
        metadata={"source": "manual_registration"}
    )
    
    return {
        "id": str(narrator.id),
        "name": narrator.name,
        "message": f"Narrator '{name}' registered successfully"
    }


@router.get("/{narrator_id}/narratives")
async def get_narrator_narratives(
    narrator_id: str,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get all narratives for a narrator.
    
    Args:
        narrator_id: UUID of narrator
        db: Database session
    
    Returns:
        List of narratives
    """
    from app.services.narrator_service import get_narrator_with_narratives
    
    result = await get_narrator_with_narratives(db, narrator_id)
    if not result:
        raise HTTPException(status_code=404, detail="Narrator not found")
    
    return result.get("narratives", [])


@router.post("/identify")
async def identify_narrator(
    video: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    confidence_threshold: float = Form(0.85),
    current_user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Identify a narrator from uploaded video or image.
    
    Extracts face embedding and matches against known narrators.
    If no match found, creates a new "Unknown #N" narrator.
    
    Args:
        video: Video file to analyze
        image: Image file to analyze (alternative to video)
        confidence_threshold: Minimum similarity for match (default: 0.85)
        db: Database session
    
    Returns:
        Dict with identification result
    """
    from app.services.narrator_service import identify_narrator as _identify_narrator
    from pathlib import Path
    from config import get_settings
    import uuid
    import tempfile
    
    if not video and not image:
        raise HTTPException(
            status_code=400,
            detail="Either video or image file is required"
        )
    
    settings = get_settings()
    storage_dir = Path(settings.storage_dir)
    temp_dir = storage_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    video_path = None
    image_path = None
    
    try:
        if video:
            video_path = temp_dir / f"{uuid.uuid4()}{Path(video.filename).suffix}"
            content = await video.read()
            with open(video_path, "wb") as f:
                f.write(content)
        
        if image:
            image_path = temp_dir / f"{uuid.uuid4()}{Path(image.filename).suffix}"
            content = await image.read()
            with open(image_path, "wb") as f:
                f.write(content)
        
        result = await _identify_narrator(
            db=db,
            video_path=str(video_path) if video_path else None,
            image_path=str(image_path) if image_path else None,
            confidence_threshold=confidence_threshold
        )
        
        return result
        
    finally:
        if video_path:
            p = Path(video_path)
            if p.exists():
                p.unlink()
        if image_path:
            p = Path(image_path)
            if p.exists():
                p.unlink()


@router.post("/rebuild-index")
async def rebuild_faiss_index(
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Rebuild FAISS index from all narrators in database.
    
    Args:
        db: Database session
    
    Returns:
        Dict with rebuild result
    """
    from app.services.faiss_service import rebuild_index_from_db
    
    count = await rebuild_index_from_db(db)
    
    return {
        "success": True,
        "narrators_indexed": count,
        "message": f"FAISS index rebuilt with {count} narrators"
    }


@router.delete("/{narrator_id}")
async def delete_narrator(
    narrator_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Soft delete a narrator (Admin only).
    
    Args:
        narrator_id: UUID of narrator to delete
        current_user: Current authenticated admin user
        db: Database session
    
    Returns:
        Success message
    """
    from app.services.narrator_service import delete_narrator as _delete_narrator
    
    narrator = await _delete_narrator(db, narrator_id)
    
    if not narrator:
        raise HTTPException(status_code=404, detail="Narrator not found")
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Narrator '{narrator.name}' has been deleted (soft delete)"
    }
