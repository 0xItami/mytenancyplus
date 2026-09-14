from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import Settings, get_settings
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.sessions import (
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
    create_refresh_session,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[rate_limit("auth-register", requests=10)],
)
async def register(payload: RegisterRequest, session: DatabaseSession) -> User:
    email = payload.email.lower()
    if await session.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post(
    "/token",
    response_model=AccessTokenResponse,
    dependencies=[rate_limit("auth-token", requests=20)],
)
async def issue_token(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AccessTokenResponse:
    user = await session.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _, refresh_token = create_refresh_session(
        session,
        user_id=user.id,
        settings=settings,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return AccessTokenResponse(
        access_token=create_access_token(user.id, settings),
        refresh_token=refresh_token,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    dependencies=[rate_limit("auth-refresh", requests=30)],
)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    request: Request,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AccessTokenResponse:
    try:
        refresh_session, refresh_token = await rotate_refresh_token(
            session,
            token=payload.refresh_token,
            settings=settings,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client else None,
        )
    except RefreshTokenReuseError as exc:
        raise HTTPException(
            status_code=401, detail="Session reuse detected; family revoked"
        ) from exc
    except InvalidRefreshTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    return AccessTokenResponse(
        access_token=create_access_token(refresh_session.user_id, settings),
        refresh_token=refresh_token,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, session: DatabaseSession) -> None:
    await revoke_refresh_token(session, payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def read_current_user(user: CurrentUser) -> User:
    return user
