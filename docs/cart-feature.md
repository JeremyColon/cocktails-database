# Plan: Tonight's Cart Feature

## Context
Users want a lightweight "I'm making these tonight" queue — separate from bookmarks/favorites — that persists across sessions. The UX is a shopping-cart metaphor: a cart icon in the navbar shows a count badge; clicking it filters the cocktail browser down to only in-cart recipes (no separate page). Individual cocktail cards get a cart toggle button alongside the existing star/bookmark buttons.

---

## Files to Create
- `migrations/versions/004_add_user_cart.py`

## Files to Modify

### Backend
| File | Change |
|------|--------|
| `backend/models.py` | Add `UserCart` model; add `cart` relationship to `User` |
| `backend/schemas.py` | Add `CartRequest`; add `in_cart: bool` to `CocktailOut`; add `cart_only: bool = False` to `CocktailFilterParams` |
| `backend/routers/cocktails.py` | Add `POST /{cocktail_id}/cart` endpoint; add `GET /cart` count endpoint; add `DELETE /cart` clear endpoint |
| `backend/services/cocktail_service.py` | Add `user_cart` LEFT JOIN + `in_cart` SELECT col + `cart_only` WHERE clause |

### Frontend
| File | Change |
|------|--------|
| `frontend/src/api/cocktails.ts` | Add `cart(id, val)`, `cartCount()`, and `clearCart()` calls |
| `frontend/src/hooks/useCocktails.ts` | Add `useCart()`, `useCartCount()`, and `useClearCart()` |
| `frontend/src/components/CocktailCard.tsx` | Add cart toggle button in the action row |
| `frontend/src/components/Navbar.tsx` | Add `ShoppingCart` icon with count badge; clicking sets `cart_only: true` on filters |
| `frontend/src/components/FilterPanel.tsx` | Add "Cart only" checkbox (auth-only), under Favorites/Bookmarks only |
| `frontend/src/pages/CocktailBrowser.tsx` | Show "Viewing tonight's cart" banner with clear + dismiss when `cart_only` is active |
| `frontend/src/App.tsx` | Lift `filters` + `setFilters` state up from `CocktailBrowser` so Navbar can trigger cart filter |

---

## Implementation Details

### 1. Migration — `004_add_user_cart.py`
```sql
CREATE TABLE user_cart (
    user_id      BIGINT  NOT NULL REFERENCES users(id),
    cocktail_id  INT     NOT NULL REFERENCES cocktails(cocktail_id),
    in_cart      BOOLEAN NOT NULL DEFAULT FALSE,
    last_updated_ts TIMESTAMP,
    PRIMARY KEY (user_id, cocktail_id)
);
CREATE INDEX ix_user_cart_user_id ON user_cart (user_id);
```

### 2. `backend/models.py`
Add after `UserRating`:
```python
class UserCart(Base):
    __tablename__ = "user_cart"
    user_id:     Mapped[int]  = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    cocktail_id: Mapped[int]  = mapped_column(Integer, ForeignKey("cocktails.cocktail_id"), primary_key=True)
    in_cart:     Mapped[bool] = mapped_column(Boolean, default=False)
    last_updated_ts: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))
    user: Mapped["User"] = relationship(back_populates="cart")
```
Add to `User`: `cart: Mapped[list["UserCart"]] = relationship(back_populates="user")`

### 3. `backend/schemas.py`
- `CocktailOut`: add `in_cart: bool`
- `CocktailFilterParams`: add `cart_only: bool = False`
- New: `class CartRequest(BaseModel): in_cart: bool`

### 4. `backend/routers/cocktails.py`
```python
@router.post("/{cocktail_id}/cart")
async def set_cart(cocktail_id: int, body: CartRequest,
                   db=Depends(get_db), user=Depends(get_current_user)):
    await db.execute(text("""
        INSERT INTO user_cart (user_id, cocktail_id, in_cart, last_updated_ts)
        VALUES (:uid, :cid, :val, now())
        ON CONFLICT (user_id, cocktail_id)
        DO UPDATE SET in_cart = EXCLUDED.in_cart, last_updated_ts = now()
    """), {"uid": user.id, "cid": cocktail_id, "val": body.in_cart})
    await db.commit()
    return {"cocktail_id": cocktail_id, "in_cart": body.in_cart}

@router.get("/cart")
async def get_cart_count(db=Depends(get_db), user=Depends(get_current_user)):
    row = await db.execute(
        text("SELECT COUNT(*) FROM user_cart WHERE user_id = :uid AND in_cart = true"),
        {"uid": user.id}
    )
    return {"count": row.scalar()}

@router.delete("/cart")
async def clear_cart(db=Depends(get_db), user=Depends(get_current_user)):
    await db.execute(
        text("UPDATE user_cart SET in_cart = false, last_updated_ts = now() WHERE user_id = :uid AND in_cart = true"),
        {"uid": user.id}
    )
    await db.commit()
    return {"cleared": True}
```

### 5. `backend/services/cocktail_service.py`
In `user_joins`, add:
```sql
LEFT JOIN user_cart uc ON c.cocktail_id = uc.cocktail_id AND uc.user_id = :user_id
```
In `select_user_cols`, add:
```sql
COALESCE(uc.in_cart, false) AS in_cart,
```
In WHERE clause (alongside `favorites_only`/`bookmarks_only`):
```python
if params.cart_only:
    my_cocktail_parts.append("uc.in_cart = true")
```

### 6. Frontend — API (`cocktails.ts`)
```typescript
cart:      (id: number, val: boolean) => api.post<void>(`/cocktails/${id}/cart`, { in_cart: val }),
cartCount: ()                         => api.get<{ count: number }>('/cocktails/cart'),
clearCart: ()                         => api.delete<void>('/cocktails/cart'),
```

### 7. Frontend — Hooks (`useCocktails.ts`)
- `useCart()` — same optimistic-update pattern as `useFavorite()`, toggling `c.in_cart`; on success invalidates `['cartCount']`
- `useCartCount()` — `useQuery({ queryKey: ['cartCount'], queryFn: cocktailsApi.cartCount })`; only enabled when user is logged in
- `useClearCart()` — on success invalidates `['cocktails']` and `['cartCount']`

### 8. Frontend — `CocktailCard.tsx`
Add a `ShoppingCart` (lucide-react) button in the action row, between bookmark and ingredients toggle. Only render when logged in:
```tsx
<button onClick={() => cart.mutate({ id: c.cocktail_id, val: !c.in_cart })}
  className={c.in_cart ? 'bg-amber/10 text-amber' : 'text-bark hover:text-amber hover:bg-amber/10'}>
  <ShoppingCart className={`w-4 h-4 ${c.in_cart ? 'fill-amber' : ''}`} />
</button>
```

### 9. Frontend — `Navbar.tsx`
- Import `useCartCount()` and `useAuth()`
- Render a `ShoppingCart` icon button with a count badge (only when logged in and count > 0)
- Clicking calls `onCartClick` prop → **replaces all filters** with `{ ...DEFAULT_FILTERS, cart_only: true }`

### 10. Frontend — `App.tsx` (State Lifting)
Lift `filters` + `setFilters` from `CocktailBrowser` up to `App.tsx`. Pass `setFilters` to `Navbar` as:
```typescript
onCartClick={() => setFilters({ ...DEFAULT_FILTERS, cart_only: true })}
```
Pass both down to `CocktailBrowser`. Small refactor — only these two components consume filter state.

### 11. Frontend — `CocktailBrowser.tsx`
When `filters.cart_only === true`, show a banner above the grid:
```
🛒 Viewing tonight's cart   [Clear cart]   [×]
```
- `×` and `Clear cart` both call `setFilters(DEFAULT_FILTERS)` — returning to a clean unfiltered state
- `Clear cart` additionally calls `useClearCart()` before resetting

### 12. Frontend — `FilterPanel.tsx`
Under the Favorites only / Bookmarks only checkboxes, add:
```
☐ Cart only   (auth-only, same pattern)
```
This checkbox is **additive** (AND with other active filters) — the navbar icon is the way to get a clean cart-only view.

---

## Verification
1. `alembic upgrade head` — confirm `user_cart` table created
2. Start backend: `uvicorn backend.main:app --reload --port 8000`
3. Confirm endpoints: `POST /api/cocktails/5/cart`, `GET /api/cocktails/cart`, `DELETE /api/cocktails/cart`
4. Start frontend: `npm run dev` in `frontend/`
5. Log in → cart button on cards, badge in navbar
6. Add cocktail to cart → badge increments, icon fills amber
7. Click navbar cart icon → list filters to in-cart only, banner appears
8. Dismiss banner → full list returns, badge still shows count
9. "Clear cart" → all removed, badge drops to 0
10. Log out → cart buttons and badge hidden
