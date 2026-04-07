from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import cache_delete, cache_get, cache_set
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import User
from backend.schemas import (
    AcceptLinkRequest,
    BarAddRequest, BarLinkPreview, BarLinkStatus, BarRemoveRequest, BarResponse,
    BarSharePreview, BarStatsResponse, BarUpdateRequest, ImportBarRequest,
    LinkInviteResponse, ShareTokenResponse, StartersResponse,
)
from backend.services.bar_service import (
    accept_link_invite,
    add_to_bar,
    create_link_invite,
    create_share_token,
    get_bar,
    get_bar_stats,
    get_link_preview,
    get_link_status,
    get_share_preview,
    get_starters,
    import_shared_bar,
    remove_from_bar,
    set_bar,
    unlink_bar,
)

router = APIRouter(prefix="/api/bar", tags=["bar"])

_BAR_CACHE_TTL = 300  # 5 minutes


def _bar_key(user_id: int) -> str:
    return f"bar:{user_id}"

def _stats_key(user_id: int, include_garnish: bool) -> str:
    return f"bar_stats:{user_id}:{include_garnish}"


async def _invalidate_household_caches(user_id: int, db: AsyncSession) -> None:
    """Invalidate bar caches for every user sharing this user's bar (household-aware)."""
    uids = (await db.execute(
        text("""
            SELECT ub2.user_id
            FROM user_bar ub1
            JOIN user_bar ub2 ON ub2.bar_id = ub1.bar_id
            WHERE ub1.user_id = :uid
        """),
        {"uid": user_id},
    )).scalars().all()
    for uid in uids:
        await cache_delete(_bar_key(uid))
        await cache_delete(_stats_key(uid, True))
        await cache_delete(_stats_key(uid, False))


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
    await _invalidate_household_caches(user.id, db)
    return await get_bar(user.id, db)


@router.post("/add", response_model=BarResponse)
async def add_ingredients(
    body: BarAddRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await add_to_bar(user.id, body.ingredient_ids, db)
    await _invalidate_household_caches(user.id, db)
    return await get_bar(user.id, db)


@router.post("/remove", response_model=BarResponse)
async def remove_ingredients(
    body: BarRemoveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await remove_from_bar(user.id, body.ingredient_ids, db)
    await _invalidate_household_caches(user.id, db)
    return await get_bar(user.id, db)


@router.get("/starters", response_model=StartersResponse)
async def bar_starters(db: AsyncSession = Depends(get_db)):
    """Curated starter kits + top 20 global ingredients. Cached for 1 hour."""
    cached = await cache_get("bar_starters")
    if cached:
        return cached

    result = await get_starters(db)
    await cache_set("bar_starters", result.model_dump(), ttl=3600)
    return result


@router.post("/share", response_model=ShareTokenResponse)
async def generate_share_token(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate (or replace) a 7-day share token for the current user's bar."""
    return await create_share_token(user.id, db)


@router.get("/share/{token}", response_model=BarSharePreview)
async def preview_shared_bar(token: str, db: AsyncSession = Depends(get_db)):
    """Public endpoint — preview of the shared bar for the given token."""
    preview = await get_share_preview(token, db)
    if not preview:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    return preview


@router.post("/import/{token}", response_model=BarResponse)
async def import_bar(
    token: str,
    body: ImportBarRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Import a shared bar. mode='add' merges; mode='replace' replaces."""
    result = await import_shared_bar(token, user.id, body.mode, db)
    if not result:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    await _invalidate_household_caches(user.id, db)
    return result


@router.get("/link/status", response_model=BarLinkStatus)
async def link_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_link_status(user.id, db)


@router.post("/link/invite", response_model=LinkInviteResponse)
async def create_invite(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a 7-day household link invite token."""
    return await create_link_invite(user.id, db)


@router.get("/link/preview/{token}", response_model=BarLinkPreview)
async def preview_link(token: str, db: AsyncSession = Depends(get_db)):
    """Public — returns the inviter's email so the acceptor knows who they're linking with."""
    preview = await get_link_preview(token, db)
    if not preview:
        raise HTTPException(status_code=404, detail="Invite link not found or expired")
    return preview


@router.post("/link/accept/{token}", response_model=BarResponse)
async def accept_invite(
    token: str,
    body: AcceptLinkRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Accept a household link invite. mode='merge' or 'replace'."""
    ok = await accept_link_invite(token, user.id, body.mode, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Invite link not found, expired, or already used")
    await _invalidate_household_caches(user.id, db)
    return await get_bar(user.id, db)


@router.delete("/link")
async def unlink(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Leave the shared household bar and get a fresh empty bar."""
    # Invalidate before unlinking (while we can still find household members)
    await _invalidate_household_caches(user.id, db)
    await unlink_bar(user.id, db)
    await cache_delete(_bar_key(user.id))
    await cache_delete(_stats_key(user.id, True))
    await cache_delete(_stats_key(user.id, False))
    return {"unlinked": True}


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
