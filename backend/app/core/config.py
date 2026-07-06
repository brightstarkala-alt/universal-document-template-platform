"""
Centralized application settings.

All configuration MUST be read through this module (via the `settings`
singleton) instead of calling `os.environ` directly elsewhere in the
codebase. This keeps env-var handling, validation, and defaults in one
auditable place.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- General ---
    PROJECT_NAME: str = "Universal Document Template Platform"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development")  # development | staging | production
    LOG_LEVEL: str = Field(default="INFO")
    API_V1_PREFIX: str = "/api/v1"

    # --- CORS ---
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Supabase (used starting in the Authentication / Database modules) ---
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # --- Storage (Module 4: Storage Foundation) ---
    STORAGE_BUCKET_NAME: str = "documents"
    MAX_UPLOAD_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    SIGNED_URL_EXPIRES_IN_SECONDS: int = 300

    # --- OpenAI (Module 7: AI Field Extraction) ---
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_EXTRACTION_UNIT_BATCH_CHAR_BUDGET: int = 8000
    """Rough token-budget proxy: units are grouped into one OpenAI call
    until their serialized candidate+context payload would exceed this many
    characters, so a large document is chunked instead of sent as one huge
    prompt."""

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — Settings() is only ever constructed once."""
    return Settings()


settings = get_settings()
