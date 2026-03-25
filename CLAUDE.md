# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Instructions

- Write all memory and contexst files to a project-level .claude/ directory rather than my computer's local .claude/ directory.

## Status

**In active refactor** — see `docs/refactor.md`. The legacy Dash app (root directory) is being replaced with a FastAPI + React stack. New code lives in `backend/`. Do not add new features to the Dash app.

## Overview

Cocktail discovery app. Users create accounts, add ingredients to their bar, filter/search cocktails, and favorite/bookmark/rate recipes. Weekly scraping keeps the recipe database fresh from multiple sources.

## Running the New Backend

```bash
cd backend
pip install -r requirements.txt

# Run FastAPI dev server
uvicorn backend.main:app --reload --port 8000

# Apply DB migrations
alembic upgrade head

# Trigger a scrape manually (runs the full pipeline once)
python -c "import asyncio; from backend.scraper.pipeline import run_pipeline; asyncio.run(run_pipeline())"
```

## Backend Architecture (`backend/`)

**Entry point:** `backend/main.py` — FastAPI app with lifespan (starts Redis cache + APScheduler)

**Routers** (`backend/routers/`)
- `auth.py` — `/api/auth/*` — register, login (JWT httpOnly cookie), logout, me, change password
- `cocktails.py` — `/api/cocktails` (POST with filter body), `/options` (dropdown data), `/{id}/favorite|bookmark|rating`
- `bar.py` — `/api/bar` GET/PUT, `/add`, `/remove`, `/stats`

**Services** (`backend/services/`)
- `cocktail_service.py` — All filtering as a single parameterized SQL query (replaces pandas logic). `get_ingredient_options()` for dropdowns.
- `bar_service.py` — Bar CRUD + stats (can_make / partial / missing ingredients), all in SQL

**Supporting modules**
- `config.py` — Settings via `pydantic-settings`; reads existing env vars (`COCKTAILS_HOST`, `COCKTAILS_PWD`, etc.) or a `DATABASE_URL`
- `database.py` — Async SQLAlchemy engine + `get_db` dependency
- `models.py` — ORM models for all tables (users, cocktails, ingredients, cocktails_ingredients, user_favorites, user_bookmarks, user_ratings, user_bar)
- `schemas.py` — Pydantic request/response models
- `dependencies.py` — JWT auth (`get_current_user`, `get_optional_user`)
- `cache.py` — Optional Redis cache (disabled gracefully if `REDIS_URL` not set)

## Scraper (`backend/scraper/`)

Runs every **Monday at 3 AM** via APScheduler. Adapter pattern — each site is one file.

- `base.py` — `BaseScraper` ABC + `RawRecipe` / `RawIngredient` dataclasses
- `session.py` — Shared `httpx` client with 1–3s random delay, retry/backoff, robots.txt check
- `normalizer.py` — Cleans ingredient names (lowercase, unidecode, strip); maps against `data/ingredient_map.csv`
- `pipeline.py` — Orchestrates scrape → normalize → upsert. **Add new sites to `SCRAPERS` list here.**
- `scheduler.py` — APScheduler config
- `sites/liquor_com.py` — liquor.com adapter (category pages + recipe parser)
- `sites/food_and_wine.py` — Food & Wine adapter (JSON-LD preferred, HTML fallback)

**Adding a new scraper site:**
1. Create `backend/scraper/sites/my_site.py`, subclass `BaseScraper`
2. Implement `get_recipe_links()` and `parse_recipe()`
3. Add `MySiteScraper()` to `SCRAPERS` in `pipeline.py`

## Database

PostgreSQL. Env vars: `COCKTAILS_HOST`, `COCKTAILS_PWD`, `COCKTAILS_PORT`, `COCKTAILS_USER`, `COCKTAILS_DB` (or a single `DATABASE_URL`).

Migrations are in `migrations/` (Alembic). Run `alembic upgrade head` after pulling.

`ingredient_map.csv` columns: `ingredient_id`, `ingredient`, `ingredient_map`, `alcohol_type`

## Auth

JWT stored as an `httpOnly` cookie (`access_token`). Existing bcrypt password hashes are fully compatible — no user migration needed. `get_current_user` / `get_optional_user` are FastAPI dependencies in `dependencies.py`.

## Legacy Dash App

The original Dash app (`app.py`, `index.py`, `login.py`, `pages/`, `utils/`) remains runnable via `python index.py` but is not being maintained. It will be removed after the React frontend (Phase 2) is complete.
