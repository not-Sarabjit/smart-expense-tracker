from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Creating an engine to connect to database
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=50,
    pool_timeout=30)

# Creating a session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# Generator function to get a session , Used by Fastapi Database calls
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

