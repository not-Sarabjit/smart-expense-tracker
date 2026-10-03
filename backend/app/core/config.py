# backend/app/core/config.py
"""Application configuration.

Settings are grouped by concern. Each group is its own ``BaseSettings`` class with an
``env_prefix``, so the *environment variable names stay flat* (``DATABASE_URL``,
``QDRANT_COLLECTION``) while the *Python access path* is grouped
(``settings.database.url``, ``settings.qdrant.collection``).

Use ``get_settings()`` in new code — in FastAPI routes prefer
``settings: Settings = Depends(get_settings)`` so tests can override it.
The module-level ``settings`` object is a deprecated back-compat shim.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class _GroupSettings(BaseSettings):
    """Base for every settings group: same .env file, same tolerance for extras.

    Each group reads the environment itself, so it needs its own env_file config.
    Subclasses only declare their env_prefix (pydantic merges model_config across
    the inheritance chain).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


class AppSettings(_GroupSettings):
    """App identity and environment. Env prefix: APP_"""

    model_config = SettingsConfigDict(env_prefix="APP_")

    name: str = "Smart Expense Tracker"
    environment: Literal["dev", "test", "prod"] = "dev"
    debug: bool = False
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    # JSON log lines on the console; set APP_LOG_JSON=false for coloured dev output.
    # (logs/app.log is always JSON.)
    log_json: bool = True

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


class DatabaseSettings(_GroupSettings):
    """PostgreSQL connection and pool. Env prefix: DATABASE_"""

    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: str
    pool_size: int = 20
    max_overflow: int = 50
    pool_timeout: int = 30
    echo: bool = False


class AuthSettings(_GroupSettings):
    """JWT signing and password hashing. No env prefix (SECRET_KEY, TOKEN_ALGORITHM)."""

    secret_key: str
    token_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


class LLMSettings(_GroupSettings):
    """Chat model provider. Env prefix: LLM_  (wired up in Step 1.1)"""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    provider: str = "groq"
    model: str = "llama-3.3-70b-versatile"
    api_key: str | None = None
    temperature: float = 0.0
    timeout_seconds: int = 30
    max_retries: int = 2
    fallback_models: str = "llama-3.1-8b-instant"

    @property
    def fallback_model_list(self) -> list[str]:
        """Parsed LLM_FALLBACK_MODELS, empty names dropped, primary never duplicated."""
        names = [name.strip() for name in self.fallback_models.split(",")]
        return [name for name in names if name and name != self.model]

class EmbeddingSettings(_GroupSettings):
    """Embedding model. Env prefix: EMBEDDING_  (wired up in Step 8.6)"""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")

    provider: str = "sentence-transformers"
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 384
    batch_size: int = 32


class RedisSettings(_GroupSettings):
    """Redis. Env prefix: REDIS_  (wired up in Step 1.7)"""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = "redis://localhost:6379/0"
    max_connections: int = 20


class QdrantSettings(_GroupSettings):
    """Vector store. Env prefix: QDRANT_"""

    model_config = SettingsConfigDict(env_prefix="QDRANT_")

    url: str = "http://localhost:6333"
    api_key: str | None = None
    collection: str = "expense_docs"


class AISettings(_GroupSettings):
    """Kill switch for the whole assistant. Env prefix: AI_

    Defaults to False: a feature flag is fail-safe, so a missing env var means off.
    """

    model_config = SettingsConfigDict(env_prefix="AI_")

    enabled: bool = False


class Settings(BaseSettings):
    """Root settings object. Build it with get_settings(), not Settings() directly."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embeddings: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    ai: AISettings = Field(default_factory=AISettings)

    # ------------------------------------------------------------------
    # DEPRECATED flat aliases — kept so existing modules
    # (database/session.py, dependencies/auth.py, services/auth_service.py,
    # migrations/env.py) keep working unchanged. New code must use the groups.
    # Delete these once `grep -rn "settings\.[A-Z]" backend/` is clean.
    # ------------------------------------------------------------------
    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        return self.database.url

    @property
    def SECRET_KEY(self) -> str:  # noqa: N802
        return self.auth.secret_key

    @property
    def TOKEN_ALGORITHM(self) -> str:  # noqa: N802
        return self.auth.token_algorithm

    @property
    def QDRANT_URL(self) -> str:  # noqa: N802
        return self.qdrant.url

    @property
    def QDRANT_API_KEY(self) -> str | None:  # noqa: N802
        return self.qdrant.api_key

    @property
    def QDRANT_COLLECTION(self) -> str:  # noqa: N802
        return self.qdrant.collection


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings instance.

    Cached so the environment and .env file are parsed once. Tests call
    ``get_settings.cache_clear()`` after changing env vars, or override the
    FastAPI dependency with ``app.dependency_overrides[get_settings]``.
    """
    return Settings()


# DEPRECATED: module-level singleton kept for existing imports. Prefer get_settings().
settings = get_settings()
