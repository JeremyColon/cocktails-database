# Memory Index

## Project

- [SECRET_KEY multi-worker JWT failure](memory/project_secret_key_multiworker.md) — Heroku multi-worker deployments require a static SECRET_KEY; shell substitution syntax causes JWT signing/verification to fail across workers, silently breaking all user-specific filters
