# Cocktails Database — Refactor Plan

## Current State & Problems

The existing app has several architectural issues that prevent it from scaling:

### Performance Bottlenecks
- **Full DB load at startup**: The entire cocktails table is loaded into a pandas DataFrame in memory when the app starts. Every user shares this same in-memory state, and any filtering is done in Python — not in the database where indexes can help.
- **All filtering in Python**: `apply_AND_filters` / `apply_OR_filters` in `helpers.py` do multi-pass DataFrame scans for every filter change. A 500-cocktail dataset is manageable; a 5,000-cocktail dataset is not.
- **Massive DOM on render**: Every filter update regenerates all card components including 100+ individual modals in a single Dash callback response. This blocks the UI and sends a large payload to the browser.
- **N+1 query pattern**: The main `update_table` callback issues 4+ separate queries (ratings, favorites, bookmarks, ratings again) that could be a single JOIN.

### Architectural Issues
- **Dash callback overhead**: Every interaction (favorite, bookmark, rating) triggers a full round-trip to the Python process. Dash's architecture serializes all component state as JSON on every callback, which grows proportionally with the number of rendered cards.
- **SQL injection**: All queries use f-string interpolation (`f"WHERE user_id={user_id}"`). No parameterized queries exist outside of SQLAlchemy's User model.
- **Monolithic callbacks**: `update_table` in `main.py` (the primary callback) handles filtering, user preference merging, card generation, and title updates all in one function. It runs on every "Apply Filters" click.
- **No pagination**: Results are not paginated; 300 cards can be returned in one shot.
- **No caching layer**: Frequently-read data (cocktail list, ingredient list) is re-queried on every page load.

---

## Recommended Stack

### Backend: FastAPI
- Async request handling — multiple users don't block each other
- Native Pydantic models for validation (eliminates SQL injection via parameterized queries by default with SQLAlchemy 2.0)
- Auto-generated OpenAPI docs at `/docs`
- Easy to add background tasks, caching middleware, and rate limiting
- Replaces: Dash server + Flask-Login + raw psycopg2

### Frontend: React + Vite
- Component-based UI naturally maps to the existing card/modal/filter pattern
- React Query handles server state (favorites, bookmarks, ratings) with optimistic updates — no more round-trip wait on star clicks
- Filtering becomes a client-side URL state problem (query params) with server-side execution
- Vite gives fast HMR in development and small production bundles
- Replaces: Dash layout + callbacks + dcc.Store + dcc.Location

### Database: PostgreSQL (same) + SQLAlchemy 2.0 async
- Move all filtering into SQL (`WHERE`, `JOIN`, `ILIKE`) — uses indexes, scales
- SQLAlchemy 2.0 async ORM with proper models for all tables (currently only `users` has an ORM model)
- Alembic for migrations (already in requirements)
- Add a Redis layer for caching the cocktail list and ingredient dropdown data

### Auth: FastAPI + JWT (replacing Flask-Login)
- Stateless JWT tokens stored in `httpOnly` cookies
- Eliminates the Dash `dcc.Store` user-store pattern
- `python-jose` + `passlib[bcrypt]` (same bcrypt hashing, no password migration needed)

---

## Architecture Overview

```
┌──────────────────────────────────┐
│         React Frontend (Vite)    │
│                                  │
│  /          → CocktailBrowser    │
│  /mybar     → MyBar              │
│  /login     → AuthForms          │
│                                  │
│  React Query ←→ API calls        │
└──────────────┬───────────────────┘
               │ HTTPS (JSON)
┌──────────────▼───────────────────┐
│       FastAPI Backend            │
│                                  │
│  /api/cocktails    (GET, filter) │
│  /api/cocktails/{id}/favorite    │
│  /api/cocktails/{id}/bookmark    │
│  /api/cocktails/{id}/rating      │
│  /api/bar          (GET/PUT)     │
│  /api/auth/login                 │
│  /api/auth/register              │
│  /api/auth/logout                │
│                                  │
│  SQLAlchemy 2.0 async ORM        │
│  Redis cache (cocktail/ingredient│
│  lists, TTL 1hr)                 │
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│          PostgreSQL              │
│  (same schema, minor additions)  │
└──────────────────────────────────┘
```

---

## Migration Phases

### Phase 1 — Backend API (no frontend changes yet)

Build the FastAPI layer as a standalone service alongside the existing Dash app. This lets you validate the API without touching the UI.

**Tasks:**
1. Create `backend/` directory with FastAPI app structure:
   ```
   backend/
   ├── main.py            # FastAPI app entry
   ├── database.py        # Async SQLAlchemy engine + session
   ├── models.py          # ORM models for ALL tables (not just users)
   ├── schemas.py         # Pydantic request/response schemas
   ├── routers/
   │   ├── auth.py        # /api/auth/*
   │   ├── cocktails.py   # /api/cocktails/*
   │   └── bar.py         # /api/bar/*
   ├── services/
   │   ├── cocktail_service.py   # Filtering logic (moved from helpers.py)
   │   └── bar_service.py        # Bar calculations (moved from helpers.py)
   └── cache.py           # Redis integration
   ```

2. Implement `/api/cocktails` with server-side filtering:
   - Replace all pandas `apply_AND_filters` / `apply_OR_filters` with a single parameterized SQL query using dynamic `WHERE` clauses
   - Add `limit` + `offset` pagination (page size: 24 cards)
   - Move NPS range filter, ingredient availability filter, favorites/bookmarks filter into SQL `JOIN`s and `WHERE` clauses
   - Add `search` param using `ILIKE`

3. Move `user_favorites`, `user_bookmarks`, `user_ratings` operations to dedicated endpoints with UPSERT logic (already exists in helpers.py — just wrap it with parameterized queries).

4. Implement JWT auth replacing Flask-Login. Existing bcrypt hashes are compatible — no user table migration needed.

5. Add Redis caching for:
   - Full ingredient list (used to populate dropdowns) — TTL 1 hour
   - Cocktail base data (names, links, images) — TTL 1 hour
   - Per-user bar data — invalidate on update

**Key SQL refactor — replace pandas filtering with:**
```sql
SELECT
    c.cocktail_id,
    c.recipe_name,
    c.image,
    c.link,
    c.alcohol_type,
    COALESCE(vr.cocktail_nps, 0) AS nps,
    COALESCE(vr.avg_rating, 0) AS avg_rating,
    COALESCE(vr.num_ratings, 0) AS num_ratings,
    COALESCE(uf.favorite, false) AS favorited,
    COALESCE(ub.bookmark, false) AS bookmarked,
    COALESCE(ur.rating, NULL) AS user_rating
FROM cocktails c
LEFT JOIN vw_cocktail_ratings vr ON c.cocktail_id = vr.cocktail_id
LEFT JOIN user_favorites uf ON c.cocktail_id = uf.cocktail_id AND uf.user_id = :user_id
LEFT JOIN user_bookmarks ub ON c.cocktail_id = ub.cocktail_id AND ub.user_id = :user_id
LEFT JOIN user_ratings ur ON c.cocktail_id = ur.cocktail_id AND ur.user_id = :user_id
WHERE
    (:liquor_types IS NULL OR c.alcohol_type = ANY(:liquor_types))
    AND (:nps_min IS NULL OR COALESCE(vr.cocktail_nps, 0) >= :nps_min)
    AND (:nps_max IS NULL OR COALESCE(vr.cocktail_nps, 0) <= :nps_max)
    -- ingredient filters handled via EXISTS subqueries
ORDER BY c.recipe_name
LIMIT :limit OFFSET :offset;
```

---

### Phase 2 — React Frontend

Replace the Dash layout with a React SPA. The existing component structure maps cleanly:

| Current (Dash) | New (React) |
|---|---|
| `pages/main.py` layout | `src/pages/CocktailBrowser.tsx` |
| `utils/filter_canvas.py` | `src/components/FilterPanel.tsx` (offcanvas) |
| `helpers.py` `create_all_drink_cards` | `src/components/CocktailCard.tsx` |
| `pages/mybar.py` | `src/pages/MyBar.tsx` |
| `login.py` | `src/pages/Login.tsx`, `src/pages/Register.tsx` |
| `dcc.Store(user-store)` | React Context + JWT cookie |
| `dcc.Store(my-bar-store)` | React Query cache |
| `pages/components/help_buttons.py` | `src/components/HelpModal.tsx` |

**Frontend structure:**
```
frontend/
├── src/
│   ├── api/           # Typed API client (fetch wrappers)
│   ├── components/
│   │   ├── CocktailCard.tsx
│   │   ├── FilterPanel.tsx
│   │   ├── HelpModal.tsx
│   │   └── Navbar.tsx
│   ├── pages/
│   │   ├── CocktailBrowser.tsx
│   │   ├── MyBar.tsx
│   │   ├── Login.tsx
│   │   └── Register.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useCocktails.ts    # React Query
│   │   └── useBar.ts          # React Query
│   └── main.tsx
├── index.html
└── vite.config.ts
```

**Key UX improvements:**
- **Optimistic updates**: Clicking favorite/bookmark updates the UI instantly; the API call happens in the background. No more 300ms wait per click.
- **Infinite scroll or pagination**: Replace "render all cards" with a 24-card grid + "Load more" or page controls.
- **Filter state in URL**: `?liquor=rum&search=mojito` — shareable, browser-back compatible. Replaces Dash `persistence_type="session"`.
- **Debounced search**: Text search fires after 300ms pause (Dash already does this, just keeping it).

---

### Phase 3 — Infrastructure & Cleanup

1. **Deployment**: Replace `Procfile` (gunicorn Dash) with:
   - `uvicorn backend.main:app --workers 4` for FastAPI
   - Static build of React served from FastAPI's `StaticFiles` or a CDN
   - Single `Procfile`: `web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

2. **Database cleanup**:
   - Add proper indexes: `(user_id, cocktail_id)` on favorites/bookmarks/ratings (likely already composite PK), `alcohol_type` on cocktails, GIN index on ingredients for text search
   - Fix `user_bar.ingredient_list` (PostgreSQL array) — consider normalizing to a proper join table for easier querying

3. **Remove**:
   - All Dash/Plotly dependencies (~15 packages)
   - `pandas` and `polars` from runtime (only needed in data pipeline notebooks)
   - `Flask`, `Flask-Login`, `Flask-Migrate`, `Flask-SQLAlchemy`, `Flask-Bcrypt`
   - `dash-ag-grid`, `dash-bootstrap-components`, `dash-mantine-components`

4. **Keep**:
   - `psycopg2-binary` (or switch to `asyncpg` for async)
   - `sqlalchemy` (upgrade to 2.0)
   - `alembic`
   - `python-dotenv`
   - `bcrypt` (compatible with existing password hashes)

---

---

### Phase 4 — Scraping Service

Replace the manual notebook-based scraping workflow with a scheduled, site-agnostic scraping service. The existing notebooks scraped liquor.com category pages and extracted `recipe_name`, `image`, `link`, and `ingredients` (with `name`, `quantity`, `unit`) — this service preserves that contract while making it easy to add new sources.

#### Design: Adapter Pattern

Each site gets a dedicated adapter class that implements a shared `BaseScraper` interface. The pipeline is site-agnostic — scrape → normalize → deduplicate → store — so adding a new source is just adding a new adapter file.

```
backend/scraper/
├── base.py                  # BaseScraper abstract class
├── sites/
│   ├── liquor_com.py        # liquor.com adapter
│   └── food_and_wine.py     # foodandwine.com adapter
│   └── ...                  # one file per new site
├── normalizer.py            # Ingredient normalization (from notebooks)
├── pipeline.py              # Orchestrates: scrape → normalize → dedupe → store
└── scheduler.py             # APScheduler cron setup
```

#### `BaseScraper` Interface

Every adapter must implement three things:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class RawRecipe:
    name: str
    link: str
    image: str | None
    alcohol_type: str | None          # e.g. "bourbon", "rum"
    ingredients: list[RawIngredient]  # [{name, quantity, unit}]
    source: str                       # site identifier, e.g. "liquor.com"

class BaseScraper(ABC):
    source: str                       # unique identifier for this site

    @abstractmethod
    def get_recipe_links(self) -> list[str]:
        """Return all recipe URLs to scrape."""
        ...

    @abstractmethod
    def parse_recipe(self, url: str) -> RawRecipe | None:
        """Parse a single recipe page. Return None to skip."""
        ...
```

#### liquor.com Adapter

Mirrors what the notebooks already do — category index pages → recipe links → parse each recipe:

```python
CATEGORIES = {
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

class LiquorComScraper(BaseScraper):
    source = "liquor.com"

    def get_recipe_links(self) -> list[str]:
        # GET each category page, parse pagination, collect recipe hrefs
        ...

    def parse_recipe(self, url: str) -> RawRecipe | None:
        # Parse ingredient list, quantities, units, image
        ...
```

#### Adding a New Site (e.g. Food & Wine)

1. Create `backend/scraper/sites/food_and_wine.py`
2. Subclass `BaseScraper`, set `source = "food_and_wine"`, implement `get_recipe_links` and `parse_recipe`
3. Register the adapter in `pipeline.py` — one line:
   ```python
   SCRAPERS = [LiquorComScraper(), FoodAndWineScraper()]
   ```

No changes needed to the normalizer, deduplicator, pipeline, or scheduler.

#### Normalizer

Extracted from the notebooks. Applied to every `RawRecipe` regardless of source:

- Lowercase, strip whitespace, remove commas/asterisks/accents (`unidecode`)
- Match ingredients against `ingredient_map.csv` for canonical `mapped_ingredient`
- Classify by type: garnish (unit == "garnish" or "Garnish:" prefix), bitters, syrups, other
- Lookup or create `ingredient_id` in the `ingredients` table

#### Deduplication

A recipe is a duplicate if `(recipe_name_normalized, source)` already exists in the `cocktails` table. On re-scrape, existing recipes are updated (image, link) rather than duplicated. Ingredients are diffed and updated if the site changed them.

New table column needed:
```sql
ALTER TABLE cocktails ADD COLUMN source TEXT DEFAULT 'liquor.com';
ALTER TABLE cocktails ADD COLUMN scraped_at TIMESTAMPTZ;
CREATE UNIQUE INDEX cocktails_name_source_idx ON cocktails (lower(recipe_name), source);
```

#### Scheduler

Uses APScheduler (already compatible with FastAPI's async runtime). Runs as a background task within the FastAPI process — no separate worker process needed for Heroku's free/hobby tier.

```python
# backend/scraper/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(run_pipeline, "cron", day_of_week="mon", hour=3)  # Monday 3 AM weekly

# Wired into FastAPI lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()
```

For larger scale (many sites, slow scrapes), the scheduler can be swapped for Celery Beat + Redis as the broker without changing the adapter interface.

#### Scraper HTTP Behavior

All adapters share a common `ScraperSession` wrapper (not per-adapter) so politeness rules are consistent:

- Random delay between requests: 1–3 seconds
- `User-Agent` header mimicking a real browser
- Retry with exponential backoff (3 attempts) on 429/503
- `robots.txt` check before scraping any domain

#### New Dependencies (scraper only)

```
httpx          # async HTTP client
beautifulsoup4 # HTML parsing
apscheduler    # job scheduling
unidecode      # accent normalization (already used in notebooks)
```

---

## What Does NOT Change

- PostgreSQL schema (minor additions for scraper: `source`, `scraped_at` columns and one index)
- Business logic (filtering rules, NPS calculation, "can make" logic)
- Existing bcrypt password hashes (users don't need to reset passwords)
- The data pipeline notebooks in `testing/` (they become optional/archival once the scraper service is running)

---

## Estimated Scope

| Phase | Effort | Risk |
|---|---|---|
| Phase 1 (FastAPI backend) | Medium | Low — additive, Dash still running |
| Phase 2 (React frontend) | Large | Medium — full UI rewrite |
| Phase 3 (cleanup/deploy) | Small | Low |
| Phase 4 (scraping service) | Medium | Low — self-contained, independent of phases 1-3 |

Phase 4 can be built in parallel with Phase 1, since both are backend Python and neither depends on the other. The scraper writes to the same PostgreSQL database the API reads from.

The safest execution order is to build Phase 1 completely and test it against the existing database before starting Phase 2. The Dash app can keep running during Phase 1 — both can coexist.
