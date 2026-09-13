from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_is_hashed_and_verifiable() -> None:
    encoded = hash_password("a-strong-password")
    assert encoded != "a-strong-password"
    assert verify_password("a-strong-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_access_token_round_trip() -> None:
    settings = Settings(environment="test", jwt_secret="test-secret-with-at-least-32-bytes")
    user_id = uuid4()
    assert decode_access_token(create_access_token(user_id, settings), settings) == user_id


def test_access_token_rejects_wrong_secret() -> None:
    user_id = uuid4()
    first = Settings(environment="test", jwt_secret="first-secret-with-at-least-32-bytes")
    second = Settings(environment="test", jwt_secret="second-secret-with-at-least-32-bytes")
    token = create_access_token(user_id, first)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, second)
