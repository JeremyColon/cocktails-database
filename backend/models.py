from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    pwd: Mapped[str] = mapped_column(Text, nullable=False)

    favorites: Mapped[list["UserFavorite"]] = relationship(back_populates="user")
    bookmarks: Mapped[list["UserBookmark"]] = relationship(back_populates="user")
    ratings: Mapped[list["UserRating"]] = relationship(back_populates="user")
    cart: Mapped[list["UserCart"]] = relationship(back_populates="user")
    bar: Mapped["UserBar"] = relationship(back_populates="user", uselist=False)


class Cocktail(Base):
    __tablename__ = "cocktails"

    cocktail_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_name: Mapped[str] = mapped_column(Text, nullable=False)
    image: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(Text)
    # alcohol_type and source/scraped_at are added by migration 001
    # date_added is added by migration 002
    alcohol_type: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, default="liquor.com")
    scraped_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    date_added: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

    ingredients: Mapped[list["CocktailIngredient"]] = relationship(
        back_populates="cocktail"
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    # ingredient_id is bigint in the DB
    ingredient_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ingredient: Mapped[str] = mapped_column(Text, nullable=False)
    mapped_ingredient: Mapped[str | None] = mapped_column(Text)
    alcohol_type: Mapped[str | None] = mapped_column(Text)
    # Note: no 'unit' column on ingredients — unit lives on cocktails_ingredients

    cocktails: Mapped[list["CocktailIngredient"]] = relationship(
        back_populates="ingredient"
    )


class CocktailIngredient(Base):
    __tablename__ = "cocktails_ingredients"

    # The DB has a surrogate PK, not a composite PK
    cocktail_ingredient_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cocktail_id: Mapped[int] = mapped_column(Integer, ForeignKey("cocktails.cocktail_id"))
    ingredient_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ingredients.ingredient_id"))
    unit: Mapped[str | None] = mapped_column(Text)
    # quantity is stored as text in the DB (e.g. "1/2", "2 1/2")
    quantity: Mapped[str | None] = mapped_column(Text)

    cocktail: Mapped["Cocktail"] = relationship(back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="cocktails")


class UserFavorite(Base):
    __tablename__ = "user_favorites"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    cocktail_id: Mapped[int] = mapped_column(Integer, ForeignKey("cocktails.cocktail_id"), primary_key=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    last_updated_ts: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))

    user: Mapped["User"] = relationship(back_populates="favorites")


class UserBookmark(Base):
    __tablename__ = "user_bookmarks"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    cocktail_id: Mapped[int] = mapped_column(Integer, ForeignKey("cocktails.cocktail_id"), primary_key=True)
    bookmark: Mapped[bool] = mapped_column(Boolean, default=False)
    last_updated_ts: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))

    user: Mapped["User"] = relationship(back_populates="bookmarks")


class UserRating(Base):
    __tablename__ = "user_ratings"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    cocktail_id: Mapped[int] = mapped_column(Integer, ForeignKey("cocktails.cocktail_id"), primary_key=True)
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    last_updated_ts: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))

    user: Mapped["User"] = relationship(back_populates="ratings")


class UserCart(Base):
    __tablename__ = "user_cart"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    cocktail_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    in_cart: Mapped[bool] = mapped_column(Boolean, default=False)
    last_updated_ts: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))

    user: Mapped["User"] = relationship(back_populates="cart")


class Bar(Base):
    __tablename__ = "bars"

    bar_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ingredient_list: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), default=list)
    last_updated_ts: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))


class UserBar(Base):
    __tablename__ = "user_bar"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    bar_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bars.bar_id"))
    last_updated_ts: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))

    user: Mapped["User"] = relationship(back_populates="bar")


class BarShareToken(Base):
    __tablename__ = "bar_share_tokens"

    token: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=False))


class BarLinkInvite(Base):
    __tablename__ = "bar_link_invites"

    token: Mapped[str] = mapped_column(Text, primary_key=True)
    inviter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=False))
    accepted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=False))
