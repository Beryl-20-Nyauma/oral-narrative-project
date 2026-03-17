"""API route handlers for search."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_db

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search_narratives(
    q: str,
    field: str = "all",
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Full-text search across narratives by narrator, emotion, theme, or keyword.
    
    Args:
        q: Search query string
        field: Field to search (all, narrator, emotion, theme, keyword)
        db: Database session
    
    Returns:
        Dict with search results
    """
    from app.services.search_service import search_all_narratives
    return await search_all_narratives(db, q, field)
