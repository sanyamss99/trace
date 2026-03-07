from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "postgresql+asyncpg://localhost:5432/trace"
    log_level: str = "DEBUG"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    trust_proxy_headers: bool = False

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # JWT
    jwt_secret: str = "change-me-in-production"

    # Frontend URL for OAuth redirect
    frontend_url: str = "http://localhost:5173"

    @property
    def is_debug(self) -> bool:
        """Return True when running in debug/development mode."""
        return self.log_level.upper() == "DEBUG"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """Reject the default JWT secret in production."""
        if not self.is_debug and self.jwt_secret == "change-me-in-production":
            raise ValueError(
                "JWT_SECRET must be set to a secure value in production "
                "(LOG_LEVEL != DEBUG)"
            )
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
