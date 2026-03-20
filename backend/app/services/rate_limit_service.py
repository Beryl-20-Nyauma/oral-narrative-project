"""Rate limiting service using Redis."""

import logging
from typing import Optional, Callable
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

_redis_client = None


def init_rate_limiter(redis_url: str):
    """Initialize rate limiter with Redis connection."""
    global _redis_client
    
    try:
        import redis.asyncio as redis
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        logger.info("Rate limiter initialized with Redis")
    except Exception as e:
        logger.warning(f"Failed to initialize rate limiter: {e}")
        _redis_client = None


async def get_redis():
    """Get Redis client."""
    return _redis_client


async def is_rate_limited(
    key: str,
    max_requests: int,
    window_seconds: int
) -> tuple[bool, int, int]:
    """
    Check if request is rate limited.
    
    Args:
        key: Unique key for rate limiting (e.g., IP address or user ID)
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
    
    Returns:
        Tuple of (is_limited, current_count, remaining_requests)
    """
    if not _redis_client:
        return False, 0, max_requests
    
    try:
        current = await _redis_client.get(key)
        
        if current is None:
            await _redis_client.setex(key, window_seconds, 1)
            return False, 1, max_requests - 1
        
        current = int(current)
        
        if current >= max_requests:
            ttl = await _redis_client.ttl(key)
            return True, current, 0
        
        await _redis_client.incr(key)
        return False, current + 1, max_requests - current - 1
        
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        return False, 0, max_requests


async def reset_rate_limit(key: str):
    """Reset rate limit for a key."""
    if _redis_client:
        try:
            await _redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Rate limit reset failed: {e}")


def rate_limit(
    max_requests: int = 100,
    window_seconds: int = 60,
    key_func: Optional[Callable] = None
):
    """
    Rate limit decorator for FastAPI endpoints.
    
    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        key_func: Function to generate rate limit key (receives request)
    
    Usage:
        @rate_limit(max_requests=10, window_seconds=60)
        async def my_endpoint(request: Request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if hasattr(arg, 'client'):
                    request = arg
                    break
            
            if not request:
                for key, value in kwargs.items():
                    if hasattr(value, 'client'):
                        request = value
                        break
            
            if request:
                if key_func:
                    key = key_func(request)
                else:
                    key = f"rate_limit:{request.client.host if request.client else 'unknown'}"
                
                is_limited, count, remaining = await is_rate_limited(
                    key, max_requests, window_seconds
                )
                
                if is_limited:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded. Please try again later.",
                        headers={
                            "X-RateLimit-Limit": str(max_requests),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(window_seconds)
                        }
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
