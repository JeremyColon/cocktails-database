"""
Admin router — ingredient mapping management.
All endpoints require the requesting user to be the configured admin.
"""
import difflib
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import User

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Common modifiers to strip when generating suggestions
_STRIP_WORDS = {
    "fresh", "freshly", "freshly-squeezed", "dry", "aged", "good", "quality",
    "homemade", "store-bought", "chilled", "cold", "hot", "warm", "room",
    "temperature", "finely", "coarsely", "roughly", "thinly", "sliced",
    "chopped", "minced", "crushed", "ground", "whole", "large", "small",
    "medium", "extra", "light", "dark", "white", "black", "red", "green",
    "pure", "premium", "organic", "unsweetened", "sweetened", "salted",
    "unsalted", "plus", "more", "garnish", "optional", "divided",
}


def _get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.id != settings.admin_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def _clean_for_suggestion(name: str) -> str:
    """Strip modifiers and punctuation to get a clean ingredient core."""
    name = name.lower().strip()
    # Remove quantities and units at the start (e.g. "2 oz ", "1/2 cup ")
    name = re.sub(r"^[\d/\s]+(oz|ounce|cup|tbsp|tsp|ml|dash|drop|part|piece|slice)s?\s+", "", name)
    words = [w for w in re.split(r"[\s,]+", name) if w and w not in _STRIP_WORDS]
    return " ".join(words)


def _score_suggestions(raw: str, candidates: list[str]) -> list[str]:
    """
    Return up to 5 suggestions for `raw` from `candidates`, ranked by:
    1. Exact match after cleaning
    2. Candidate is a substring of raw (or vice versa)
    3. difflib SequenceMatcher ratio
    4. Word overlap ratio
    """
    clean = _clean_for_suggestion(raw)
    scored: list[tuple[float, str]] = []

    for c in candidates:
        c_clean = _clean_for_suggestion(c)
        score = 0.0

        if c_clean == clean:
            score = 1.0
        elif c_clean in clean or clean in c_clean:
            # Prefer longer containment (more specific)
            score = 0.85 + 0.1 * len(min(c_clean, clean)) / max(len(c_clean), len(clean), 1)
        else:
            ratio = difflib.SequenceMatcher(None, clean, c_clean).ratio()
            words_raw = set(clean.split())
            words_c = set(c_clean.split())
            overlap = len(words_raw & words_c) / max(len(words_raw | words_c), 1)
            score = max(ratio, overlap)

        if score > 0.3:
            scored.append((score, c))

    scored.sort(key=lambda x: -x[0])
    # Deduplicate while preserving order
    seen: set[str] = set()
    results: list[str] = []
    for _, c in scored:
        if c not in seen:
            seen.add(c)
            results.append(c)
        if len(results) == 5:
            break
    return results


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/unmapped")
async def list_unmapped(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_get_admin_user),
):
    """Return all unmapped ingredients sorted by how many cocktails they affect."""
    rows = (
        await db.execute(text("""
            SELECT
                i.ingredient_id,
                i.ingredient,
                i.alcohol_type,
                COUNT(DISTINCT ci.cocktail_id) AS cocktail_count
            FROM ingredients i
            JOIN cocktails_ingredients ci ON i.ingredient_id = ci.ingredient_id
            WHERE i.mapped_ingredient IS NULL
            GROUP BY i.ingredient_id, i.ingredient, i.alcohol_type
            ORDER BY cocktail_count DESC, i.ingredient
        """))
    ).mappings().all()

    return [dict(r) for r in rows]


@router.get("/suggestions/{ingredient_id}")
async def get_suggestions(
    ingredient_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_get_admin_user),
):
    """Return up to 5 suggested mappings for an unmapped ingredient."""
    # Get the ingredient name
    row = (
        await db.execute(
            text("SELECT ingredient FROM ingredients WHERE ingredient_id = :id"),
            {"id": ingredient_id},
        )
    ).mappings().one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    # Get all distinct existing mapped_ingredient values as candidates
    candidates = (
        await db.execute(
            text("SELECT DISTINCT mapped_ingredient FROM ingredients WHERE mapped_ingredient IS NOT NULL ORDER BY mapped_ingredient")
        )
    ).scalars().all()

    suggestions = _score_suggestions(row["ingredient"], list(candidates))
    return {"ingredient": row["ingredient"], "suggestions": suggestions}


class MappingUpdate(BaseModel):
    mapped_ingredient: str
    alcohol_type: str | None = None


@router.patch("/ingredients/{ingredient_id}")
async def update_mapping(
    ingredient_id: int,
    body: MappingUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_get_admin_user),
):
    """Set mapped_ingredient (and optionally alcohol_type) for an ingredient."""
    result = await db.execute(
        text("""
            UPDATE ingredients
            SET mapped_ingredient = :mapped,
                alcohol_type = COALESCE(:alcohol_type, alcohol_type)
            WHERE ingredient_id = :id
            RETURNING ingredient_id, ingredient, mapped_ingredient, alcohol_type
        """),
        {"id": ingredient_id, "mapped": body.mapped_ingredient.strip(), "alcohol_type": body.alcohol_type},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    await db.commit()
    return dict(row)


@router.get("/alcohol-types")
async def list_alcohol_types(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_get_admin_user),
):
    """Return all distinct alcohol_type values for the dropdown."""
    types = (
        await db.execute(
            text("SELECT DISTINCT alcohol_type FROM ingredients WHERE alcohol_type IS NOT NULL ORDER BY alcohol_type")
        )
    ).scalars().all()
    return list(types)
