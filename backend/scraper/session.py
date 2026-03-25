"""
Shared async HTTP session with politeness controls applied to all scrapers.
All adapters use get_session() rather than creating their own httpx clients.
"""
import asyncio
import logging
import random
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_DELAY_MIN = 1.0   # seconds between requests
_DELAY_MAX = 3.0

# Cache robots.txt per domain so we only fetch it once per run
_robots_cache: dict[str, RobotFileParser] = {}

_client: httpx.AsyncClient | None = None


def get_session() -> "ScraperSession":
    return ScraperSession()


class ScraperSession:
    """
    Thin wrapper around httpx.AsyncClient that adds:
    - Consistent User-Agent
    - Random delay between requests
    - Retry with exponential backoff on transient errors
    - robots.txt compliance check
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
            timeout=20.0,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self._client.aclose()

    async def get(self, url: str) -> httpx.Response:
        if not await self._robots_allowed(url):
            raise PermissionError(f"robots.txt disallows: {url}")

        await self._polite_delay()

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.get(url)
                if response.status_code in _RETRY_STATUSES:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"HTTP {response.status_code} for {url}, "
                        f"retrying in {wait:.1f}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return response
            except httpx.TransportError as e:
                if attempt == _MAX_RETRIES - 1:
                    raise
                wait = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Transport error for {url}: {e}, retry in {wait:.1f}s")
                await asyncio.sleep(wait)

        raise RuntimeError(f"Failed to fetch {url} after {_MAX_RETRIES} attempts")

    async def _polite_delay(self) -> None:
        await asyncio.sleep(random.uniform(_DELAY_MIN, _DELAY_MAX))

    async def _robots_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in _robots_cache:
            robots_url = f"{domain}/robots.txt"
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                async with httpx.AsyncClient(timeout=5.0) as c:
                    resp = await c.get(robots_url)
                    rp.parse(resp.text.splitlines())
            except Exception:
                # If robots.txt is unreachable, allow (fail open)
                _robots_cache[domain] = None
                return True
            _robots_cache[domain] = rp

        rp = _robots_cache.get(domain)
        if rp is None:
            return True
        return rp.can_fetch(_USER_AGENT, url)
