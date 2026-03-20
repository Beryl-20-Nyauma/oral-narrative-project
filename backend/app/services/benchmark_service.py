"""Performance benchmark service for measuring system metrics."""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import sys

logger = logging.getLogger(__name__)


def get_system_info() -> Dict[str, Any]:
    """
    Get system information.
    
    Returns:
        Dict with CPU, memory, and platform info
    """
    import platform
    
    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count() or 1,
    }
    
    try:
        import psutil
        info["memory_total_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
        info["memory_available_gb"] = round(psutil.virtual_memory().available / (1024**3), 2)
        info["cpu_percent"] = psutil.cpu_percent(interval=0.1)
    except ImportError:
        info["memory_total_gb"] = "psutil not installed"
        info["memory_available_gb"] = "psutil not installed"
        info["cpu_percent"] = "psutil not installed"
    
    return info


def get_gpu_info() -> Dict[str, Any]:
    """
    Get GPU information if available.
    
    Returns:
        Dict with GPU info
    """
    info = {
        "cuda_available": False,
        "device_count": 0,
        "devices": []
    }
    
    try:
        import torch
        info["cuda_available"] = torch.cuda.is_available()
        
        if info["cuda_available"]:
            info["device_count"] = torch.cuda.device_count()
            info["devices"] = [
                {
                    "name": torch.cuda.get_device_name(i),
                    "memory_total_gb": round(torch.cuda.get_device_properties(i).total_memory / (1024**3), 2)
                }
                for i in range(info["device_count"])
            ]
    except ImportError:
        info["error"] = "PyTorch not installed"
    
    return info


async def benchmark_database(db) -> Dict[str, Any]:
    """
    Benchmark database operations.
    
    Args:
        db: Database session
    
    Returns:
        Dict with benchmark results
    """
    from sqlalchemy import text
    
    results = {}
    
    start = time.perf_counter()
    await db.execute(text("SELECT 1"))
    results["simple_query_ms"] = round((time.perf_counter() - start) * 1000, 2)
    
    start = time.perf_counter()
    await db.execute(text("SELECT COUNT(*) FROM narratives"))
    results["count_query_ms"] = round((time.perf_counter() - start) * 1000, 2)
    
    return results


async def benchmark_redis(redis_url: str) -> Dict[str, Any]:
    """
    Benchmark Redis operations.
    
    Args:
        redis_url: Redis connection URL
    
    Returns:
        Dict with benchmark results
    """
    results = {"available": False}
    
    try:
        import redis.asyncio as redis
        
        client = redis.from_url(redis_url)
        
        start = time.perf_counter()
        await client.ping()
        results["ping_ms"] = round((time.perf_counter() - start) * 1000, 2)
        
        start = time.perf_counter()
        await client.set("benchmark_key", "benchmark_value", ex=10)
        results["set_ms"] = round((time.perf_counter() - start) * 1000, 2)
        
        start = time.perf_counter()
        value = await client.get("benchmark_key")
        results["get_ms"] = round((time.perf_counter() - start) * 1000, 2)
        
        results["available"] = True
        
        await client.close()
        
    except Exception as e:
        results["error"] = str(e)
    
    return results


async def benchmark_ml_services() -> Dict[str, Any]:
    """
    Benchmark ML service inference times.
    
    Returns:
        Dict with benchmark results
    """
    results = {}
    
    results["whisper_model"] = "not_tested"
    results["deepface_model"] = "not_tested"
    
    return results


def measure_memory_usage() -> Dict[str, Any]:
    """
    Measure current memory usage.
    
    Returns:
        Dict with memory stats
    """
    try:
        import psutil
        import tracemalloc
        
        process = psutil.Process(os.getpid())
        
        return {
            "rss_mb": round(process.memory_info().rss / (1024**2), 2),
            "vms_mb": round(process.memory_info().vms / (1024**2), 2),
            "percent": round(process.memory_percent(), 2)
        }
    except ImportError:
        return {"error": "psutil not installed"}


async def run_full_benchmark(
    db=None,
    redis_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run full system benchmark.
    
    Args:
        db: Optional database session
        redis_url: Optional Redis URL
    
    Returns:
        Dict with all benchmark results
    """
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "system": get_system_info(),
        "gpu": get_gpu_info(),
        "memory": measure_memory_usage(),
        "services": {}
    }
    
    if db:
        results["services"]["database"] = await benchmark_database(db)
    
    if redis_url:
        results["services"]["redis"] = await benchmark_redis(redis_url)
    
    results["services"]["ml"] = await benchmark_ml_services()
    
    return results


class PerformanceTracker:
    """Track performance metrics during processing."""
    
    def __init__(self):
        self.metrics: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
    
    def start(self):
        """Start tracking."""
        self.start_time = time.perf_counter()
    
    def record(self, stage: str, metadata: Optional[Dict] = None):
        """Record a stage completion."""
        if self.start_time is None:
            return
        
        elapsed = time.perf_counter() - self.start_time
        
        self.metrics.append({
            "stage": stage,
            "elapsed_sec": round(elapsed, 3),
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.metrics:
            return {"total_time_sec": 0, "stages": []}
        
        total_time = self.metrics[-1]["elapsed_sec"] if self.metrics else 0
        
        return {
            "total_time_sec": round(total_time, 3),
            "stages": self.metrics,
            "stage_count": len(self.metrics)
        }
