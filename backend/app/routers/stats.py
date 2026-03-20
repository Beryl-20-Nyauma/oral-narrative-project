"""API route handlers for statistics."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_db
from config import get_settings

router = APIRouter(prefix="/api/stats", tags=["stats"])
settings = get_settings()


@router.get("")
async def get_system_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get system-wide statistics.
    
    Args:
        db: Database session
    
    Returns:
        Dict with narrative counts, durations, emotion distribution
    """
    from app.services.stats_service import calculate_stats
    return await calculate_stats(db)


@router.get("/benchmark")
async def run_benchmark(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Run system performance benchmark.
    
    Args:
        db: Database session
    
    Returns:
        Dict with benchmark results for database, Redis, ML services
    """
    from app.services.benchmark_service import run_full_benchmark
    
    return await run_full_benchmark(
        db=db,
        redis_url=settings.redis_url
    )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Quick health check endpoint.
    
    Returns:
        Dict with health status
    """
    from app.services.benchmark_service import get_system_info, get_gpu_info
    
    return {
        "status": "healthy",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "system": get_system_info(),
        "gpu": get_gpu_info()
    }
