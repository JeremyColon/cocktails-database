---
name: FastAPI route ordering — static before dynamic
description: Static path segments (e.g. /cart) must be registered before dynamic segments (e.g. /{cocktail_id}) or FastAPI will match the wrong handler
type: project
---

In `backend/routers/cocktails.py`, always define static GET routes (`/cart`, `/options`, `/ingredients`) **before** the catch-all dynamic route `/{cocktail_id}`.

FastAPI matches routes in registration order. If `GET /{cocktail_id}` appears first, a request to `/cart` is matched with `cocktail_id="cart"`, fails int validation, and returns a 422 — silently breaking any frontend query that hits the static endpoint.

**Why:** Hit this bug when adding `GET /cart` after `GET /{cocktail_id}` — the cart count query always returned a 422, causing the navbar badge to disappear and the dropdown to show "empty".

**How to apply:** Whenever adding a new static GET route under `/api/cocktails`, place it above the `/{cocktail_id}` handler.
