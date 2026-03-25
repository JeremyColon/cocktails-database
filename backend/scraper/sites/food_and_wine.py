"""
Food & Wine scraper adapter.

Discovery: cocktail tag/category pages → collect recipe hrefs
Parsing:   individual recipe pages using schema.org JSON-LD (most reliable)
           with BeautifulSoup fallback
"""
import json
import logging
import re

from bs4 import BeautifulSoup

from backend.scraper.base import BaseScraper, RawIngredient, RawRecipe
from backend.scraper.session import get_session
from backend.scraper.sites.liquor_com import _parse_ingredient_text

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.foodandwine.com"

# Category pages that list cocktail recipes
CATEGORY_URLS: list[str] = [
    "https://www.foodandwine.com/cocktails-spirits/cocktails",
    "https://www.foodandwine.com/cocktails-spirits/whiskey",
    "https://www.foodandwine.com/cocktails-spirits/vodka",
    "https://www.foodandwine.com/cocktails-spirits/tequila",
    "https://www.foodandwine.com/cocktails-spirits/rum",
    "https://www.foodandwine.com/cocktails-spirits/gin",
]

# Map F&W URL keywords → alcohol_type values used in the DB
_TYPE_MAP = {
    "whiskey": "other whiskey",
    "bourbon": "bourbon",
    "vodka": "vodka",
    "tequila": "tequila/mezcal",
    "mezcal": "tequila/mezcal",
    "rum": "rum",
    "gin": "gin",
    "scotch": "scotch",
    "brandy": "cognac/brandy",
    "cognac": "cognac/brandy",
}


class FoodAndWineScraper(BaseScraper):
    source = "food_and_wine"

    async def get_recipe_links(self) -> list[str]:
        links: list[str] = []
        async with get_session() as session:
            for cat_url in CATEGORY_URLS:
                try:
                    page_links = await self._scrape_category(session, cat_url)
                    links.extend(page_links)
                    logger.info(
                        f"[food_and_wine] {cat_url}: {len(page_links)} recipes found"
                    )
                except Exception as e:
                    logger.error(f"[food_and_wine] Failed to scrape {cat_url}: {e}")
        return list(dict.fromkeys(links))

    async def _scrape_category(self, session, url: str) -> list[str]:
        links: list[str] = []
        current_url = url

        while current_url:
            resp = await session.get(current_url)
            soup = BeautifulSoup(resp.text, "html.parser")

            # F&W recipe cards typically use article/card elements with recipe links
            for a in soup.select(
                "a[href*='/recipe/'], "
                "a[href*='/cocktails/'], "
                ".card__title a, "
                "h3.card__title a"
            ):
                href = a.get("href", "")
                if href.startswith("/"):
                    href = _BASE_URL + href
                if href and _BASE_URL in href and href not in links:
                    links.append(href)

            # F&W uses a "Load More" button / page query param for pagination
            next_link = soup.select_one(
                "a[rel='next'], a.pagination__next, [data-page]"
            )
            if next_link and next_link.get("href"):
                next_href = next_link["href"]
                current_url = (
                    _BASE_URL + next_href if next_href.startswith("/") else next_href
                )
            else:
                current_url = None

        return links

    async def parse_recipe(self, url: str) -> RawRecipe | None:
        async with get_session() as session:
            try:
                resp = await session.get(url)
            except Exception as e:
                logger.warning(f"[food_and_wine] Failed to fetch {url}: {e}")
                return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Prefer schema.org JSON-LD — most reliable across site redesigns
        recipe = _parse_json_ld(soup)
        if recipe:
            recipe.link = url
            recipe.source = self.source
            recipe.alcohol_type = recipe.alcohol_type or _infer_type_from_url(url)
            return recipe

        # Fallback: parse HTML directly
        return _parse_html(soup, url, self.source)


def _parse_json_ld(soup: BeautifulSoup) -> RawRecipe | None:
    """Extract recipe data from schema.org Recipe JSON-LD block."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, AttributeError):
            continue

        # JSON-LD can be an array or a single object
        if isinstance(data, list):
            data = next((d for d in data if d.get("@type") == "Recipe"), None)
        if not isinstance(data, dict) or data.get("@type") != "Recipe":
            continue

        name = data.get("name", "").strip()
        if not name:
            continue

        image_raw = data.get("image")
        if isinstance(image_raw, list):
            image = image_raw[0] if image_raw else None
        elif isinstance(image_raw, dict):
            image = image_raw.get("url")
        else:
            image = image_raw

        ingredients: list[RawIngredient] = []
        for raw in data.get("recipeIngredient", []):
            qty, unit, ing_name = _parse_ingredient_text(raw)
            ingredients.append(RawIngredient(name=ing_name, quantity=qty, unit=unit))

        return RawRecipe(
            name=name,
            link="",      # caller fills this in
            source="",    # caller fills this in
            image=image,
            ingredients=ingredients,
        )

    return None


def _parse_html(soup: BeautifulSoup, url: str, source: str) -> RawRecipe | None:
    """Fallback HTML parser for when JSON-LD is not present."""
    name_el = soup.select_one("h1.recipe-title, h1.article-heading, h1")
    if not name_el:
        return None
    name = name_el.get_text(strip=True)

    img_el = soup.select_one("img.recipe__photo, .recipe-photo img, picture img")
    image = img_el.get("src") if img_el else None

    ingredients: list[RawIngredient] = []
    for li in soup.select(
        "ul.ingredients-section li, "
        ".recipe-ingredients li, "
        "li.ingredient"
    ):
        text = li.get_text(strip=True)
        if text:
            qty, unit, ing_name = _parse_ingredient_text(text)
            ingredients.append(RawIngredient(name=ing_name, quantity=qty, unit=unit))

    if not ingredients:
        logger.debug(f"[food_and_wine] No ingredients found for {url}, skipping")
        return None

    return RawRecipe(
        name=name,
        link=url,
        source=source,
        image=image,
        alcohol_type=_infer_type_from_url(url),
        ingredients=ingredients,
    )


def _infer_type_from_url(url: str) -> str | None:
    url_lower = url.lower()
    for keyword, label in _TYPE_MAP.items():
        if keyword in url_lower:
            return label
    return None
