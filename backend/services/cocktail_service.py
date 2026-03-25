"""
Server-side cocktail filtering — replaces the pandas-based apply_AND_filters /
apply_OR_filters logic from the original helpers.py. All filtering is pushed
into a single parameterized SQL query so the database can use indexes.
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


async def get_cocktails(
    params: CocktailFilterParams,
    db: AsyncSession,
    user_id: int | None = None,
) -> CocktailListResponse:
    offset = (params.page - 1) * params.page_size
    sort_col = _SORT_COLUMNS[params.sort_by]
    sort_dir = "ASC" if params.sort_dir == "asc" else "DESC"

    # Build dynamic WHERE clauses and bind parameters
    where_clauses = []
    bind = {
        "user_id": user_id,
        "limit": params.page_size,
        "offset": offset,
    }

    # Full-text search on recipe name
    if params.search:
        where_clauses.append("c.recipe_name ILIKE :search")
        bind["search"] = f"%{params.search}%"

    # Liquor type filter — match via ingredients.alcohol_type (populated from ingredient_map.csv)
    # c.alcohol_type is only set for scraped cocktails; existing cocktails use ingredient-level types
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

    # User-preference filters — only applied when logged in
    # favorites/bookmarks use OR between them (show if either matches)
    if user_id:
        my_cocktail_parts = []
        if params.favorites_only:
            my_cocktail_parts.append("uf.favorite = true")
        if params.bookmarks_only:
            my_cocktail_parts.append("ub.bookmark = true")
        if my_cocktail_parts:
            where_clauses.append(f"({' OR '.join(my_cocktail_parts)})")

    # Ingredient AND filters — each ingredient must appear in the cocktail
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

    # Ingredient OR filters — at least one ingredient must appear
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

    # Garnish filters — OR within (at least one of the selected garnishes must appear)
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

    # Bitters filters — OR within
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

    # Syrup filters — OR within
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

    # Bar availability filter — matched at mapped_ingredient level
    if user_id and params.can_make:
        garnish_clause = "" if params.include_garnish else "AND ci_bar.unit != 'garnish'"
        # CTE-style subquery: mapped names the user has
        bar_mapped = (
            "SELECT DISTINCT COALESCE(ib.mapped_ingredient, ib.ingredient) AS mapped_name"
            " FROM ingredients ib"
            " CROSS JOIN LATERAL unnest((SELECT ingredient_list FROM user_bar WHERE user_id = :user_id)) AS bar_id"
            " WHERE ib.ingredient_id = bar_id"
        )
        if params.can_make == "all":
            where_clauses.append(
                f"NOT EXISTS ("
                f"  SELECT 1 FROM cocktails_ingredients ci_bar"
                f"  JOIN ingredients i_bar ON ci_bar.ingredient_id = i_bar.ingredient_id"
                f"  WHERE ci_bar.cocktail_id = c.cocktail_id {garnish_clause}"
                f"  AND COALESCE(i_bar.mapped_ingredient, i_bar.ingredient) NOT IN ({bar_mapped})"
                f")"
            )
        elif params.can_make == "some":
            garnish_clause_miss = "" if params.include_garnish else "AND ci_miss.unit != 'garnish'"
            where_clauses.append(
                f"EXISTS ("
                f"  SELECT 1 FROM cocktails_ingredients ci_have"
                f"  JOIN ingredients i_have ON ci_have.ingredient_id = i_have.ingredient_id"
                f"  WHERE ci_have.cocktail_id = c.cocktail_id"
                f"  AND COALESCE(i_have.mapped_ingredient, i_have.ingredient) IN ({bar_mapped})"
                f")"
                f" AND EXISTS ("
                f"  SELECT 1 FROM cocktails_ingredients ci_miss"
                f"  JOIN ingredients i_miss ON ci_miss.ingredient_id = i_miss.ingredient_id"
                f"  WHERE ci_miss.cocktail_id = c.cocktail_id {garnish_clause_miss}"
                f"  AND COALESCE(i_miss.mapped_ingredient, i_miss.ingredient) NOT IN ({bar_mapped})"
                f")"
            )
        elif params.can_make == "none":
            where_clauses.append(
                f"NOT EXISTS ("
                f"  SELECT 1 FROM cocktails_ingredients ci_none"
                f"  JOIN ingredients i_none ON ci_none.ingredient_id = i_none.ingredient_id"
                f"  WHERE ci_none.cocktail_id = c.cocktail_id"
                f"  AND COALESCE(i_none.mapped_ingredient, i_none.ingredient) IN ({bar_mapped})"
                f")"
            )

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # User join subqueries — only emit when a user is present
    user_joins = ""
    if user_id:
        user_joins = """
            LEFT JOIN user_favorites uf
                ON c.cocktail_id = uf.cocktail_id AND uf.user_id = :user_id
            LEFT JOIN user_bookmarks ub
                ON c.cocktail_id = ub.cocktail_id AND ub.user_id = :user_id
            LEFT JOIN user_ratings ur
                ON c.cocktail_id = ur.cocktail_id AND ur.user_id = :user_id
        """

    select_user_cols = ""
    if user_id:
        select_user_cols = """
            COALESCE(uf.favorite, false)   AS favorited,
            COALESCE(ub.bookmark, false)   AS bookmarked,
            ur.rating                      AS user_rating,
        """

    base_sql = f"""
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

    # Fetch ingredients for the returned cocktails in one query
    # in_bar matched at mapped_ingredient level
    ing_sql = """
        SELECT
            ci.cocktail_id,
            i.ingredient_id,
            i.ingredient,
            i.mapped_ingredient,
            ci.unit,
            ci.quantity,
            CASE
                WHEN CAST(:user_id AS bigint) IS NOT NULL
                     AND COALESCE(i.mapped_ingredient, i.ingredient) IN (
                         SELECT DISTINCT COALESCE(ib.mapped_ingredient, ib.ingredient)
                         FROM ingredients ib
                         CROSS JOIN LATERAL unnest((
                             SELECT ingredient_list FROM user_bar
                             WHERE user_id = CAST(:user_id AS bigint)
                         )) AS bar_id
                         WHERE ib.ingredient_id = bar_id
                     )
                THEN true ELSE false
            END AS in_bar
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

    # Group ingredients by cocktail_id
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


async def get_ingredient_options(db: AsyncSession) -> dict:
    """Return all distinct filter option values for dropdowns."""
    # unit lives on cocktails_ingredients, not ingredients — join to get it
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

    # Liquor types come from ingredients.alcohol_type (populated from ingredient_map.csv)
    lt_rows = (
        await db.execute(
            text("SELECT DISTINCT alcohol_type FROM ingredients WHERE alcohol_type IS NOT NULL ORDER BY alcohol_type")
        )
    ).scalars().all()
    liquor_types = list(lt_rows)

    return {
        "liquor_types": liquor_types,
        "ingredients": sorted(all_ingredients - garnishes - bitters - syrups),
        "garnishes": sorted(garnishes),
        "bitters": sorted(bitters),
        "syrups": sorted(syrups),
    }
