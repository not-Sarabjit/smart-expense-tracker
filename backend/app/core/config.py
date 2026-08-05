from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from sqlalchemy import create_engine



class Settings(BaseSettings):
  DATABASE_URL: str
  SECRET_KEY: str
  TOKEN_ALGORITHM: str
  
  model_config = ConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()