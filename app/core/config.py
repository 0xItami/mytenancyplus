from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MTP_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "MyTenancyPlus"
    environment: Literal["local", "test", "staging", "production"] = "local"
    database_url: str = (
        "postgresql+asyncpg://mytenancyplus:mytenancyplus@localhost:5432/mytenancyplus"
    )
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "local-development-secret-change-me"
    access_token_ttl_minutes: int = Field(default=30, ge=5, le=1440)
    cors_origins: list[str] = ["http://localhost:3000"]

    @model_validator(mode="after")
    def reject_unsafe_production_secret(self) -> "Settings":
        if self.environment in {"staging", "production"} and len(self.jwt_secret) < 32:
            raise ValueError("MTP_JWT_SECRET must contain at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
