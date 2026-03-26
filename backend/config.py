from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database — accepts a full URL or individual parts from the existing env vars
    database_url: str = ""
    cocktails_host: str = "localhost"
    cocktails_port: int = 5432
    cocktails_user: str = "postgres"
    cocktails_pwd: str = ""
    cocktails_db: str = "cocktails"

    # JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    # Set to False in local dev (HTTP). Set to True in production (HTTPS).
    secure_cookies: bool = False

    # User ID with admin privileges (ingredient mapping, etc.)
    admin_user_id: int = 1

    # CORS — comma-separated string or JSON list of allowed origins.
    # Example: ALLOWED_ORIGINS="https://your-app.herokuapp.com"
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:8000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # Redis (optional — caching disabled if not set)
    redis_url: str = ""

    @property
    def async_database_url(self) -> str:
        if self.database_url and self.database_url.startswith(("postgresql", "postgres")):
            # Replace postgres:// or postgresql:// with the asyncpg driver
            return self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            ).replace("postgres://", "postgresql+asyncpg://")
        return (
            f"postgresql+asyncpg://{self.cocktails_user}:{self.cocktails_pwd}"
            f"@{self.cocktails_host}:{self.cocktails_port}/{self.cocktails_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Used by Alembic (sync driver)."""
        if self.database_url and self.database_url.startswith(("postgresql", "postgres")):
            return self.database_url.replace(
                "postgresql+asyncpg://", "postgresql://"
            )
        return (
            f"postgresql://{self.cocktails_user}:{self.cocktails_pwd}"
            f"@{self.cocktails_host}:{self.cocktails_port}/{self.cocktails_db}"
        )


settings = Settings()
