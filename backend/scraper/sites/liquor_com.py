"""
liquor.com scraper adapter.

Discovery: category index pages → paginate → collect recipe hrefs
Parsing:   individual recipe pages → name, image, ingredients (name, qty, unit)
"""
import json
import logging
import re

from bs4 import BeautifulSoup

from backend.scraper.base import BaseScraper, RawIngredient, RawRecipe
from backend.scraper.session import ScraperSession, get_session

logger = logging.getLogger(__name__)

# Liquor type → category index URL (from original notebooks)
CATEGORIES: dict[str, str] = {
    "bourbon":        "https://www.liquor.com/bourbon-cocktails-4779435",
    "vodka":          "https://www.liquor.com/vodka-cocktails-4779437",
    "rum":            "https://www.liquor.com/rum-cocktails-4779434",
    "scotch":         "https://www.liquor.com/scotch-cocktails-4779431",
    "rye whiskey":    "https://www.liquor.com/rye-whiskey-cocktails-4779433",
    "other whiskey":  "https://www.liquor.com/whiskey-cocktails-4779430",
    "tequila/mezcal": "https://www.liquor.com/tequila-and-mezcal-cocktails-4779429",
    "cognac/brandy":  "https://www.liquor.com/brandy-cocktails-4779428",
    "gin":            "https://www.liquor.com/gin-cocktails-4779436",
    "other":          "https://www.liquor.com/other-cocktails-4779427",
}

_BASE_URL = "https://www.liquor.com"
_QTY_RE = re.compile(r"^([\d\s/½¼¾⅓⅔⅛]+)\s*(.*)")


class LiquorComScraper(BaseScraper):
    source = "liquor.com"

    async def get_recipe_links(self) -> list[str]:
        links: list[str] = []
        async with get_session() as session:
            for liquor_type, category_url in CATEGORIES.items():
                try:
                    category_links = await self._scrape_category(
                        session, category_url, liquor_type
                    )
                    links.extend(category_links)
                    logger.info(
                        f"[liquor.com] {liquor_type}: {len(category_links)} recipes found"
                    )
                except Exception as e:
                    logger.error(f"[liquor.com] Failed to scrape category {liquor_type}: {e}")
        return list(dict.fromkeys(links))  # deduplicate while preserving order

    async def _scrape_category(
        self, session: ScraperSession, url: str, liquor_type: str
    ) -> list[str]:
        """Scrape all recipe links from a category page, following pagination."""
        links: list[str] = []
        current_url = url

        while current_url:
            resp = await session.get(current_url)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Recipe cards — liquor.com uses <a> tags with /recipe/ in href
            for a in soup.select("a[href*='/recipe/'], a[href*='-recipe-']"):
                href = a.get("href", "")
                if href.startswith("/"):
                    href = _BASE_URL + href
                if href and href not in links:
                    links.append(href)

            # Pagination — look for "Next" link
            next_link = soup.select_one("a[aria-label='Next Page'], a.pagination__next")
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
                logger.warning(f"[liquor.com] Failed to fetch {url}: {e}")
                return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Recipe name
        name_el = soup.select_one("h1.recipe__title, h1.heading__title, h1")
        if not name_el:
            return None
        name = name_el.get_text(strip=True)

        # Hero image — try JSON-LD first (most reliable), then lazy-load attrs, then src
        image = None
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Recipe", "recipe"):
                        raw_img = item.get("image")
                        if isinstance(raw_img, list):
                            raw_img = raw_img[0]
                        if isinstance(raw_img, dict):
                            raw_img = raw_img.get("url")
                        if raw_img:
                            image = raw_img
                            break
            except (json.JSONDecodeError, AttributeError):
                pass
            if image:
                break
        if not image:
            img_el = soup.select_one(
                "img.recipe__image, img.img-fluid, "
                "div.recipe__image img, picture img"
            )
            if img_el:
                image = img_el.get("data-src") or img_el.get("src")

        # Infer alcohol_type from URL path (used as fallback)
        alcohol_type = _infer_alcohol_type_from_url(url)

        # Ingredients
        ingredients: list[RawIngredient] = []
        for li in soup.select(
            "li.ingredient, "
            "ul.recipe__ingredients li, "
            "div.recipe-ingredients li, "
            ".structured-ingredients__list-item"
        ):
            text = li.get_text(strip=True)
            if not text:
                continue
            qty, unit, ingredient_name = _parse_ingredient_text(text)
            ingredients.append(RawIngredient(name=ingredient_name, quantity=qty, unit=unit))

        if not ingredients:
            logger.debug(f"[liquor.com] No ingredients found for {url}, skipping")
            return None

        return RawRecipe(
            name=name,
            link=url,
            source=self.source,
            image=image,
            alcohol_type=alcohol_type,
            ingredients=ingredients,
        )


def _parse_ingredient_text(text: str) -> tuple[float | None, str | None, str]:
    """
    Parse a raw ingredient line like '2 oz vodka' or 'Garnish: lemon twist'
    into (quantity, unit, name).
    """
    text = text.strip()

    # Handle garnish prefix
    if text.lower().startswith("garnish:") or text.lower().startswith("garnish -"):
        name = re.sub(r"^garnish\s*[:\-]\s*", "", text, flags=re.IGNORECASE).strip()
        return None, "garnish", name

    # Try to extract leading number + unit
    # e.g. "2 oz vodka", "1/2 oz lemon juice", "3 dashes bitters"
    parts = text.split(None, 2)  # split on whitespace, max 3 parts
    if len(parts) >= 2:
        qty = _parse_quantity(parts[0])
        if qty is not None:
            if len(parts) == 3:
                unit, name = parts[1], parts[2]
            else:
                unit, name = None, parts[1]
            return qty, unit, name

    return None, None, text


def _parse_quantity(s: str) -> float | None:
    """Convert fraction/unicode fraction strings to float."""
    _FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125}
    s = s.strip()
    for uc, val in _FRACTIONS.items():
        s = s.replace(uc, str(val))
    try:
        if "/" in s:
            num, den = s.split("/", 1)
            return float(num) / float(den)
        return float(s)
    except (ValueError, ZeroDivisionError):
        return None


def _infer_alcohol_type_from_url(url: str) -> str | None:
    url_lower = url.lower()
    for keyword, label in [
        ("bourbon", "bourbon"),
        ("vodka", "vodka"),
        ("rum", "rum"),
        ("scotch", "scotch"),
        ("rye", "rye whiskey"),
        ("whiskey", "other whiskey"),
        ("tequila", "tequila/mezcal"),
        ("mezcal", "tequila/mezcal"),
        ("brandy", "cognac/brandy"),
        ("cognac", "cognac/brandy"),
        ("gin", "gin"),
    ]:
        if keyword in url_lower:
            return label
    return None
