"""
Scraper pipeline — orchestrates: discover → parse → normalize → deduplicate → persist.

To add a new site, import its adapter and add an instance to SCRAPERS.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.scraper.base import BaseScraper
from backend.scraper.normalizer import normalize_recipe
from backend.scraper.sites.food_and_wine import FoodAndWineScraper
from backend.scraper.sites.liquor_com import LiquorComScraper

logger = logging.getLogger(__name__)

# ── Registry ──────────────────────────────────────────────────────────────────
# Add a new BaseScraper instance here to include it in the weekly run.
SCRAPERS: list[BaseScraper] = [
    LiquorComScraper(),
    FoodAndWineScraper(),
]


# ── Entry point ───────────────────────────────────────────────────────────────

async def run_pipeline() -> None:
    """Run all scrapers and persist results. Called by the scheduler."""
    logger.info("Scrape pipeline started")
    async with AsyncSessionLocal() as db:
        for scraper in SCRAPERS:
            await _run_scraper(scraper, db)
    logger.info("Scrape pipeline complete")


async def _run_scraper(scraper: BaseScraper, db: AsyncSession) -> None:
    logger.info(f"[{scraper.source}] Discovering recipe links...")
    try:
        urls = await scraper.get_recipe_links()
    except Exception as e:
        logger.error(f"[{scraper.source}] Link discovery failed: {e}")
        return

    logger.info(f"[{scraper.source}] Found {len(urls)} recipe URLs")
    saved = skipped = errors = 0

    for url in urls:
        try:
            raw = await scraper.parse_recipe(url)
            if raw is None:
                skipped += 1
                continue

            normalized = normalize_recipe(raw)
            was_new = await _upsert_recipe(normalized, db)
            if was_new:
                saved += 1
            else:
                skipped += 1
        except Exception as e:
            logger.warning(f"[{scraper.source}] Error processing {url}: {e}")
            errors += 1

    logger.info(
        f"[{scraper.source}] Done — saved: {saved}, skipped: {skipped}, errors: {errors}"
    )


async def _upsert_recipe(normalized: dict, db: AsyncSession) -> bool:
    """
    Insert or update a cocktail and its ingredients.
    Returns True if this was a new recipe, False if it was an update.
    """
    now = datetime.now(timezone.utc)

    # Upsert cocktail — conflict on (lower(recipe_name), source)
    # date_added is intentionally excluded from the UPDATE so it is set once and never changed.
    cocktail_sql = """
        INSERT INTO cocktails (recipe_name, image, link, alcohol_type, source, scraped_at, date_added)
        VALUES (:recipe_name, :image, :link, :alcohol_type, :source, :scraped_at, :scraped_at)
        ON CONFLICT (lower(recipe_name), source)
        DO UPDATE SET
            image      = COALESCE(EXCLUDED.image, cocktails.image),
            link       = EXCLUDED.link,
            scraped_at = EXCLUDED.scraped_at
        RETURNING cocktail_id, (xmax = 0) AS is_new
    """
    row = (
        await db.execute(
            text(cocktail_sql),
            {
                "recipe_name": normalized["recipe_name"],
                "image": normalized["image"],
                "link": normalized["link"],
                "alcohol_type": normalized["alcohol_type"],
                "source": normalized["source"],
                "scraped_at": now,
            },
        )
    ).mappings().one()

    cocktail_id = row["cocktail_id"]
    is_new = row["is_new"]

    # If updating an existing recipe, clear old ingredient links first
    if not is_new:
        await db.execute(
            text("DELETE FROM cocktails_ingredients WHERE cocktail_id = :cid"),
            {"cid": cocktail_id},
        )

    # Upsert each ingredient and link to cocktail
    for ing in normalized["ingredients"]:
        ingredient_id = await _get_or_create_ingredient(ing, db)
        await db.execute(
            text("""
                INSERT INTO cocktails_ingredients (cocktail_id, ingredient_id, unit, quantity)
                VALUES (:cocktail_id, :ingredient_id, :unit, :quantity)
                ON CONFLICT (cocktail_id, ingredient_id) DO NOTHING
            """),
            {
                "cocktail_id": cocktail_id,
                "ingredient_id": ingredient_id,
                "unit": ing.get("unit"),
                "quantity": str(ing["quantity"]) if ing.get("quantity") is not None else None,
            },
        )

    await db.commit()
    return is_new


async def _get_or_create_ingredient(ing: dict, db: AsyncSession) -> int:
    """Return the ingredient_id, creating a new row if needed."""
    # If the normalizer found a known ingredient_id, use it directly
    if ing.get("ingredient_id"):
        return ing["ingredient_id"]

    # Check if ingredient already exists by name
    existing = (
        await db.execute(
            text("SELECT ingredient_id FROM ingredients WHERE ingredient = :ingredient"),
            {"ingredient": ing["ingredient"]},
        )
    ).mappings().one_or_none()

    if existing:
        return existing["ingredient_id"]

    row = (
        await db.execute(
            text("""
                INSERT INTO ingredients (ingredient, mapped_ingredient, alcohol_type)
                VALUES (:ingredient, :mapped_ingredient, :alcohol_type)
                RETURNING ingredient_id
            """),
            {
                "ingredient": ing["ingredient"],
                "mapped_ingredient": ing.get("mapped_ingredient"),
                "alcohol_type": ing.get("alcohol_type"),
            },
        )
    ).mappings().one()

    return row["ingredient_id"]
