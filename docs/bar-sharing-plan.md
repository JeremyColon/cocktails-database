# Plan: Bar Sharing & Quick Start

Three related but independent features for getting a bar populated quickly and sharing it with others.

---

## Feature Overview

| Feature | Complexity | Value |
|---|---|---|
| **Bar Starter** — curated "starter kits" to bulk-add common ingredients | Low | High |
| **One-time Share** — snapshot link to copy your bar to someone else | Medium | High |
| **Permanent Link** — two accounts share one live bar (household mode) | High | Medium |

Recommended build order: Bar Starter → One-time Share → Permanent Link.

---

## Feature 1: Bar Starter Kits

### Concept
On the My Bar page, a new section (alongside "Add Ingredients" and "Top Missing") shows curated starter kits — pre-grouped collections of popular ingredients a user can bulk-add in one click. Two flavors:

- **Popular kits** — static curated groups: "Base Spirits", "Citrus & Fresh", "Bitters & Vermouth", "Syrups & Liqueurs"
- **Top ingredients** — dynamic: query the DB for the top N most-used mapped_ingredients, shown as selectable chips

The user can select a whole kit or pick individual items from it, then click "Add to my bar".

### What's Already There
`GET /api/cocktails/ingredients?search=` already returns ingredient search results. We can reuse this shape. The "Top Missing" stat already ranks ingredients by cocktail count — we can adapt the same SQL for a global ranking (not personalized to what the user is missing).

### New Backend Endpoint
`GET /api/bar/starters` — returns both the static kits and the top-N dynamic list:

```python
# Static kits are defined in code (no DB):
STARTER_KITS = [
    {"name": "Base Spirits",        "tags": ["whiskey", "vodka", "gin", "rum", "tequila"]},
    {"name": "Citrus & Fresh",      "tags": ["lemon juice", "lime juice", "orange juice"]},
    {"name": "Bitters & Vermouth",  "tags": ["angostura bitters", "sweet vermouth", "dry vermouth"]},
    {"name": "Syrups & Liqueurs",   "tags": ["simple syrup", "triple sec", "grenadine"]},
]
```

Each kit resolves its tags against the `ingredients` table (fuzzy match on `mapped_ingredient`) to get real `ingredient_id`s. The dynamic "Top 20" list comes from the same SQL used in bar_stats, but globally (no user filter):

```sql
SELECT i.ingredient_id, i.mapped_ingredient, COUNT(DISTINCT ci.cocktail_id) AS cocktail_count
FROM cocktails_ingredients ci
JOIN ingredients i ON i.ingredient_id = ci.ingredient_id
WHERE i.mapped_ingredient IS NOT NULL AND ci.unit != 'garnish'
GROUP BY i.ingredient_id, i.mapped_ingredient
ORDER BY cocktail_count DESC
LIMIT 20
```

Response shape:
```json
{
  "kits": [
    {
      "name": "Base Spirits",
      "ingredients": [{ "ingredient_id": 12, "mapped_ingredient": "whiskey", "alcohol_type": "whiskey" }, ...]
    }
  ],
  "top_ingredients": [{ "ingredient_id": 5, "mapped_ingredient": "lime juice", "cocktail_count": 142 }, ...]
}
```

Cached for 1 hour (changes only when the recipe DB changes).

### Frontend Changes
**`MyBar.tsx`** — add a "Get Started" section in the right column (above or below "Top Missing") with:
- Expandable/tabbed kits: clicking "Base Spirits" shows the ingredients in that kit
- Each ingredient chip shows: name + alcohol_type badge + whether it's already in the bar (grayed out if so)
- "Add kit" button bulk-adds all non-bar ingredients from that kit
- "Top ingredients" tab shows the 20 most common ingredients as chips, same interaction

No new hooks needed — reuse `useAddToBar`. New `useBarStarters()` query hook for the endpoint.

### Files to Change
| File | Change |
|---|---|
| `backend/routers/bar.py` | Add `GET /starters` endpoint |
| `backend/services/bar_service.py` | Add `get_starters(db)` function |
| `frontend/src/hooks/useBar.ts` | Add `useBarStarters()` |
| `frontend/src/api/bar.ts` | Add `barApi.starters()` call |
| `frontend/src/pages/MyBar.tsx` | Add starter kits UI section |

---

## Feature 2: One-time Bar Share (Snapshot)

### Concept
User A clicks "Share my bar" on My Bar → gets a link (e.g. `https://app.com/bar/import?token=abc123`). They send it to a friend. The friend opens it (logged in or prompted to log in first), sees a preview of what they'll get ("You'll be adding 24 ingredients including Bourbon, Gin, Lime Juice…"), and clicks "Add to my bar" or "Replace my bar". One-time, no ongoing sync.

### Token Design
Store tokens in a new `bar_share_tokens` table:
```sql
CREATE TABLE bar_share_tokens (
    token      TEXT    PRIMARY KEY,
    user_id    BIGINT  NOT NULL REFERENCES users(id),
    expires_at TIMESTAMP NOT NULL,
    used_at    TIMESTAMP
);
```
- `token` — random 12-char alphanumeric, generated server-side (via `secrets.token_urlsafe`)
- Expires in 7 days
- Marked as used after first import (single-use by default; could make multi-use but single-use is simpler and safer)
- The user's current `ingredient_list` is fetched at import time from `user_bar` — not stored in the token. This means the link always reflects the bar as it was when the recipient uses it, not when it was generated. If you want a true snapshot, we'd store the ingredient IDs in the token row.

**Decision point:** Store ingredient snapshot in the token, or fetch live at import time?
- **Live fetch (simpler)**: token just stores `user_id`. If user A updates their bar before friend imports, friend gets the updated bar. Feels natural — "share my current bar".
- **Snapshot (stored)**: add `ingredient_ids BIGINT[]` to the token row. What the friend imports is frozen at share time.

Recommendation: **live fetch** — simpler, and the share link is typically used within hours of being generated.

### New Backend Endpoints
```
POST /api/bar/share          → generates token, returns share URL
GET  /api/bar/share/:token   → preview (list of ingredients in the shared bar) — public
POST /api/bar/import/:token  → imports (requires auth); marks token used
```

### Frontend Changes
- **`MyBar.tsx`**: "Share my bar" button → calls generate endpoint → shows copy-able link (same copied/Check icon pattern used elsewhere)
- **New page `BarImport.tsx`** (`/bar/import?token=...`): shows preview of what's being imported, "Add to my bar" / "Replace my bar" options, requires login first
- New route in `App.tsx`: `<Route path="/bar/import" element={<BarImport />} />`

### Files to Change
| File | Change |
|---|---|
| `migrations/versions/005_add_bar_share_tokens.py` | New table |
| `backend/models.py` | `BarShareToken` model |
| `backend/routers/bar.py` | 3 new endpoints |
| `backend/services/bar_service.py` | Token generation/validation/import logic |
| `frontend/src/api/bar.ts` | 3 new API calls |
| `frontend/src/hooks/useBar.ts` | `useShareBar()`, `useBarSharePreview()`, `useImportBar()` |
| `frontend/src/pages/MyBar.tsx` | Share button + copied state |
| `frontend/src/pages/BarImport.tsx` | New page |
| `frontend/src/App.tsx` | New route |

---

## Feature 3: Permanent Bar Link (Household Mode)

### Concept
Two users (e.g. a couple or roommates) link their accounts so they share one bar inventory. Either person can add/remove ingredients and both see the change immediately. Ratings, favorites, bookmarks, and cart remain personal.

### Data Model
Introduce a dedicated `bars` table that holds the ingredient list. `user_bar` becomes a mapping of user → bar. Multiple users can point to the same `bar_id`.

```sql
-- New table: the actual bar (ingredient list lives here)
CREATE TABLE bars (
    bar_id          BIGSERIAL PRIMARY KEY,
    ingredient_list BIGINT[]  NOT NULL DEFAULT '{}',
    last_updated_ts TIMESTAMP,
    deleted_at      TIMESTAMP  -- soft delete; set when a user abandons this bar on link
);

-- user_bar becomes a thin mapping (ingredient_list column is removed)
ALTER TABLE user_bar ADD COLUMN bar_id BIGINT REFERENCES bars(bar_id);
ALTER TABLE user_bar DROP COLUMN ingredient_list;
```

**Migration path for existing data:**
For each existing `user_bar` row: create a `bars` row seeded with their current `ingredient_list`, then set `user_bar.bar_id` to point to it.

**Linking behavior:**
When user B links to user A's bar:
1. User B's current `bars` row is soft-deleted (`deleted_at = now()`).
2. `user_bar.bar_id` for user B is updated to user A's `bar_id`.
3. User B now reads and writes the same `bars` row as user A — fully symmetric, no primary/secondary.

**Confirmation modal shown before accepting a link:**
The accepting user chooses one of two options:
- **Merge** — ingredients unique to their bar are added to the inviter's bar first, then they join it. Net effect: the shared bar becomes the union of both.
- **Replace** — they adopt the inviter's bar as-is; their current ingredients are discarded.

Either way, their old `bars` row is soft-deleted after the operation. Warning shown regardless:
> "Your current bar cannot be recovered after linking."

**Merge implementation:**
```sql
-- 1. Find ingredient_ids in B's bar not already in A's bar
SELECT unnest(b.ingredient_list) FROM bars b WHERE b.bar_id = :b_bar_id
EXCEPT
SELECT unnest(a.ingredient_list) FROM bars a WHERE a.bar_id = :a_bar_id

-- 2. Append the diff to A's bar
UPDATE bars SET ingredient_list = ingredient_list || :diff_ids WHERE bar_id = :a_bar_id
```
Then soft-delete B's old bar and update `user_bar.bar_id` for B to point at A's `bar_id`.

**Unlinking:**
Either user can unlink at any time. A new empty `bars` row is created for the departing user and their `user_bar.bar_id` is updated to point to it. The shared bar remains intact for whoever stays.

### Invite Flow
```sql
CREATE TABLE bar_link_invites (
    token       TEXT      PRIMARY KEY,
    inviter_id  BIGINT    NOT NULL REFERENCES users(id),
    expires_at  TIMESTAMP NOT NULL,
    accepted_at TIMESTAMP
);
```

Endpoints:
```
POST   /api/bar/link/invite          → generate invite token (7-day TTL, multi-use until accepted once)
GET    /api/bar/link/preview/:token  → return inviter's email so acceptor knows who they're linking with
POST   /api/bar/link/accept/:token   → soft-delete acceptor's old bar, point their user_bar to inviter's bar_id
DELETE /api/bar/link                 → unlink; create new empty bars row for requesting user
GET    /api/bar/link/status          → { linked: bool, linked_to_email: string | null, household_size: int }
```

### Cocktail Service — `in_bar` Join
No resolver function needed. Change the join in `cocktail_service.py` from:
```sql
LEFT JOIN user_bar ub ON ub.user_id = :user_id
```
to:
```sql
LEFT JOIN user_bar ub ON ub.user_id = :user_id
LEFT JOIN bars b ON b.bar_id = ub.bar_id
```
Then reference `b.ingredient_list` instead of `ub.ingredient_list`. Transparent — works automatically for both solo and linked users.

### Bar Service Changes
All `get_bar`, `add_to_bar`, `remove_from_bar`, `set_bar` operations change from writing to `user_bar.ingredient_list` directly to reading/writing `bars.ingredient_list` via the `bar_id` lookup. Cache keys stay as `bar:{user_id}` (or can switch to `bar:{bar_id}` — both work; `bar_id` is slightly more cache-efficient for shared bars since one invalidation covers all linked users).

### Frontend Changes
**`MyBar.tsx`** — new "Household" section:
- If not linked: "Link with a household member" button → generates invite link → copy-to-clipboard (same pattern as share link)
- If linked: "Sharing bar with [email]" + "Unlink" button
- Household of 3+: "Sharing bar with X others" + list of emails

### Complexity Notes
- Circular link prevention: user A tries to link to user B who is already on a bar with user A — must be blocked (check if inviter's `bar_id === acceptor's bar_id` before linking)
- The invite token is single-accept (one user can accept it), but multi-use in the sense that the inviter doesn't need to regenerate it if the first attempt fails

### Files to Change
| File | Change |
|---|---|
| `migrations/versions/006_add_bar_linking.py` | `linked_to_user_id` column + `bar_link_invites` table |
| `backend/models.py` | Update `UserBar`, add `BarLinkInvite` |
| `backend/services/bar_service.py` | `resolve_bar_user_id()`, all bar ops use it |
| `backend/services/cocktail_service.py` | Pass resolved bar user_id to `in_bar` join |
| `backend/routers/bar.py` | 4 new endpoints |
| `frontend/src/api/bar.ts` | New API calls |
| `frontend/src/hooks/useBar.ts` | New hooks |
| `frontend/src/pages/MyBar.tsx` | Household section |

---

## Decisions

1. **Bar Starter kits** — Hybrid: static kit names/groupings with intentionally curated specific ingredients (e.g. "Tito's Vodka" not "vodka"), but ingredient IDs resolved dynamically from the DB so mappings stay current as the ingredient table evolves.

2. **One-time share token** — TTL-based (7 days), multi-use within that window. The sharer doesn't need to regenerate a new link each time someone imports — anyone with the link can import within the TTL. After expiry, a new token must be generated.

3. **Linking gives the accepting user a choice** — **Merge** (their unique ingredients are added to the inviter's bar before joining) or **Replace** (adopt inviter's bar as-is). Either way, their old `bars` row is soft-deleted and not recoverable. A warning is shown before confirming.

4. **`in_bar` in the cocktail browser updates automatically** — transparent, no toggle needed. Implemented by adding a second JOIN to the `bars` table in `cocktail_service.py`. No resolver function needed with the new `bars` data model.