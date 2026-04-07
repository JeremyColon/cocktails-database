"""
Server-side cocktail filtering — replaces the pandas-based apply_AND_filters /
apply_OR_filters logic from the original helpers.py. All filtering is pushed
into a single parameterized SQL query so the database can use indexes.

SQL style: CTEs (WITH clauses) are preferred over nested subqueries for readability.
When user_id is present, bar_mapped is defined as a CTE and referenced by name
throughout the query rather than repeated inline.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas import CocktailFilterParams, CocktailListResponse, CocktailOut, CocktailIngredientOut

# Sort column allow-list (prevents any injection through sort_by param)
_SORT_COLUMNS = {
    "recipe_name": "c.recipe_name",
    "nps": "nps",
    "avg_rating": "avg_rating",
    "num_ratings": "num_ratings",
    "date_added": "c.date_added",
}

# CTE that resolves a user's bar to a set of mapped ingredient names.
# Referenced by name in WHERE clauses so it's never repeated inline.
_BAR_MAPPED_CTE = """
    bar_mapped AS (
        SELECT DISTINCT COALESCE(i.mapped_ingredient, i.ingredient) AS mapped_name
        FROM user_bar ub
        JOIN bars b ON b.bar_id = ub.bar_id
        CROSS JOIN LATERAL unnest(b.ingredient_list) AS ing_id
        JOIN ingredients i ON i.ingredient_id = ing_id
        WHERE ub.user_id = :user_id
    )
"""


async def get_cocktails(
    params: CocktailFilterParams,
    db: AsyncSession,
    user_id: int | None = None,
) -> CocktailListResponse:
    offset = (params.page - 1) * params.page_size
    sort_col = _SORT_COLUMNS[params.sort_by]
    sort_dir = "ASC" if params.sort_dir == "asc" else "DESC"

    ctes: list[str] = []
    where_clauses: list[str] = []
    bind: dict = {
        "user_id": user_id,
        "limit": params.page_size,
        "offset": offset,
    }

    # bar_mapped CTE — only needed when user has bar-related filters
    needs_bar_mapped = user_id and params.can_make
    if needs_bar_mapped:
        ctes.append(_BAR_MAPPED_CTE)

    # Full-text search on recipe name
    if params.search:
        where_clauses.append("c.recipe_name ILIKE :search")
        bind["search"] = f"%{params.search}%"

    # Liquor type filter
    if params.liquor_types:
        where_clauses.append(
            "EXISTS ("
            "  SELECT 1 FROM cocktails_ingredients ci_lt"
            "  JOIN ingredients i_lt ON ci_lt.ingredient_id = i_lt.ingredient_id"
            "  WHERE ci_lt.cocktail_id = c.cocktail_id"
            "  AND i_lt.alcohol_type = ANY(:liquor_types)"
            ")"
        )
        bind["liquor_types"] = params.liquor_types

    # NPS range
    if params.nps_min is not None:
        where_clauses.append("COALESCE(vr.cocktail_nps, 0) >= :nps_min")
        bind["nps_min"] = params.nps_min
    if params.nps_max is not None:
        where_clauses.append("COALESCE(vr.cocktail_nps, 0) <= :nps_max")
        bind["nps_max"] = params.nps_max

    # User-preference filters
    if user_id:
        my_cocktail_parts = []
        if params.favorites_only:
            my_cocktail_parts.append("uf.favorite = true")
        if params.bookmarks_only:
            my_cocktail_parts.append("ub.bookmark = true")
        if params.cart_only:
            my_cocktail_parts.append("uc.in_cart = true")
        if my_cocktail_parts:
            where_clauses.append(f"({' OR '.join(my_cocktail_parts)})")

    # Ingredient AND filters
    for i, ing in enumerate(params.ingredients or []):
        param = f"ing_and_{i}"
        where_clauses.append(
            f"EXISTS ("
            f"  SELECT 1 FROM cocktails_ingredients ci_{i}"
            f"  JOIN ingredients ing_{i} ON ci_{i}.ingredient_id = ing_{i}.ingredient_id"
            f"  WHERE ci_{i}.cocktail_id = c.cocktail_id"
            f"  AND ing_{i}.mapped_ingredient ILIKE :{param}"
            f")"
        )
        bind[param] = ing

    # Ingredient OR filters
    if params.ingredients_or:
        or_parts = []
        for i, ing in enumerate(params.ingredients_or):
            param = f"ing_or_{i}"
            or_parts.append(
                f"EXISTS ("
                f"  SELECT 1 FROM cocktails_ingredients ci_or_{i}"
                f"  JOIN ingredients ing_or_{i} ON ci_or_{i}.ingredient_id = ing_or_{i}.ingredient_id"
                f"  WHERE ci_or_{i}.cocktail_id = c.cocktail_id"
                f"  AND ing_or_{i}.mapped_ingredient ILIKE :{param}"
                f")"
            )
            bind[param] = ing
        where_clauses.append(f"({' OR '.join(or_parts)})")

    # Garnish filters
    if params.garnishes:
        garnish_parts = []
        for i, g in enumerate(params.garnishes):
            param = f"garnish_{i}"
            garnish_parts.append(
                f"EXISTS ("
                f"  SELECT 1 FROM cocktails_ingredients cig_{i}"
                f"  JOIN ingredients ging_{i} ON cig_{i}.ingredient_id = ging_{i}.ingredient_id"
                f"  WHERE cig_{i}.cocktail_id = c.cocktail_id"
                f"  AND cig_{i}.unit = 'garnish'"
                f"  AND ging_{i}.mapped_ingredient ILIKE :{param}"
                f")"
            )
            bind[param] = g
        where_clauses.append(f"({' OR '.join(garnish_parts)})")

    # Bitters filters
    if params.bitters:
        bitters_parts = []
        for i, b in enumerate(params.bitters):
            param = f"bitters_{i}"
            bitters_parts.append(
                f"EXISTS ("
                f"  SELECT 1 FROM cocktails_ingredients cib_{i}"
                f"  JOIN ingredients bing_{i} ON cib_{i}.ingredient_id = bing_{i}.ingredient_id"
                f"  WHERE cib_{i}.cocktail_id = c.cocktail_id"
                f"  AND bing_{i}.ingredient ILIKE '%bitters%'"
                f"  AND bing_{i}.mapped_ingredient ILIKE :{param}"
                f")"
            )
            bind[param] = b
        where_clauses.append(f"({' OR '.join(bitters_parts)})")

    # Syrup filters
    if params.syrups:
        syrups_parts = []
        for i, s in enumerate(params.syrups):
            param = f"syrup_{i}"
            syrups_parts.append(
                f"EXISTS ("
                f"  SELECT 1 FROM cocktails_ingredients cis_{i}"
                f"  JOIN ingredients sing_{i} ON cis_{i}.ingredient_id = sing_{i}.ingredient_id"
                f"  WHERE cis_{i}.cocktail_id = c.cocktail_id"
                f"  AND sing_{i}.ingredient ILIKE '%syrup%'"
                f"  AND sing_{i}.mapped_ingredient ILIKE :{param}"
                f")"
            )
            bind[param] = s
        where_clauses.append(f"({' OR '.join(syrups_parts)})")

    # Bar availability filter — references bar_mapped CTE by name
    if needs_bar_mapped:
        garnish_clause = "" if params.include_garnish else "AND ci_bar.unit != 'garnish'"
        if params.can_make == "all":
            where_clauses.append(f"""
                NOT EXISTS (
                    SELECT 1
                    FROM cocktails_ingredients ci_bar
                    JOIN ingredients i_bar ON ci_bar.ingredient_id = i_bar.ingredient_id
                    WHERE ci_bar.cocktail_id = c.cocktail_id {garnish_clause}
                    AND COALESCE(i_bar.mapped_ingredient, i_bar.ingredient)
                        NOT IN (SELECT mapped_name FROM bar_mapped)
                )
            """)
        elif params.can_make == "some":
            garnish_clause_miss = "" if params.include_garnish else "AND ci_miss.unit != 'garnish'"
            where_clauses.append(f"""
                EXISTS (
                    SELECT 1
                    FROM cocktails_ingredients ci_have
                    JOIN ingredients i_have ON ci_have.ingredient_id = i_have.ingredient_id
                    WHERE ci_have.cocktail_id = c.cocktail_id
                    AND COALESCE(i_have.mapped_ingredient, i_have.ingredient)
                        IN (SELECT mapped_name FROM bar_mapped)
                )
                AND EXISTS (
                    SELECT 1
                    FROM cocktails_ingredients ci_miss
                    JOIN ingredients i_miss ON ci_miss.ingredient_id = i_miss.ingredient_id
                    WHERE ci_miss.cocktail_id = c.cocktail_id {garnish_clause_miss}
                    AND COALESCE(i_miss.mapped_ingredient, i_miss.ingredient)
                        NOT IN (SELECT mapped_name FROM bar_mapped)
                )
            """)
        elif params.can_make == "none":
            where_clauses.append("""
                NOT EXISTS (
                    SELECT 1
                    FROM cocktails_ingredients ci_none
                    JOIN ingredients i_none ON ci_none.ingredient_id = i_none.ingredient_id
                    WHERE ci_none.cocktail_id = c.cocktail_id
                    AND COALESCE(i_none.mapped_ingredient, i_none.ingredient)
                        IN (SELECT mapped_name FROM bar_mapped)
                )
            """)

    with_clause = ("WITH " + ",\n".join(ctes)) if ctes else ""
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    user_joins = ""
    if user_id:
        user_joins = """
            LEFT JOIN user_favorites uf
                ON c.cocktail_id = uf.cocktail_id AND uf.user_id = :user_id
            LEFT JOIN user_bookmarks ub
                ON c.cocktail_id = ub.cocktail_id AND ub.user_id = :user_id
            LEFT JOIN user_ratings ur
                ON c.cocktail_id = ur.cocktail_id AND ur.user_id = :user_id
            LEFT JOIN user_cart uc
                ON c.cocktail_id = uc.cocktail_id AND uc.user_id = :user_id
        """

    select_user_cols = ""
    if user_id:
        select_user_cols = """
            COALESCE(uf.favorite, false)   AS favorited,
            COALESCE(ub.bookmark, false)   AS bookmarked,
            COALESCE(uc.in_cart, false)    AS in_cart,
            ur.rating                      AS user_rating,
        """

    base_sql = f"""
        {with_clause}
        SELECT
            c.cocktail_id,
            c.recipe_name,
            c.image,
            c.link,
            c.alcohol_type,
            c.source,
            c.date_added,
            COALESCE(vr.cocktail_nps, 0)   AS nps,
            COALESCE(vr.avg_rating, 0)     AS avg_rating,
            COALESCE(vr.num_ratings, 0)    AS num_ratings,
            {select_user_cols}
            COUNT(*) OVER ()               AS total_count
        FROM cocktails c
        LEFT JOIN vw_cocktail_ratings vr ON c.cocktail_id = vr.cocktail_id
        {user_joins}
        {where_sql}
        ORDER BY {sort_col} {sort_dir}
        LIMIT :limit OFFSET :offset
    """

    rows = (await db.execute(text(base_sql), bind)).mappings().all()

    if not rows:
        return CocktailListResponse(
            total=0, page=params.page, page_size=params.page_size, results=[]
        )

    total = rows[0]["total_count"]
    cocktail_ids = [r["cocktail_id"] for r in rows]

    # Ingredient query — bar_mapped CTE used to compute in_bar cleanly
    if user_id:
        ing_sql = f"""
            WITH {_BAR_MAPPED_CTE}
            SELECT
                ci.cocktail_id,
                i.ingredient_id,
                i.ingredient,
                i.mapped_ingredient,
                ci.unit,
                ci.quantity,
                COALESCE(i.mapped_ingredient, i.ingredient) IN (
                    SELECT mapped_name FROM bar_mapped
                ) AS in_bar
            FROM cocktails_ingredients ci
            JOIN ingredients i ON ci.ingredient_id = i.ingredient_id
            WHERE ci.cocktail_id = ANY(:cocktail_ids)
            ORDER BY ci.cocktail_id, i.ingredient
        """
    else:
        ing_sql = """
            SELECT
                ci.cocktail_id,
                i.ingredient_id,
                i.ingredient,
                i.mapped_ingredient,
                ci.unit,
                ci.quantity,
                false AS in_bar
            FROM cocktails_ingredients ci
            JOIN ingredients i ON ci.ingredient_id = i.ingredient_id
            WHERE ci.cocktail_id = ANY(:cocktail_ids)
            ORDER BY ci.cocktail_id, i.ingredient
        """

    ing_rows = (
        await db.execute(
            text(ing_sql), {"cocktail_ids": cocktail_ids, "user_id": user_id}
        )
    ).mappings().all()

    ing_map: dict[int, list] = {cid: [] for cid in cocktail_ids}
    for ir in ing_rows:
        ing_map[ir["cocktail_id"]].append(
            CocktailIngredientOut(
                ingredient_id=ir["ingredient_id"],
                ingredient=ir["ingredient"],
                mapped_ingredient=ir["mapped_ingredient"],
                unit=ir["unit"],
                quantity=ir["quantity"],
                in_bar=ir["in_bar"],
            )
        )

    results = []
    for r in rows:
        results.append(
            CocktailOut(
                cocktail_id=r["cocktail_id"],
                recipe_name=r["recipe_name"],
                image=r["image"],
                link=r["link"],
                alcohol_type=r["alcohol_type"],
                source=r["source"],
                date_added=r["date_added"],
                nps=r["nps"],
                avg_rating=r["avg_rating"],
                num_ratings=r["num_ratings"],
                favorited=r.get("favorited", False),
                bookmarked=r.get("bookmarked", False),
                in_cart=r.get("in_cart", False),
                user_rating=r.get("user_rating"),
                ingredients=ing_map.get(r["cocktail_id"], []),
            )
        )

    return CocktailListResponse(
        total=total,
        page=params.page,
        page_size=params.page_size,
        results=results,
    )


async def get_cocktail_by_id(
    cocktail_id: int,
    db: AsyncSession,
    user_id: int | None = None,
) -> CocktailOut | None:
    user_joins = ""
    if user_id:
        user_joins = """
            LEFT JOIN user_favorites uf
                ON c.cocktail_id = uf.cocktail_id AND uf.user_id = :user_id
            LEFT JOIN user_bookmarks ub
                ON c.cocktail_id = ub.cocktail_id AND ub.user_id = :user_id
            LEFT JOIN user_ratings ur
                ON c.cocktail_id = ur.cocktail_id AND ur.user_id = :user_id
            LEFT JOIN user_cart uc
                ON c.cocktail_id = uc.cocktail_id AND uc.user_id = :user_id
        """

    select_user_cols = ""
    if user_id:
        select_user_cols = """
            COALESCE(uf.favorite, false)   AS favorited,
            COALESCE(ub.bookmark, false)   AS bookmarked,
            COALESCE(uc.in_cart, false)    AS in_cart,
            ur.rating                      AS user_rating,
        """

    sql = f"""
        SELECT
            c.cocktail_id,
            c.recipe_name,
            c.image,
            c.link,
            c.alcohol_type,
            c.source,
            c.date_added,
            COALESCE(vr.cocktail_nps, 0)   AS nps,
            COALESCE(vr.avg_rating, 0)     AS avg_rating,
            COALESCE(vr.num_ratings, 0)    AS num_ratings,
            {select_user_cols}
            1 AS _placeholder
        FROM cocktails c
        LEFT JOIN vw_cocktail_ratings vr ON c.cocktail_id = vr.cocktail_id
        {user_joins}
        WHERE c.cocktail_id = :cocktail_id
    """

    row = (
        await db.execute(text(sql), {"cocktail_id": cocktail_id, "user_id": user_id})
    ).mappings().one_or_none()

    if not row:
        return None

    if user_id:
        ing_sql = f"""
            WITH {_BAR_MAPPED_CTE}
            SELECT
                ci.cocktail_id,
                i.ingredient_id,
                i.ingredient,
                i.mapped_ingredient,
                ci.unit,
                ci.quantity,
                COALESCE(i.mapped_ingredient, i.ingredient) IN (
                    SELECT mapped_name FROM bar_mapped
                ) AS in_bar
            FROM cocktails_ingredients ci
            JOIN ingredients i ON ci.ingredient_id = i.ingredient_id
            WHERE ci.cocktail_id = :cocktail_id
            ORDER BY i.ingredient
        """
    else:
        ing_sql = """
            SELECT
                ci.cocktail_id,
                i.ingredient_id,
                i.ingredient,
                i.mapped_ingredient,
                ci.unit,
                ci.quantity,
                false AS in_bar
            FROM cocktails_ingredients ci
            JOIN ingredients i ON ci.ingredient_id = i.ingredient_id
            WHERE ci.cocktail_id = :cocktail_id
            ORDER BY i.ingredient
        """

    ing_rows = (
        await db.execute(text(ing_sql), {"cocktail_id": cocktail_id, "user_id": user_id})
    ).mappings().all()

    ingredients = [
        CocktailIngredientOut(
            ingredient_id=ir["ingredient_id"],
            ingredient=ir["ingredient"],
            mapped_ingredient=ir["mapped_ingredient"],
            unit=ir["unit"],
            quantity=ir["quantity"],
            in_bar=ir["in_bar"],
        )
        for ir in ing_rows
    ]

    return CocktailOut(
        cocktail_id=row["cocktail_id"],
        recipe_name=row["recipe_name"],
        image=row["image"],
        link=row["link"],
        alcohol_type=row["alcohol_type"],
        source=row["source"],
        date_added=row["date_added"],
        nps=row["nps"],
        avg_rating=row["avg_rating"],
        num_ratings=row["num_ratings"],
        favorited=row.get("favorited", False),
        bookmarked=row.get("bookmarked", False),
        in_cart=row.get("in_cart", False),
        user_rating=row.get("user_rating"),
        ingredients=ingredients,
    )


async def get_ingredient_options(db: AsyncSession) -> dict:
    """Return all distinct filter option values for dropdowns."""
    sql = """
        SELECT DISTINCT ON (i.mapped_ingredient, ci.unit)
            i.mapped_ingredient,
            ci.unit,
            i.ingredient ILIKE '%bitters%' AS is_bitters,
            i.ingredient ILIKE '%syrup%'   AS is_syrup
        FROM ingredients i
        JOIN cocktails_ingredients ci ON i.ingredient_id = ci.ingredient_id
        WHERE i.mapped_ingredient IS NOT NULL
        ORDER BY i.mapped_ingredient, ci.unit
    """
    rows = (await db.execute(text(sql))).mappings().all()

    garnishes: set[str] = set()
    bitters: set[str] = set()
    syrups: set[str] = set()
    all_ingredients: set[str] = set()

    for r in rows:
        mi = r["mapped_ingredient"]
        all_ingredients.add(mi)
        if r["unit"] == "garnish":
            garnishes.add(mi)
        elif r["is_bitters"]:
            bitters.add(mi)
        elif r["is_syrup"]:
            syrups.add(mi)

    lt_rows = (
        await db.execute(
            text("SELECT DISTINCT alcohol_type FROM ingredients WHERE alcohol_type IS NOT NULL ORDER BY alcohol_type")
        )
    ).scalars().all()

    return {
        "liquor_types": list(lt_rows),
        "ingredients": sorted(all_ingredients - garnishes - bitters - syrups),
        "garnishes": sorted(garnishes),
        "bitters": sorted(bitters),
        "syrups": sorted(syrups),
    }
