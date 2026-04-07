# Memory Index

## Project

- [SECRET_KEY multi-worker JWT failure](memory/project_secret_key_multiworker.md) — Heroku multi-worker deployments require a static SECRET_KEY; shell substitution syntax causes JWT signing/verification to fail across workers, silently breaking all user-specific filters
- [FastAPI route ordering — static before dynamic](memory/project_fastapi_route_ordering.md) — Static routes (/cart, /options) must be registered before /{cocktail_id} or FastAPI silently matches the wrong handler
