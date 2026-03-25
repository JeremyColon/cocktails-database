import dns.resolver
import disposable_email_domains
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.dependencies import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.models import User
from backend.schemas import LoginRequest, RegisterRequest, UserResponse


def _validate_email_domain(email: str) -> None:
    domain = email.split("@")[-1].lower()

    if domain in disposable_email_domains.blocklist:
        raise HTTPException(status_code=400, detail="Disposable email addresses are not allowed")

    try:
        dns.resolver.resolve(domain, "MX")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        raise HTTPException(status_code=400, detail="Email domain does not appear to be valid")
    except Exception:
        # DNS timeout or other transient error — let it through rather than blocking legitimate signups
        pass

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "is_admin": user.id == settings.admin_user_id,
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    _validate_email_domain(body.email)

    result = await db.execute(select(User).where(User.email == body.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=body.email.lower(), pwd=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _user_response(user)


@router.post("/login", response_model=UserResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.pwd):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        max_age=60 * 60,  # 1 hour, matches token expiry
    )
    return _user_response(user)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return _user_response(user)


@router.put("/password")
async def change_password(
    body: RegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    target = result.scalar_one_or_none()
    if not target or target.id != user.id:
        raise HTTPException(status_code=404, detail="User not found")

    target.pwd = hash_password(body.password)
    await db.commit()
    return {"detail": "Password updated"}
