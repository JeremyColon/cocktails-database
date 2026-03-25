from pydantic import BaseModel, EmailStr, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}


# ── Ingredients ───────────────────────────────────────────────────────────────

class IngredientOut(BaseModel):
    ingredient_id: int
    ingredient: str
    mapped_ingredient: str | None
    alcohol_type: str | None
    unit: str | None

    model_config = {"from_attributes": True}


# ── Cocktails ─────────────────────────────────────────────────────────────────

class CocktailIngredientOut(BaseModel):
    ingredient_id: int
    ingredient: str
    mapped_ingredient: str | None
    unit: str | None
    quantity: str | None
    in_bar: bool = False

    model_config = {"from_attributes": True}


class CocktailOut(BaseModel):
    cocktail_id: int
    recipe_name: str
    image: str | None
    link: str | None
    alcohol_type: str | None
    nps: float
    avg_rating: float
    num_ratings: int
    favorited: bool
    bookmarked: bool
    user_rating: int | None
    ingredients: list[CocktailIngredientOut] = []

    model_config = {"from_attributes": True}


class CocktailListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[CocktailOut]


class CocktailFilterParams(BaseModel):
    # Text search
    search: str | None = None

    # Filters
    liquor_types: list[str] | None = None
    ingredients: list[str] | None = None       # mapped_ingredient names (AND)
    ingredients_or: list[str] | None = None    # mapped_ingredient names (OR)
    garnishes: list[str] | None = None
    bitters: list[str] | None = None
    syrups: list[str] | None = None
    other: list[str] | None = None

    # NPS range
    nps_min: float | None = None
    nps_max: float | None = None

    # User preference filters (require auth)
    favorites_only: bool = False
    bookmarks_only: bool = False

    # Bar ingredient availability
    can_make: str | None = None  # "all" | "some" | "none"
    include_garnish: bool = True

    # Sorting
    sort_by: str = "recipe_name"   # recipe_name | nps | avg_rating
    sort_dir: str = "asc"          # asc | desc

    # Pagination
    page: int = 1
    page_size: int = 24

    @field_validator("page_size")
    @classmethod
    def clamp_page_size(cls, v: int) -> int:
        return max(1, min(v, 100))

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        allowed = {"recipe_name", "nps", "avg_rating", "num_ratings"}
        if v not in allowed:
            raise ValueError(f"sort_by must be one of {allowed}")
        return v

    @field_validator("sort_dir")
    @classmethod
    def validate_sort_dir(cls, v: str) -> str:
        if v not in {"asc", "desc"}:
            raise ValueError("sort_dir must be 'asc' or 'desc'")
        return v


# ── User preferences ──────────────────────────────────────────────────────────

class FavoriteRequest(BaseModel):
    favorite: bool

class BookmarkRequest(BaseModel):
    bookmark: bool

class RatingRequest(BaseModel):
    rating: int

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if not (0 <= v <= 10):
            raise ValueError("Rating must be between 0 and 10")
        return v


# ── Bar ───────────────────────────────────────────────────────────────────────

class BarIngredient(BaseModel):
    ingredient_id: int
    ingredient: str
    mapped_ingredient: str | None
    alcohol_type: str | None

class BarResponse(BaseModel):
    ingredients: list[BarIngredient]

class BarUpdateRequest(BaseModel):
    ingredient_ids: list[int]   # full replacement list

class BarAddRequest(BaseModel):
    ingredient_ids: list[int]   # ids to add

class BarRemoveRequest(BaseModel):
    ingredient_ids: list[int]   # ids to remove

class MissingIngredient(BaseModel):
    ingredient_id: int
    mapped_ingredient: str
    cocktail_count: int         # how many cocktails this would unlock

class BarStatsResponse(BaseModel):
    can_make_count: int
    partial_count: int
    cannot_make_count: int
    top_missing: list[MissingIngredient]
