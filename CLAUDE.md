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
# Install dependencies
uv sync

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

## Git Workflow

All work should be done on a branch. Never commit directly to `main`.

**Branch naming:**
- New feature: `feature/short-description` (e.g. `feature/ri-cost-breakdown`)
- Bug fix: `bug/short-description` (e.g. `bug/ops-support-double-count`)

**Workflow:**
1. Branch from `main`: `git checkout -b feature/my-feature`
2. Make changes, commit with descriptive messages
3. Open a PR into `main` when ready for review
4. Delete the branch after merge

Never force-push to `main`. If a branch has conflicts with `main`, rebase or merge `main` into the branch before merging the PR.

## Testing (Red/Green TDD)

This project has no test suite yet. When adding tests, follow red/green TDD:

1. **Red** — write a failing test that describes the intended behavior. Run it and confirm it fails for the right reason (not a syntax error or import problem).
2. **Green** — write the minimum code to make it pass. No more.
3. **Refactor** — clean up without breaking the test.

### Backend

Use `pytest` + `pytest-asyncio` + `httpx.AsyncClient` (FastAPI's test client). Tests live in `backend/tests/`.

```bash
uv add --dev pytest pytest-asyncio
uv run pytest backend/tests/
```

**Fixtures** (`backend/tests/conftest.py`):
- Spin up a real test database (separate `TEST_DATABASE_URL` env var pointing at a local Postgres test DB).
- Apply migrations with `alembic upgrade head` before the test session.
- Wrap each test in a transaction that rolls back after, so tests are isolated without re-running migrations.
- Yield an `AsyncClient` pointed at the FastAPI app with `base_url="http://test"`.

**What to test:**
- Service functions directly (e.g. `add_to_bar`, `get_bar_stats`) — these contain the real logic.
- Router endpoints for auth/permission boundaries (unauthenticated requests should 401, wrong user shouldn't see another's bar).
- Do **not** mock the database — we've been burned by mock/prod divergence before. Hit the real test DB.

### Frontend

Use Vitest + React Testing Library. Tests live alongside components as `*.test.tsx`.

```bash
cd frontend && npm run test
```

**What to test:**
- Hook behavior (e.g. `useCart` optimistic update reverts on error).
- Components that have non-trivial conditional rendering (e.g. `BarLink` showing error state vs. success state).
- Do **not** test Tailwind classes or static markup — test behavior, not appearance.

---

## Exploring Options Before Implementing

Before jumping into implementation, consider whether a better approach exists that the developer may not be aware of. This codebase sits at the intersection of several domains (finance, Salesforce, SharePoint, React, Flask) — it is easy to solve a problem with a custom solution when a built-in capability, library feature, or platform primitive would do it more simply and reliably.

When given a task, ask: **is there a cleaner way to do this that I should surface before writing code?**

Examples of things worth raising proactively:
- A Salesforce formula field or flow that eliminates backend logic entirely
- A Microsoft Graph API capability that replaces custom Excel parsing
- A React Query pattern (caching, optimistic updates, background refetch) that replaces manual state management
- A Flask/SQLAlchemy feature that replaces a hand-rolled implementation
- A Python standard library function that replaces a custom utility
- A Tailwind component pattern that avoids a bespoke CSS solution

The right approach is: briefly describe the option, explain the tradeoff, and let the developer decide. Don't assume the simplest implementation you already know is the best one available.