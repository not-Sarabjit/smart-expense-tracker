from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from sqlalchemy import create_engine
from typing import Literal


class Settings(BaseSettings):
  DATABASE_URL: str
  SECRET_KEY: str
  TOKEN_ALGORITHM: str

  AI_PROVIDER: Literal["groq", "openai"] = "groq"
  AI_MODEL: str = 'groq'
  AI_API_KEY: str = ''
  AI_MAX_TOKENS: int = 1024
  AI_TEMPERATURE: float = 0.2

    
  model_config = ConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()