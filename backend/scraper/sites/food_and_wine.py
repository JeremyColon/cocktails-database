"""
Food & Wine scraper adapter.

Discovery: sitemap-based (category pages are JS-rendered and return no links)
Parsing:   schema.org JSON-LD (preferred) with BeautifulSoup fallback
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

# Both sitemaps are scanned; URLs are filtered to likely recipe pages.
_SITEMAP_URLS = [
    "https://www.foodandwine.com/sitemap_1.xml",
    "https://www.foodandwine.com/sitemap_2.xml",
]

# Map URL keywords → alcohol_type values used in the DB
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


def _is_recipe_url(url: str) -> bool:
    """Return True for URLs that are likely individual cocktail recipes."""
    u = url.lower()
    if "cocktail" not in u:
        return False
    # New F&W format: ...-recipe-XXXXXXX
    # Old format: /recipes/...-cocktail  or  /cocktails/...
    return "-recipe-" in u or "/recipes/" in u or "/cocktails/" in u


def _is_recipe_type(type_val) -> bool:
    """Handle @type as either a string or a list."""
    if isinstance(type_val, list):
        return "Recipe" in type_val
    return type_val == "Recipe"


class FoodAndWineScraper(BaseScraper):
    source = "food_and_wine"

    async def get_recipe_links(self) -> list[str]:
        links: list[str] = []
        async with get_session() as session:
            for sitemap_url in _SITEMAP_URLS:
                try:
                    resp = await session.get(sitemap_url)
                    urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
                    recipe_urls = [u for u in urls if _is_recipe_url(u)]
                    links.extend(recipe_urls)
                    logger.info(
                        f"[food_and_wine] {sitemap_url}: {len(recipe_urls)} recipe URLs found"
                    )
                except Exception as e:
                    logger.error(f"[food_and_wine] Failed to fetch {sitemap_url}: {e}")
        return list(dict.fromkeys(links))

    async def parse_recipe(self, url: str) -> RawRecipe | None:
        async with get_session() as session:
            try:
                resp = await session.get(url)
            except Exception as e:
                logger.warning(f"[food_and_wine] Failed to fetch {url}: {e}")
                return None

        soup = BeautifulSoup(resp.text, "html.parser")

        recipe = _parse_json_ld(soup)
        if recipe:
            recipe.link = url
            recipe.source = self.source
            recipe.alcohol_type = recipe.alcohol_type or _infer_type_from_url(url)
            return recipe

        return _parse_html(soup, url, self.source)


def _parse_json_ld(soup: BeautifulSoup) -> RawRecipe | None:
    """Extract recipe data from schema.org Recipe JSON-LD block."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, AttributeError):
            continue

        # JSON-LD can be a single object or a list of objects
        if isinstance(data, list):
            data = next((d for d in data if isinstance(d, dict) and _is_recipe_type(d.get("@type"))), None)
        if not isinstance(data, dict) or not _is_recipe_type(data.get("@type")):
            continue

        name = (data.get("name") or data.get("headline") or "").strip()
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

        if not ingredients:
            continue

        return RawRecipe(
            name=name,
            link="",   # caller fills this in
            source="", # caller fills this in
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
