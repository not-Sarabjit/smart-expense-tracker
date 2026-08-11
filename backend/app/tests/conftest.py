import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.api.main import app
from app.database.base import Base
from app.database.session import get_db


# Using a separate SQLite file for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed only for SQLite
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """
    Creates all tables before each test, yields a session,
    then drops all tables after — keeps every test isolated.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """
    Provides a FastAPI TestClient with get_db overridden
    to use the test database session instead of the real one.
    """

    def override_get_db():
        try:
            yield db
        finally:
            pass  

    app.dependency_overrides[get_db] = override_get_db  ## Use override_get_db instead of get_db in real api calls
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()