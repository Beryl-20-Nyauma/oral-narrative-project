"""API route handlers for queue management."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_db

router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.get("/status")
async def get_queue_status() -> Dict[str, Any]:
    """
    Get Celery queue status and worker information.
    
    Returns:
        Dict with worker status, active tasks, and queue info
    """
    from app.core.celery_app import celery_app
    
    inspect = celery_app.control.inspect()
    
    stats = inspect.stats() or {}
    active = inspect.active() or {}
    reserved = inspect.reserved() or {}
    
    workers = []
    for worker_name, worker_stats in stats.items():
        workers.append({
            "name": worker_name,
            "pool": worker_stats.get("pool", {}).get("max-concurrency", "unknown"),
            "tasks_processed": worker_stats.get("total", {}).get("tasks", 0),
        })
    
    active_count = sum(len(tasks) for tasks in active.values())
    reserved_count = sum(len(tasks) for tasks in reserved.values())
    
    return {
        "workers": workers,
        "worker_count": len(workers),
        "active_tasks": active_count,
        "reserved_tasks": reserved_count,
        "queues": ["video_processing", "celery"],
    }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of a specific Celery task.
    
    Args:
        task_id: Celery task ID
    
    Returns:
        Dict with task status and result
    """
    from app.services.upload_service import get_task_status
    return await get_task_status(task_id)


@router.post("/retry/{narrative_id}")
async def retry_narrative_processing(
    narrative_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retry a failed narrative processing task.
    
    Args:
        narrative_id: UUID of the failed narrative
        db: Database session
    
    Returns:
        Dict with new task info
    """
    from app.services.upload_service import retry_failed_task
    return await retry_failed_task(narrative_id, db)
