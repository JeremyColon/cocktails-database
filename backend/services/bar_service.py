"""
Bar service — replaces get_available_cocktails() and my_bar_outputs() from helpers.py.
All matching is done at the mapped_ingredient level so that adding "mint" covers
mint leaves, mint sprigs, etc. without requiring each variant to be added separately.

Schema note: ingredient lists now live in the `bars` table (bar_id PK). user_bar is a
thin user_id → bar_id mapping. Multiple users can share the same bar_id (household mode).
"""
import secrets
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas import (
    AcceptLinkRequest,
    BarIngredient,
    BarLinkPreview,
    BarLinkStatus,
    BarResponse,
    BarSharePreview,
    BarStatsResponse,
    LinkInviteResponse,
    MissingIngredient,
    ShareTokenResponse,
    StarterIngredient,
    StarterKit,
    StartersResponse,
    TopStarterIngredient,
)

# Reusable CTE: mapped_ingredient values the user has in their bar (via bars table)
_MY_BAR_MAPPED_CTE = """
    my_bar_mapped AS (
        SELECT DISTINCT COALESCE(i.mapped_ingredient, i.ingredient) AS mapped_name
        FROM user_bar ub
        JOIN bars b ON b.bar_id = ub.bar_id
        CROSS JOIN LATERAL unnest(b.ingredient_list) AS ing_id
        JOIN ingredients i ON i.ingredient_id = ing_id
        WHERE ub.user_id = :user_id
    )
"""


async def _get_or_create_bar_id(user_id: int, db: AsyncSession) -> int:
    """Returns the bar_id for a user, creating a bars row + user_bar row if needed."""
    row = (await db.execute(
        text("SELECT bar_id FROM user_bar WHERE user_id = :uid"),
        {"uid": user_id},
    )).scalar_one_or_none()

    if row is not None:
        return row

    bar_id = (await db.execute(
        text("INSERT INTO bars (ingredient_list, last_updated_ts) VALUES ('{}', now()) RETURNING bar_id"),
    )).scalar_one()

    await db.execute(
        text("INSERT INTO user_bar (user_id, bar_id, last_updated_ts) VALUES (:uid, :bar_id, now())"),
        {"uid": user_id, "bar_id": bar_id},
    )
    return bar_id


async def get_bar(user_id: int, db: AsyncSession) -> BarResponse:
    sql = """
        WITH bar_ids AS (
            SELECT unnest(b.ingredient_list) AS ingredient_id
            FROM user_bar ub
            JOIN bars b ON b.bar_id = ub.bar_id
            WHERE ub.user_id = :user_id
        )
        SELECT DISTINCT ON (COALESCE(i.mapped_ingredient, i.ingredient))
            i.ingredient_id, i.ingredient, i.mapped_ingredient, i.alcohol_type
        FROM ingredients i
        JOIN bar_ids ON i.ingredient_id = bar_ids.ingredient_id
        ORDER BY COALESCE(i.mapped_ingredient, i.ingredient)
    """
    rows = (await db.execute(text(sql), {"user_id": user_id})).mappings().all()
    return BarResponse(
        ingredients=[
            BarIngredient(
                ingredient_id=r["ingredient_id"],
                ingredient=r["ingredient"],
                mapped_ingredient=r["mapped_ingredient"],
                alcohol_type=r["alcohol_type"],
            )
            for r in rows
        ]
    )


async def set_bar(user_id: int, ingredient_ids: list[int], db: AsyncSession) -> None:
    """Full replacement of the bar's ingredient list."""
    bar_id = await _get_or_create_bar_id(user_id, db)
    await db.execute(
        text("UPDATE bars SET ingredient_list = :ingredient_list, last_updated_ts = now() WHERE bar_id = :bar_id"),
        {"ingredient_list": ingredient_ids, "bar_id": bar_id},
    )
    await db.commit()


async def add_to_bar(user_id: int, ingredient_ids: list[int], db: AsyncSession) -> None:
    bar_id = await _get_or_create_bar_id(user_id, db)
    await db.execute(
        text("""
            UPDATE bars SET
                ingredient_list = (
                    SELECT array_agg(DISTINCT x)
                    FROM unnest(ingredient_list || :ingredient_list) x
                ),
                last_updated_ts = now()
            WHERE bar_id = :bar_id
        """),
        {"ingredient_list": ingredient_ids, "bar_id": bar_id},
    )
    await db.commit()


async def remove_from_bar(user_id: int, ingredient_ids: list[int], db: AsyncSession) -> None:
    # Remove all IDs that share the same mapped_ingredient as any of the given IDs,
    # so removing "mint" clears mint leaves, mint sprigs, etc. in one go.
    bar_id = await _get_or_create_bar_id(user_id, db)
    await db.execute(
        text("""
            WITH mapped_to_remove AS (
                SELECT DISTINCT COALESCE(i1.mapped_ingredient, i1.ingredient) AS mapped_name
                FROM ingredients i1
                WHERE i1.ingredient_id = ANY(:remove_ids)
            ),
            ids_to_remove AS (
                SELECT i2.ingredient_id
                FROM ingredients i2
                JOIN mapped_to_remove ON COALESCE(i2.mapped_ingredient, i2.ingredient) = mapped_to_remove.mapped_name
            ),
            kept AS (
                SELECT COALESCE(array_agg(x), ARRAY[]::bigint[]) AS new_list
                FROM unnest((SELECT ingredient_list FROM bars WHERE bar_id = :bar_id)) x
                WHERE x NOT IN (SELECT ingredient_id FROM ids_to_remove)
            )
            UPDATE bars
            SET ingredient_list = (SELECT new_list FROM kept),
                last_updated_ts = now()
            WHERE bar_id = :bar_id
        """),
        {"remove_ids": ingredient_ids, "bar_id": bar_id},
    )
    await db.commit()


async def get_bar_stats(
    user_id: int, db: AsyncSession, include_garnish: bool = True
) -> BarStatsResponse:
    garnish_filter = "" if include_garnish else "AND ci.unit != 'garnish'"

    stats_sql = f"""
        WITH {_MY_BAR_MAPPED_CTE},
        cocktail_totals AS (
            SELECT
                ci.cocktail_id,
                COUNT(*) FILTER (WHERE ci.unit != 'garnish' OR :include_garnish)   AS total_needed,
                COUNT(*) FILTER (WHERE mb.mapped_name IS NOT NULL
                                 AND (ci.unit != 'garnish' OR :include_garnish))    AS have_count
            FROM cocktails_ingredients ci
            JOIN ingredients i ON ci.ingredient_id = i.ingredient_id
            LEFT JOIN my_bar_mapped mb
                   ON COALESCE(i.mapped_ingredient, i.ingredient) = mb.mapped_name
            {garnish_filter}
            GROUP BY ci.cocktail_id
        )
        SELECT
            SUM(CASE WHEN have_count = total_needed THEN 1 ELSE 0 END) AS can_make_count,
            SUM(CASE WHEN have_count > 0 AND have_count < total_needed THEN 1 ELSE 0 END) AS partial_count,
            SUM(CASE WHEN have_count = 0 THEN 1 ELSE 0 END) AS cannot_make_count
        FROM cocktail_totals
    """

    stats_row = (
        await db.execute(
            text(stats_sql), {"user_id": user_id, "include_garnish": include_garnish}
        )
    ).mappings().one()

    missing_sql = f"""
        WITH {_MY_BAR_MAPPED_CTE},
        missing_mapped AS (
            SELECT DISTINCT
                COALESCE(i.mapped_ingredient, i.ingredient) AS mapped_name,
                ci.cocktail_id
            FROM cocktails_ingredients ci
            JOIN ingredients i ON ci.ingredient_id = i.ingredient_id
            LEFT JOIN my_bar_mapped mb
                   ON COALESCE(i.mapped_ingredient, i.ingredient) = mb.mapped_name
            WHERE mb.mapped_name IS NULL
            {garnish_filter}
        )
        SELECT
            MIN(i.ingredient_id) AS ingredient_id,
            mm.mapped_name       AS mapped_ingredient,
            COUNT(DISTINCT mm.cocktail_id) AS cocktail_count
        FROM missing_mapped mm
        JOIN ingredients i ON COALESCE(i.mapped_ingredient, i.ingredient) = mm.mapped_name
        GROUP BY mm.mapped_name
        ORDER BY cocktail_count DESC
        LIMIT 9
    """

    missing_rows = (
        await db.execute(text(missing_sql), {"user_id": user_id})
    ).mappings().all()

    return BarStatsResponse(
        can_make_count=stats_row["can_make_count"] or 0,
        partial_count=stats_row["partial_count"] or 0,
        cannot_make_count=stats_row["cannot_make_count"] or 0,
        top_missing=[
            MissingIngredient(
                ingredient_id=r["ingredient_id"],
                mapped_ingredient=r["mapped_ingredient"],
                cocktail_count=r["cocktail_count"],
            )
            for r in missing_rows
        ],
    )


_STARTER_KITS: list[dict] = [
    {
        "name": "Base Spirits",
        "tags": ["vodka", "gin", "bourbon", "rum", "tequila", "scotch whisky", "rye whiskey", "brandy"],
    },
    {
        "name": "Citrus & Fresh",
        "tags": ["lemon juice", "lime juice", "orange juice", "grapefruit juice", "simple syrup"],
    },
    {
        "name": "Bitters & Vermouth",
        "tags": ["angostura bitters", "sweet vermouth", "dry vermouth", "orange bitters", "peychaud's bitters"],
    },
    {
        "name": "Syrups & Liqueurs",
        "tags": ["simple syrup", "triple sec", "grenadine", "cointreau", "campari", "aperol", "amaretto"],
    },
]


async def get_starters(db: AsyncSession) -> StartersResponse:
    all_tags = list({tag.lower() for kit in _STARTER_KITS for tag in kit["tags"]})
    resolved_rows = (await db.execute(
        text("""
            SELECT DISTINCT ON (lower(mapped_ingredient))
                ingredient_id, mapped_ingredient, alcohol_type
            FROM ingredients
            WHERE lower(mapped_ingredient) = ANY(:names)
            ORDER BY lower(mapped_ingredient)
        """),
        {"names": all_tags},
    )).mappings().all()

    lookup: dict[str, dict] = {r["mapped_ingredient"].lower(): dict(r) for r in resolved_rows}

    kits = []
    for kit in _STARTER_KITS:
        ingredients = []
        for tag in kit["tags"]:
            row = lookup.get(tag.lower())
            if row:
                ingredients.append(StarterIngredient(
                    ingredient_id=row["ingredient_id"],
                    mapped_ingredient=row["mapped_ingredient"],
                    alcohol_type=row["alcohol_type"],
                ))
        kits.append(StarterKit(name=kit["name"], ingredients=ingredients))

    top_rows = (await db.execute(text("""
        SELECT
            MIN(i.ingredient_id)   AS ingredient_id,
            i.mapped_ingredient,
            MIN(i.alcohol_type)    AS alcohol_type,
            COUNT(DISTINCT ci.cocktail_id) AS cocktail_count
        FROM cocktails_ingredients ci
        JOIN ingredients i ON i.ingredient_id = ci.ingredient_id
        WHERE i.mapped_ingredient IS NOT NULL
          AND ci.unit != 'garnish'
        GROUP BY i.mapped_ingredient
        ORDER BY cocktail_count DESC
        LIMIT 20
    """))).mappings().all()

    return StartersResponse(
        kits=kits,
        top_ingredients=[
            TopStarterIngredient(
                ingredient_id=r["ingredient_id"],
                mapped_ingredient=r["mapped_ingredient"],
                alcohol_type=r["alcohol_type"],
                cocktail_count=r["cocktail_count"],
            )
            for r in top_rows
        ],
    )


# ── Bar share (one-time snapshot) ─────────────────────────────────────────────

async def create_share_token(user_id: int, db: AsyncSession) -> ShareTokenResponse:
    """Generate a fresh 7-day share token. Replaces any existing token for this user."""
    token = secrets.token_urlsafe(12)
    expires_at = datetime.utcnow() + timedelta(days=7)
    await db.execute(
        text("DELETE FROM bar_share_tokens WHERE user_id = :uid"),
        {"uid": user_id},
    )
    await db.execute(
        text("INSERT INTO bar_share_tokens (token, user_id, expires_at) VALUES (:token, :uid, :expires_at)"),
        {"token": token, "uid": user_id, "expires_at": expires_at},
    )
    await db.commit()
    return ShareTokenResponse(token=token, expires_at=expires_at)


async def get_share_preview(token: str, db: AsyncSession) -> BarSharePreview | None:
    row = (await db.execute(
        text("""
            SELECT bst.user_id, bst.expires_at, u.email
            FROM bar_share_tokens bst
            JOIN users u ON u.id = bst.user_id
            WHERE bst.token = :token AND bst.expires_at > now()
        """),
        {"token": token},
    )).mappings().one_or_none()

    if not row:
        return None

    bar = await get_bar(row["user_id"], db)
    return BarSharePreview(
        owner_email=row["email"],
        ingredient_count=len(bar.ingredients),
        ingredients=[
            StarterIngredient(
                ingredient_id=i.ingredient_id,
                mapped_ingredient=i.mapped_ingredient or i.ingredient,
                alcohol_type=i.alcohol_type,
            )
            for i in bar.ingredients
        ],
        expires_at=row["expires_at"],
    )


async def import_shared_bar(
    token: str, user_id: int, mode: str, db: AsyncSession
) -> BarResponse | None:
    row = (await db.execute(
        text("SELECT user_id FROM bar_share_tokens WHERE token = :token AND expires_at > now()"),
        {"token": token},
    )).mappings().one_or_none()

    if not row:
        return None

    source_bar = await get_bar(row["user_id"], db)
    source_ids = [i.ingredient_id for i in source_bar.ingredients]

    if mode == "replace":
        await set_bar(user_id, source_ids, db)
    else:
        await add_to_bar(user_id, source_ids, db)

    return await get_bar(user_id, db)


# ── Household bar linking ──────────────────────────────────────────────────────

async def create_link_invite(user_id: int, db: AsyncSession) -> LinkInviteResponse:
    """Generate a 7-day household link invite. Replaces any pending invite from this user."""
    token = secrets.token_urlsafe(12)
    expires_at = datetime.utcnow() + timedelta(days=7)

    await db.execute(
        text("DELETE FROM bar_link_invites WHERE inviter_id = :uid AND accepted_at IS NULL"),
        {"uid": user_id},
    )
    await db.execute(
        text("INSERT INTO bar_link_invites (token, inviter_id, expires_at) VALUES (:token, :uid, :expires_at)"),
        {"token": token, "uid": user_id, "expires_at": expires_at},
    )
    await db.commit()
    return LinkInviteResponse(token=token, expires_at=expires_at)


async def get_link_preview(token: str, db: AsyncSession) -> BarLinkPreview | None:
    row = (await db.execute(
        text("""
            SELECT u.email
            FROM bar_link_invites bli
            JOIN users u ON u.id = bli.inviter_id
            WHERE bli.token = :token
              AND bli.expires_at > now()
              AND bli.accepted_at IS NULL
        """),
        {"token": token},
    )).mappings().one_or_none()

    return BarLinkPreview(inviter_email=row["email"]) if row else None


async def accept_link_invite(
    token: str, user_id: int, mode: str, db: AsyncSession
) -> bool:
    """
    Link acceptor's bar to inviter's bar.
    mode='merge': union acceptor's unique ingredients into inviter's bar first.
    mode='replace': adopt inviter's bar as-is.
    Returns False if token is invalid/expired/already accepted.
    """
    row = (await db.execute(
        text("""
            SELECT bli.inviter_id, ub.bar_id AS inviter_bar_id
            FROM bar_link_invites bli
            JOIN user_bar ub ON ub.user_id = bli.inviter_id
            WHERE bli.token = :token
              AND bli.expires_at > now()
              AND bli.accepted_at IS NULL
        """),
        {"token": token},
    )).mappings().one_or_none()

    if not row:
        return False

    inviter_bar_id = row["inviter_bar_id"]

    acceptor_bar_id = (await db.execute(
        text("SELECT bar_id FROM user_bar WHERE user_id = :uid"),
        {"uid": user_id},
    )).scalar_one_or_none()

    # Prevent linking to own bar (already in the same household)
    if acceptor_bar_id == inviter_bar_id:
        return False

    if mode == "merge" and acceptor_bar_id is not None:
        # Union: add acceptor's unique ingredients into inviter's bar
        await db.execute(
            text("""
                WITH acceptor_ingredients AS (
                    SELECT ingredient_list FROM bars WHERE bar_id = :acceptor_bar_id
                ),
                merged AS (
                    SELECT array_agg(DISTINCT x) AS new_list
                    FROM unnest(
                        (SELECT ingredient_list FROM bars WHERE bar_id = :inviter_bar_id)
                        || CAST((SELECT ingredient_list FROM acceptor_ingredients) AS bigint[])
                    ) x
                )
                UPDATE bars SET
                    ingredient_list = (SELECT new_list FROM merged),
                    last_updated_ts = now()
                WHERE bar_id = :inviter_bar_id
            """),
            {"inviter_bar_id": inviter_bar_id, "acceptor_bar_id": acceptor_bar_id},
        )

    # Soft-delete acceptor's old bar
    if acceptor_bar_id is not None:
        await db.execute(
            text("UPDATE bars SET deleted_at = now() WHERE bar_id = :bar_id"),
            {"bar_id": acceptor_bar_id},
        )

    # Point acceptor's user_bar to inviter's bar
    await db.execute(
        text("""
            INSERT INTO user_bar (user_id, bar_id, last_updated_ts)
            VALUES (:user_id, :bar_id, now())
            ON CONFLICT (user_id) DO UPDATE SET bar_id = :bar_id, last_updated_ts = now()
        """),
        {"user_id": user_id, "bar_id": inviter_bar_id},
    )

    # Mark invite as accepted (but keep it so the inviter can still use it for others)
    await db.execute(
        text("UPDATE bar_link_invites SET accepted_at = now() WHERE token = :token"),
        {"token": token},
    )

    await db.commit()
    return True


async def unlink_bar(user_id: int, db: AsyncSession) -> None:
    """Detach user from shared bar and give them a new empty bar."""
    new_bar_id = (await db.execute(
        text("INSERT INTO bars (ingredient_list, last_updated_ts) VALUES ('{}', now()) RETURNING bar_id"),
    )).scalar_one()

    await db.execute(
        text("UPDATE user_bar SET bar_id = :bar_id, last_updated_ts = now() WHERE user_id = :uid"),
        {"bar_id": new_bar_id, "uid": user_id},
    )
    await db.commit()


async def get_link_status(user_id: int, db: AsyncSession) -> BarLinkStatus:
    bar_id = (await db.execute(
        text("SELECT bar_id FROM user_bar WHERE user_id = :uid"),
        {"uid": user_id},
    )).scalar_one_or_none()

    if bar_id is None:
        return BarLinkStatus(linked=False, linked_to_emails=[], household_size=1)

    members = (await db.execute(
        text("""
            SELECT u.email, ub.user_id
            FROM user_bar ub
            JOIN users u ON u.id = ub.user_id
            WHERE ub.bar_id = :bar_id
        """),
        {"bar_id": bar_id},
    )).mappings().all()

    others = [m["email"] for m in members if m["user_id"] != user_id]
    return BarLinkStatus(
        linked=len(others) > 0,
        linked_to_emails=others,
        household_size=len(members),
    )
