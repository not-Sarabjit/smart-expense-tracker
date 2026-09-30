from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    TOKEN_ALGORITHM: str

    # ─── Qdrant Vector Store ──────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None  # None, for local docker, no auth is needed
    QDRANT_COLLECTION: str = "expense_docs"

    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()
