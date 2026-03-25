"""
Base types and abstract interface for all site scrapers.

To add a new site:
1. Create backend/scraper/sites/my_site.py
2. Subclass BaseScraper, set source, implement get_recipe_links + parse_recipe
3. Add an instance to SCRAPERS in pipeline.py
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawIngredient:
    name: str
    quantity: float | None = None
    unit: str | None = None  # e.g. "oz", "dash", "garnish"


@dataclass
class RawRecipe:
    name: str
    link: str
    source: str                              # site identifier, e.g. "liquor.com"
    image: str | None = None
    alcohol_type: str | None = None          # e.g. "bourbon", "rum"
    ingredients: list[RawIngredient] = field(default_factory=list)


class BaseScraper(ABC):
    """
    Abstract base for all site scrapers. Each implementation handles one site
    and is responsible only for fetching + parsing. Normalization, deduplication,
    and persistence are handled by the pipeline.
    """

    source: str  # unique identifier, e.g. "liquor.com"

    @abstractmethod
    async def get_recipe_links(self) -> list[str]:
        """
        Discover and return all recipe page URLs to scrape for this site.
        May involve paginating category/index pages.
        """
        ...

    @abstractmethod
    async def parse_recipe(self, url: str) -> RawRecipe | None:
        """
        Fetch and parse a single recipe page.
        Return None to skip (e.g. parse error, non-recipe page, paywall).
        """
        ...
