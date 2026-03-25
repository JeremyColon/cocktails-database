"""
Bar service — replaces get_available_cocktails() and my_bar_outputs() from helpers.py.
All matching is done at the mapped_ingredient level so that adding "mint" covers
mint leaves, mint sprigs, etc. without requiring each variant to be added separately.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas import (
    BarIngredient,
    BarResponse,
    BarStatsResponse,
    MissingIngredient,
)

# Reusable snippet: the set of mapped_ingredient values the user has in their bar
_MY_BAR_MAPPED_CTE = """
    my_bar_mapped AS (
        SELECT DISTINCT COALESCE(i.mapped_ingredient, i.ingredient) AS mapped_name
        FROM user_bar ub
        CROSS JOIN LATERAL unnest(ub.ingredient_list) AS bar_id
        JOIN ingredients i ON i.ingredient_id = bar_id
        WHERE ub.user_id = :user_id
    )
"""


async def get_bar(user_id: int, db: AsyncSession) -> BarResponse:
    # DISTINCT ON mapped_ingredient so duplicate mappings show only once
    sql = """
        SELECT DISTINCT ON (COALESCE(i.mapped_ingredient, i.ingredient))
            i.ingredient_id, i.ingredient, i.mapped_ingredient, i.alcohol_type
        FROM ingredients i
        JOIN (
            SELECT unnest(ingredient_list) AS ingredient_id
            FROM user_bar WHERE user_id = :user_id
        ) ub ON i.ingredient_id = ub.ingredient_id
        ORDER BY COALESCE(i.mapped_ingredient, i.ingredient)
    """
    rows = (await db.execute(text(sql), {"user_id": user_id})).mappings().all()
    return BarResponse(
        ingredients=[
            BarIngredient(
                ingredient_id=r["ingredient_id"],
                ingredient=r["ingredient"],
                mapped_ingredient=r["mapped_ingredient"],
                alcohol_type=r["alcohol_type"],
            )
            for r in rows
        ]
    )


async def set_bar(user_id: int, ingredient_ids: list[int], db: AsyncSession) -> None:
    """Full replacement of the user's bar ingredient list."""
    sql = """
        INSERT INTO user_bar (user_id, ingredient_list, last_updated_ts)
        VALUES (:user_id, :ingredient_list, now())
        ON CONFLICT (user_id)
        DO UPDATE SET ingredient_list = EXCLUDED.ingredient_list,
                      last_updated_ts = now()
    """
    await db.execute(text(sql), {"user_id": user_id, "ingredient_list": ingredient_ids})
    await db.commit()


async def add_to_bar(user_id: int, ingredient_ids: list[int], db: AsyncSession) -> None:
    sql = """
        INSERT INTO user_bar (user_id, ingredient_list, last_updated_ts)
        VALUES (:user_id, :ingredient_list, now())
        ON CONFLICT (user_id)
        DO UPDATE SET
            ingredient_list = (
                SELECT array_agg(DISTINCT x)
                FROM unnest(user_bar.ingredient_list || :ingredient_list) x
            ),
            last_updated_ts = now()
    """
    await db.execute(text(sql), {"user_id": user_id, "ingredient_list": ingredient_ids})
    await db.commit()


async def remove_from_bar(user_id: int, ingredient_ids: list[int], db: AsyncSession) -> None:
    # Remove all IDs that share the same mapped_ingredient as any of the given IDs,
    # so removing "mint" clears mint leaves, mint sprigs, etc. in one go.
    sql = """
        UPDATE user_bar
        SET ingredient_list = (
            SELECT array_agg(x)
            FROM unnest(ingredient_list) x
            WHERE x NOT IN (
                SELECT i2.ingredient_id
                FROM ingredients i2
                WHERE COALESCE(i2.mapped_ingredient, i2.ingredient) IN (
                    SELECT COALESCE(i1.mapped_ingredient, i1.ingredient)
                    FROM ingredients i1
                    WHERE i1.ingredient_id = ANY(:remove_ids)
                )
            )
        ),
        last_updated_ts = now()
        WHERE user_id = :user_id
    """
    await db.execute(text(sql), {"user_id": user_id, "remove_ids": ingredient_ids})
    await db.commit()


async def get_bar_stats(
    user_id: int, db: AsyncSession, include_garnish: bool = True
) -> BarStatsResponse:
    """
    Returns can_make / partial / cannot_make counts plus top missing ingredients.
    Matching is at the mapped_ingredient level.
    """
    garnish_filter = "" if include_garnish else "AND ci.unit != 'garnish'"

    stats_sql = f"""
        WITH {_MY_BAR_MAPPED_CTE},
        cocktail_totals AS (
            SELECT
                ci.cocktail_id,
                COUNT(*) FILTER (WHERE ci.unit != 'garnish' OR :include_garnish)   AS total_needed,
                COUNT(*) FILTER (WHERE mb.mapped_name IS NOT NULL
                                 AND (ci.unit != 'garnish' OR :include_garnish))    AS have_count
            FROM cocktails_ingredients ci
            JOIN ingredients i ON ci.ingredient_id = i.ingredient_id
            LEFT JOIN my_bar_mapped mb
                   ON COALESCE(i.mapped_ingredient, i.ingredient) = mb.mapped_name
            {garnish_filter}
            GROUP BY ci.cocktail_id
        )
        SELECT
            SUM(CASE WHEN have_count = total_needed THEN 1 ELSE 0 END) AS can_make_count,
            SUM(CASE WHEN have_count > 0 AND have_count < total_needed THEN 1 ELSE 0 END) AS partial_count,
            SUM(CASE WHEN have_count = 0 THEN 1 ELSE 0 END) AS cannot_make_count
        FROM cocktail_totals
    """

    stats_row = (
        await db.execute(
            text(stats_sql), {"user_id": user_id, "include_garnish": include_garnish}
        )
    ).mappings().one()

    # Top missing — group by mapped_ingredient so variants don't split the count
    missing_sql = f"""
        WITH {_MY_BAR_MAPPED_CTE},
        missing_mapped AS (
            SELECT DISTINCT
                COALESCE(i.mapped_ingredient, i.ingredient) AS mapped_name,
                ci.cocktail_id
            FROM cocktails_ingredients ci
            JOIN ingredients i ON ci.ingredient_id = i.ingredient_id
            LEFT JOIN my_bar_mapped mb
                   ON COALESCE(i.mapped_ingredient, i.ingredient) = mb.mapped_name
            WHERE mb.mapped_name IS NULL
            {garnish_filter}
        )
        SELECT
            MIN(i.ingredient_id) AS ingredient_id,
            mm.mapped_name       AS mapped_ingredient,
            COUNT(DISTINCT mm.cocktail_id) AS cocktail_count
        FROM missing_mapped mm
        JOIN ingredients i ON COALESCE(i.mapped_ingredient, i.ingredient) = mm.mapped_name
        GROUP BY mm.mapped_name
        ORDER BY cocktail_count DESC
        LIMIT 10
    """

    missing_rows = (
        await db.execute(text(missing_sql), {"user_id": user_id})
    ).mappings().all()

    return BarStatsResponse(
        can_make_count=stats_row["can_make_count"] or 0,
        partial_count=stats_row["partial_count"] or 0,
        cannot_make_count=stats_row["cannot_make_count"] or 0,
        top_missing=[
            MissingIngredient(
                ingredient_id=r["ingredient_id"],
                mapped_ingredient=r["mapped_ingredient"],
                cocktail_count=r["cocktail_count"],
            )
            for r in missing_rows
        ],
    )
