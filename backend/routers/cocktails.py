import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import cache_get, cache_set
from backend.database import get_db
from backend.dependencies import get_current_user, get_optional_user
from backend.models import User
from backend.schemas import (
    BookmarkRequest,
    CocktailFilterParams,
    CocktailListResponse,
    FavoriteRequest,
    RatingRequest,
)
from backend.services.cocktail_service import get_cocktails, get_ingredient_options

router = APIRouter(prefix="/api/cocktails", tags=["cocktails"])


@router.post("", response_model=CocktailListResponse)
async def list_cocktails(
    params: CocktailFilterParams,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    uid = user.id if user else None
    logging.warning("DEBUG list_cocktails user_id=%s favorites=%s can_make=%s", uid, params.favorites_only, params.can_make)
    return await get_cocktails(params, db, user_id=uid)


@router.get("/ingredients")
async def search_ingredients(
    search: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Name → ingredient_id lookup for the My Bar add-ingredient search."""
    cached_key = f"ingredient_search:{search.lower()}"
    cached = await cache_get(cached_key)
    if cached:
        return cached

    sql = """
        SELECT DISTINCT ON (mapped_ingredient)
            ingredient_id, ingredient, mapped_ingredient, alcohol_type
        FROM ingredients
        WHERE mapped_ingredient IS NOT NULL
          AND (mapped_ingredient ILIKE :q OR ingredient ILIKE :q)
        ORDER BY mapped_ingredient
        LIMIT 20
    """
    rows = (await db.execute(text(sql), {"q": f"%{search}%"})).mappings().all()
    result = [dict(r) for r in rows]
    await cache_set(cached_key, result, ttl=3600)
    return result


@router.get("/options")
async def ingredient_options(db: AsyncSession = Depends(get_db)):
    """Returns dropdown options for all filter controls. Cached for 1 hour."""
    cached = await cache_get("ingredient_options")
    if cached:
        return cached

    options = await get_ingredient_options(db)
    await cache_set("ingredient_options", options, ttl=3600)
    return options


@router.post("/{cocktail_id}/favorite")
async def set_favorite(
    cocktail_id: int,
    body: FavoriteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sql = """
        INSERT INTO user_favorites (user_id, cocktail_id, favorite, last_updated_ts)
        VALUES (:user_id, :cocktail_id, :favorite, now())
        ON CONFLICT (user_id, cocktail_id)
        DO UPDATE SET favorite = EXCLUDED.favorite, last_updated_ts = now()
    """
    await db.execute(
        text(sql),
        {"user_id": user.id, "cocktail_id": cocktail_id, "favorite": body.favorite},
    )
    await db.commit()
    return {"cocktail_id": cocktail_id, "favorite": body.favorite}


@router.post("/{cocktail_id}/bookmark")
async def set_bookmark(
    cocktail_id: int,
    body: BookmarkRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sql = """
        INSERT INTO user_bookmarks (user_id, cocktail_id, bookmark, last_updated_ts)
        VALUES (:user_id, :cocktail_id, :bookmark, now())
        ON CONFLICT (user_id, cocktail_id)
        DO UPDATE SET bookmark = EXCLUDED.bookmark, last_updated_ts = now()
    """
    await db.execute(
        text(sql),
        {"user_id": user.id, "cocktail_id": cocktail_id, "bookmark": body.bookmark},
    )
    await db.commit()
    return {"cocktail_id": cocktail_id, "bookmark": body.bookmark}


@router.post("/{cocktail_id}/rating")
async def set_rating(
    cocktail_id: int,
    body: RatingRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sql = """
        INSERT INTO user_ratings (user_id, cocktail_id, rating, last_updated_ts)
        VALUES (:user_id, :cocktail_id, :rating, now())
        ON CONFLICT (user_id, cocktail_id)
        DO UPDATE SET rating = EXCLUDED.rating, last_updated_ts = now()
    """
    await db.execute(
        text(sql),
        {"user_id": user.id, "cocktail_id": cocktail_id, "rating": body.rating},
    )
    await db.commit()

    # Return updated aggregate NPS for this cocktail
    nps_row = (
        await db.execute(
            text("SELECT cocktail_nps, avg_rating, num_ratings FROM vw_cocktail_ratings WHERE cocktail_id = :cid"),
            {"cid": cocktail_id},
        )
    ).mappings().one_or_none()

    return {
        "cocktail_id": cocktail_id,
        "user_rating": body.rating,
        "nps": nps_row["cocktail_nps"] if nps_row else None,
        "avg_rating": nps_row["avg_rating"] if nps_row else None,
        "num_ratings": nps_row["num_ratings"] if nps_row else None,
    }
