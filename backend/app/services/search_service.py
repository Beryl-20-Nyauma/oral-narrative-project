"""Business logic for search operations."""

from typing import Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.narrative import Narrative, Theme, NarratorProfile


async def search_all_narratives(
    db: AsyncSession,
    query: str,
    field: str = "all"
) -> Dict[str, Any]:
    """
    Search narratives by query and field.
    
    Args:
        db: Database session
        query: Search query string
        field: Field to search (all, narrator, emotion, theme, keyword)
    
    Returns:
        Dict with search results
    """
    q_lower = query.lower()
    
    base_query = (
        select(Narrative)
        .options(selectinload(Narrative.themes))
        .options(selectinload(Narrative.narrator_profile))
        .where(Narrative.status == "complete")
    )
    
    conditions = []
    
    if field in ("all", "narrator"):
        conditions.append(Narrative.narrator_name.ilike(f"%{query}%"))
    
    if field in ("all", "emotion"):
        conditions.append(NarratorProfile.dominant_emotion.ilike(f"%{query}%"))
    
    if field in ("all", "theme"):
        conditions.append(Theme.name.ilike(f"%{query}%"))
    
    if field in ("all", "keyword"):
        conditions.append(Narrative.title.ilike(f"%{query}%"))
    
    if conditions:
        base_query = base_query.join(Narrative.narrator_profile, isouter=True)
        base_query = base_query.join(Narrative.themes, isouter=True)
        base_query = base_query.where(or_(*conditions))
    
    base_query = base_query.distinct()
    
    result = await db.execute(base_query)
    narratives = result.scalars().all()
    
    results = []
    for n in narratives:
        results.append({
            "id": str(n.id),
            "title": n.title,
            "narrator_name": n.narrator_name,
            "dominant_emotion": n.narrator_profile.dominant_emotion if n.narrator_profile else None,
            "themes": [t.name for t in n.themes] if n.themes else [],
        })
    
    return {"query": query, "results": results, "count": len(results)}
