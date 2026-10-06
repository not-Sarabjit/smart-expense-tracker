import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.database.base import Base
from app.database.session import get_db
from app.dependencies.agent import get_agent_graph
from app.dependencies.features import require_ai_enabled
from app.dependencies.llm import get_title_llm

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

    app.dependency_overrides[get_db] = (
        override_get_db  ## Use override_get_db instead of get_db in real api calls
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register_and_login(client, email, password="TestPass123!"):
    """Helper: registers a user and returns their auth headers."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "first_name": "Test",
            "last_name": "User",
            "password": password,
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_a_headers(client):
    return register_and_login(client, "usera@example.com")


@pytest.fixture
def user_b_headers(client):
    return register_and_login(client, "userb@example.com")


@pytest.fixture
def category_id(client, user_a_headers):
    """Creates an expense category for user A to attach transactions to."""
    response = client.post(
        "/api/v1/categories/create_category",
        json={"name": "Groceries", "category_type": "expense"},
        headers=user_a_headers,
    )
    return response.json()["id"]


@pytest.fixture
def income_category_id(client, user_a_headers):
    """Creates an income category for user A."""
    response = client.post(
        "/api/v1/categories/create_category",
        json={"name": "Paycheck", "category_type": "income"},
        headers=user_a_headers,
    )
    return response.json()["id"]

class FakeGraph:
    """Minimal stand-in for a compiled LangGraph: only `astream` is used."""

    def __init__(self, pieces: list[str], usage: dict | None = None):
        self.pieces = pieces
        self.usage = usage or {
            "input_tokens": 11,
            "output_tokens": 3,
            "total_tokens": 14,
        }
        self.calls: list = []

    async def astream(self, state, *, context=None, stream_mode=None, **kwargs):
        self.calls.append((state, context, stream_mode))
        meta = {"langgraph_node": "agent"}
        for index, piece in enumerate(self.pieces):
            last = index == len(self.pieces) - 1
            yield (
                AIMessageChunk(
                    content=piece,
                    usage_metadata=self.usage if last else None,
                    response_metadata={"model_name": "fake-model"} if last else {},
                ),
                meta,
            )


class FakeTitleModel:
    def __init__(self, title: str = "Groceries in September"):
        self.title = title
        self.calls = 0

    async def ainvoke(self, messages, **kwargs):
        self.calls += 1
        return AIMessage(content=f'"{self.title}."')


@pytest.fixture
def fake_graph():
    graph = FakeGraph(["Hello", " there", "!"])
    app.dependency_overrides[require_ai_enabled] = lambda: None
    app.dependency_overrides[get_agent_graph] = lambda: graph
    yield graph
    app.dependency_overrides.pop(require_ai_enabled, None)
    app.dependency_overrides.pop(get_agent_graph, None)


@pytest.fixture
def fake_title_model():
    model = FakeTitleModel()
    app.dependency_overrides[get_title_llm] = lambda: model
    yield model
    app.dependency_overrides.pop(get_title_llm, None)
