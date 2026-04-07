# Plan: Share Feature + Cocktail Detail Page

## Context
Users want to share individual cocktails with others to grow the user base organically. The share link points to a new public `/cocktail/:id` detail page — fully visible without an account, but richer (bar availability, action buttons) when logged in. On the card, both the image and recipe name become links to the internal detail page; the ExternalLink button is replaced by a Share button (copies the deep link to clipboard). The external source link moves to the detail page only.

---

## UX Summary

| Element | Before | After |
|---------|--------|-------|
| Card image | Static display | `<Link>` to `/cocktail/:id` (internal, same tab) |
| Recipe name | Plain text | `<Link>` to `/cocktail/:id` (internal, same tab) |
| ExternalLink button (top-right of name) | Opens source URL in new tab | Replaced by Share button — copies `/cocktail/:id` URL to clipboard, shows "Copied!" for 1.5s |
| External source link | Card button | Lives on detail page only (source favicon + link) |
| `/cocktail/:id` route | Doesn't exist | New public detail page |

---

## Files to Create
- `frontend/src/pages/CocktailDetail.tsx`

## Files to Modify

### Backend
| File | Change |
|------|--------|
| `backend/routers/cocktails.py` | Add `GET /{cocktail_id}` endpoint (public, optional auth) |
| `backend/services/cocktail_service.py` | Add `get_cocktail_by_id(id, db, user_id)` function |

### Frontend
| File | Change |
|------|--------|
| `frontend/src/api/cocktails.ts` | Add `getById(id)` API call |
| `frontend/src/hooks/useCocktails.ts` | Add `useCocktail(id)` query hook |
| `frontend/src/components/CocktailCard.tsx` | Wrap image in external link; replace ExternalLink with Share button |
| `frontend/src/App.tsx` | Add `/cocktail/:id` public route |

---

## Implementation Details

### 1. Backend service — `get_cocktail_by_id`
New function in `cocktail_service.py`, reusing the same SELECT/JOIN pattern as `get_cocktails`:

```python
async def get_cocktail_by_id(
    cocktail_id: int,
    db: AsyncSession,
    user_id: int | None = None,
) -> CocktailOut | None:
```

- Same `user_joins` / `select_user_cols` / ingredient-fetch logic as the list query
- WHERE clause is simply `WHERE c.cocktail_id = :cocktail_id`
- No pagination, no ORDER BY, no `COUNT(*) OVER ()`
- Returns `None` if not found (router raises 404)

### 2. Backend router — `GET /api/cocktails/{cocktail_id}`
Add **before** the `/{cocktail_id}/cart` and other sub-routes to avoid shadowing:

```python
@router.get("/{cocktail_id}", response_model=CocktailOut)
async def get_cocktail(
    cocktail_id: int,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    cocktail = await get_cocktail_by_id(cocktail_id, db, user_id=user.id if user else None)
    if not cocktail:
        raise HTTPException(status_code=404, detail="Cocktail not found")
    return cocktail
```

> Note: FastAPI matches static segments (`/cart`, `/ingredients`, `/options`) before parameterized ones (`/{cocktail_id}`), so ordering is safe as long as static GET routes stay above this one.

### 3. Frontend API + hook
**`cocktails.ts`:**
```typescript
getById: (id: number) => api.get<Cocktail>(`/cocktails/${id}`),
```

**`useCocktails.ts`:**
```typescript
export function useCocktail(id: number) {
  return useQuery({
    queryKey: ['cocktail', id],
    queryFn: () => cocktailsApi.getById(id),
  })
}
```

### 4. `CocktailCard.tsx` changes

**Image → internal detail link:**
```tsx
<Link to={`/cocktail/${c.cocktail_id}`}
  className="relative overflow-hidden h-48 bg-parchment-200 block">
  {/* existing image / placeholder / badges / progress bar — unchanged */}
</Link>
```
No conditional needed — always links to detail page regardless of whether `c.link` exists.

**Share button (replaces ExternalLink):**
```tsx
const [copied, setCopied] = useState(false)

function handleShare() {
  navigator.clipboard.writeText(`${window.location.origin}/cocktail/${c.cocktail_id}`)
  setCopied(true)
  setTimeout(() => setCopied(false), 1500)
}

// In JSX (where ExternalLink button was):
<button onClick={handleShare} className="shrink-0 text-bark hover:text-amber transition-colors mt-0.5"
  title="Copy share link">
  {copied
    ? <Check className="w-4 h-4 text-green-600" />
    : <Link2 className="w-4 h-4" />}
</button>
```

Import `Link2, Check` from lucide-react; remove `ExternalLink`. Also import `Link` from `react-router-dom` for the image and recipe name links.

**Recipe name → internal detail link:**
```tsx
<Link to={`/cocktail/${c.cocktail_id}`}
  className="font-display text-xl text-mahogany leading-tight line-clamp-2 hover:text-amber transition-colors">
  {c.recipe_name}
</Link>
```

### 5. `CocktailDetail.tsx` — new page

**Layout** (`max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-16`):

```
← Browse                              [Share link button]

[Hero image — full width, rounded, max-h-80]

[Alcohol type badge]  Recipe Name      [source favicon + link]
NPS / avg rating / num ratings

──────────────────────────────────────
Ingredients
  ● London dry gin          1.5 oz     ✓ in bar
  ● Lemon juice             0.75 oz    ✗ missing
  ...

──────────────────────────────────────
[★ Favorite]  [⊟ Bookmark]  [🛒 Cart]  [Rate]   ← logged-in only
```

- Uses `useCocktail(id)` where `id = parseInt(useParams().id)`
- Reuses the same `useFavorite`, `useBookmark`, `useCart`, `useRate` mutation hooks from the card
- Share button on detail page copies `window.location.href`
- Loading skeleton + 404 state
- No auth required to view; action buttons hidden when logged out

### 6. `App.tsx` — new route
Add as a public route (no ProtectedRoute wrapper):
```tsx
<Route path="/cocktail/:id" element={<CocktailDetail />} />
```

---

## Verification
1. Start backend + frontend locally
2. Open a cocktail card — image should open source URL in new tab
3. Click share button — "Copied!" flashes briefly; paste confirms `localhost:5173/cocktail/123`
4. Navigate to that URL while logged out — detail page loads with recipe + ingredients, no action buttons
5. Navigate while logged in — bar availability indicators show, action buttons present and functional
6. Share a link to someone else (simulate by opening in incognito) — page loads cleanly
