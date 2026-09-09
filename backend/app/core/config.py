from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from sqlalchemy import create_engine
from typing import Literal, Optional


class Settings(BaseSettings):
  DATABASE_URL: str
  SECRET_KEY: str
  TOKEN_ALGORITHM: str

  # ─── Groq LLM ────────────────────────────────────────────────────────────
  GROQ_API_KEY: str
  GROQ_MODEL: str = "openai/gpt-oss-20b"
  GROQ_TEMPERATURE: float = 0.1
  GROQ_MAX_TOKENS: int = 2048

  # ─── Qdrant Vector Store ──────────────────────────────────────────────────
  QDRANT_URL: str = "http://localhost:6333"
  QDRANT_API_KEY: Optional[str] = None        # None, for local docker, no auth is needed
  QDRANT_COLLECTION: str = "expense_docs"

    
  model_config = ConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()