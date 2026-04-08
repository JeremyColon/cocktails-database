---
name: Git workflow — branch first, never push directly to main
description: All changes must go on a feature or bug branch; never commit or push directly to main
type: feedback
---

Always create a branch before making changes. Never commit directly to main or push directly to main.

**Why:** CLAUDE.md explicitly requires this workflow. Branches allow testing on Heroku (or locally) before merging. Pushing directly to main bypasses review and deploys untested code immediately.

**How to apply:**
- Before any code change, run `git checkout -b feature/short-description` or `bug/short-description`
- Commit and push to that branch
- Open a PR into main when ready
- Do this even for small bug fixes — no exceptions
