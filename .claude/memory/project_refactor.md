---
name: active_refactor_plan
description: User wants to refactor the Dash cocktail app to FastAPI + React for scalability
type: project
---

Migrating cocktails-database from Dash (Python) to FastAPI (backend) + React/Vite (frontend).

Full plan is in `docs/refactor.md`.

**Why:** Dash is memory-intensive and not scalable. In-memory pandas filtering, 100+ modal DOM generation, no pagination, and callback overhead make it slow at scale.

**Target stack:**
- Backend: FastAPI + SQLAlchemy 2.0 async + Redis caching
- Frontend: React + Vite + React Query (optimistic updates, pagination)
- Auth: JWT (httpOnly cookies) — bcrypt hashes are compatible, no user migration needed
- DB: same PostgreSQL schema with added indexes

**How to apply:** When suggesting code changes, target the new FastAPI/React stack described in `docs/refactor.md`. Do not add new features to the Dash app.
