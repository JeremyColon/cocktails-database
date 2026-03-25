import json
import logging
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)

_redis = None


async def init_cache() -> None:
    global _redis
    if not settings.redis_url:
        logger.info("REDIS_URL not set — caching disabled")
        return
    try:
        import redis.asyncio as aioredis
        _redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
        await _redis.ping()
        logger.info("Redis cache connected")
    except Exception as e:
        logger.warning(f"Redis unavailable, caching disabled: {e}")
        _redis = None


async def close_cache() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


async def cache_get(key: str) -> Any | None:
    if _redis is None:
        return None
    try:
        value = await _redis.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    if _redis is None:
        return
    try:
        await _redis.set(key, json.dumps(value), ex=ttl)
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    if _redis is None:
        return
    try:
        await _redis.delete(key)
    except Exception:
        pass


async def cache_delete_pattern(pattern: str) -> None:
    if _redis is None:
        return
    try:
        keys = await _redis.keys(pattern)
        if keys:
            await _redis.delete(*keys)
    except Exception:
        pass
