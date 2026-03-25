"""
Ingredient normalization — extracted from the cocktails.ipynb notebook logic.

Transforms raw scraped ingredient names into canonical mapped_ingredient values
by cleaning the text and looking up against ingredient_map.csv (or the DB table).
"""
import csv
import logging
import re
from functools import lru_cache
from pathlib import Path

from unidecode import unidecode

from backend.scraper.base import RawIngredient, RawRecipe

logger = logging.getLogger(__name__)

# Path to the ingredient map CSV (relative to repo root)
_INGREDIENT_MAP_PATH = Path(__file__).parents[3] / "data" / "ingredient_map.csv"

# Regex patterns for ingredient classification
_BITTERS_RE = re.compile(r"bitters?", re.IGNORECASE)
_SYRUP_RE = re.compile(r"syrup", re.IGNORECASE)


@lru_cache(maxsize=1)
def _load_ingredient_map() -> dict[str, dict]:
    """
    Load ingredient_map.csv into memory.
    Returns dict keyed by normalized raw ingredient name → {ingredient_map, alcohol_type}.
    Cached after first load.
    """
    mapping: dict[str, dict] = {}
    if not _INGREDIENT_MAP_PATH.exists():
        logger.warning(f"ingredient_map.csv not found at {_INGREDIENT_MAP_PATH}")
        return mapping

    with open(_INGREDIENT_MAP_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = _clean_name(row["ingredient"])
            mapping[key] = {
                "ingredient_id": int(row["ingredient_id"]) if row.get("ingredient_id") else None,
                "mapped_ingredient": row.get("ingredient_map") or row.get("ingredient"),
                "alcohol_type": row.get("alcohol_type") or None,
            }
    return mapping


def _clean_name(name: str) -> str:
    """Normalize a raw ingredient string to a lookup key."""
    name = name.lower()
    name = re.sub(r"[,*''\u2018\u2019]", "", name)  # remove commas, asterisks, curly quotes
    name = unidecode(name)   # convert accented chars → ASCII
    name = name.strip()
    return name


def normalize_ingredient(raw: RawIngredient) -> dict:
    """
    Return a normalized ingredient dict with:
    - ingredient: cleaned raw name
    - mapped_ingredient: canonical name from ingredient_map
    - alcohol_type: spirit category or None
    - unit: 'garnish' | 'bitters' | 'syrup' | original unit
    - quantity: float or None
    - ingredient_id: int or None (if found in map)
    """
    cleaned = _clean_name(raw.name)
    mapping = _load_ingredient_map()

    lookup = mapping.get(cleaned, {})

    # Determine unit / ingredient type
    unit = raw.unit or ""
    if unit.lower() == "garnish" or cleaned.startswith("garnish"):
        unit = "garnish"
    elif _BITTERS_RE.search(cleaned):
        unit = unit or "dash"
    elif _SYRUP_RE.search(cleaned):
        unit = unit or "oz"

    return {
        "ingredient": cleaned,
        "mapped_ingredient": lookup.get("mapped_ingredient", cleaned),
        "alcohol_type": lookup.get("alcohol_type"),
        "unit": unit or None,
        "quantity": raw.quantity,
        "ingredient_id": lookup.get("ingredient_id"),
    }


def normalize_recipe(raw: RawRecipe) -> dict:
    """
    Return a normalized recipe dict ready for DB insertion.
    """
    return {
        "recipe_name": raw.name.strip(),
        "link": raw.link,
        "image": raw.image,
        "alcohol_type": raw.alcohol_type,
        "source": raw.source,
        "ingredients": [normalize_ingredient(i) for i in raw.ingredients],
    }
