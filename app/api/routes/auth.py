from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import Settings, get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, RegisterRequest, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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


@router.post("/token", response_model=AccessTokenResponse)
async def issue_token(
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
    return AccessTokenResponse(access_token=create_access_token(user.id, settings))


@router.get("/me", response_model=UserResponse)
async def read_current_user(user: CurrentUser) -> User:
    return user
