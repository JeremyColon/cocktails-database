from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import cache_delete, cache_get, cache_set
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import User
from backend.schemas import BarAddRequest, BarRemoveRequest, BarResponse, BarStatsResponse, BarUpdateRequest
from backend.services.bar_service import (
    add_to_bar,
    get_bar,
    get_bar_stats,
    remove_from_bar,
    set_bar,
)

router = APIRouter(prefix="/api/bar", tags=["bar"])

_BAR_CACHE_TTL = 300  # 5 minutes


def _bar_key(user_id: int) -> str:
    return f"bar:{user_id}"

def _stats_key(user_id: int, include_garnish: bool) -> str:
    return f"bar_stats:{user_id}:{include_garnish}"


@router.get("", response_model=BarResponse)
async def get_my_bar(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cached = await cache_get(_bar_key(user.id))
    if cached:
        return cached

    result = await get_bar(user.id, db)
    await cache_set(_bar_key(user.id), result.model_dump(), ttl=_BAR_CACHE_TTL)
    return result


@router.put("", response_model=BarResponse)
async def replace_bar(
    body: BarUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await set_bar(user.id, body.ingredient_ids, db)
    await cache_delete(_bar_key(user.id))
    await cache_delete(_stats_key(user.id, True))
    await cache_delete(_stats_key(user.id, False))
    return await get_bar(user.id, db)


@router.post("/add", response_model=BarResponse)
async def add_ingredients(
    body: BarAddRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await add_to_bar(user.id, body.ingredient_ids, db)
    await cache_delete(_bar_key(user.id))
    await cache_delete(_stats_key(user.id, True))
    await cache_delete(_stats_key(user.id, False))
    return await get_bar(user.id, db)


@router.post("/remove", response_model=BarResponse)
async def remove_ingredients(
    body: BarRemoveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await remove_from_bar(user.id, body.ingredient_ids, db)
    await cache_delete(_bar_key(user.id))
    await cache_delete(_stats_key(user.id, True))
    await cache_delete(_stats_key(user.id, False))
    return await get_bar(user.id, db)


@router.get("/stats", response_model=BarStatsResponse)
async def bar_stats(
    include_garnish: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    key = _stats_key(user.id, include_garnish)
    cached = await cache_get(key)
    if cached:
        return cached

    result = await get_bar_stats(user.id, db, include_garnish=include_garnish)
    await cache_set(key, result.model_dump(), ttl=_BAR_CACHE_TTL)
    return result
