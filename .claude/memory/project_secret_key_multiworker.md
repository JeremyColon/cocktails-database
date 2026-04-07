---
name: SECRET_KEY multi-worker JWT failure
description: Heroku multi-worker deployments require a static SECRET_KEY — shell substitution syntax breaks JWT signing/verification across workers
type: project
---

On Heroku, `SECRET_KEY` was set to the literal string `"$(openssl rand -hex 32)"` instead of an actual hex value. With `WEB_CONCURRENCY=2`, each uvicorn worker evaluates the config independently. If pydantic_settings or the shell parses the literal string differently across workers, Worker A signs a JWT at login with one effective key and Worker B fails to verify it on the next request → "Signature verification failed" → `get_optional_user` returns `None` → all user-specific filters (favorites, can_make, bookmarks) silently have no effect.

**Symptom:** User is visibly logged in (filter sections appear), but selecting user filters has no effect. Heroku logs show `user_id=None` despite `access_token` cookie being present.

**Fix applied (2026-03-26):** Replaced the config var with a real static key generated via:
```
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Set via `heroku config:set SECRET_KEY=<value> -a cocktail-finder`.

**Why:** Shell substitution syntax (`$(...)`) in Heroku config vars is never evaluated — it's stored and read as a literal string. Even if both workers read the same literal, the value is predictable/weak as a JWT secret.

**How to apply:** If user-specific features (favorites, bar, ratings) ever silently stop working after a Heroku config change or re-deploy, check `heroku config:get SECRET_KEY` to confirm it's a real hex value, not a shell expression. Never set SECRET_KEY using shell substitution syntax.
