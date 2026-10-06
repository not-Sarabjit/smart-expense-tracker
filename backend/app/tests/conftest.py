import socket
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai.agent.graph import build_graph
from app.api.main import app
from app.database.base import Base
from app.database.session import get_db
from app.dependencies.agent import get_agent_graph
from app.dependencies.features import require_ai_enabled
from app.dependencies.llm import get_title_llm
from app.tests.fakes import FakeGraph, FakeTitleModel, ScriptedChatModel

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


# ---------------------------------------------------------------------------
# Step 1.8 — fake LLMs behind the REAL graph
# ---------------------------------------------------------------------------

_LOOPBACK = {"127.0.0.1", "::1", "localhost", "", "0.0.0.0"}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Make any outbound TCP connection fail loudly.

    Without this, a dependency someone forgot to override does not fail — it
    quietly calls a real provider, and the suite becomes slow, flaky and
    dependent on a key. Loopback stays open (a local Postgres, a debugger), as
    do non-IP sockets (AF_UNIX, socketpair) that asyncio and httpx use
    internally.
    """
    real_connect = socket.socket.connect

    def guarded(self, address, *args, **kwargs):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            host = address[0] if isinstance(address, tuple) else address
            if str(host) not in _LOOPBACK:
                raise RuntimeError(
                    f"Blocked outbound connection to {host!r}: tests must not use the network. "
                    "Override the dependency with a fake (see app/tests/fakes.py)."
                )
        return real_connect(self, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded)


@pytest.fixture
def ai_enabled():
    """Open the chat router (AI_ENABLED is false for the whole suite)."""
    app.dependency_overrides[require_ai_enabled] = lambda: None
    yield
    app.dependency_overrides.pop(require_ai_enabled, None)


@dataclass
class InstalledLLM:
    """What `scripted_llm` hands back: the fakes now wired into the app."""

    agent: BaseChatModel
    title: BaseChatModel
    graph: Runnable


@pytest.fixture
def scripted_llm(ai_enabled):
    """Install a fake chat model behind the **real** compiled graph.

    `fake_graph` replaces the graph itself; this replaces only the model, so
    `build_graph`, the agent node, `prepare_turn`, the prompt loader, history
    replay and `stream_turn` all run for real. That is the layer where the
    network begins, which makes it the right place to cut.

    Call the fixture to install::

        llm = scripted_llm(["Hi there"], usage=None)
    """

    def install(
        responses: list[Any] | None = None,
        *,
        model: BaseChatModel | Runnable | None = None,
        title: str | None = "Groceries in September",
        **kwargs: Any,
    ) -> InstalledLLM:
        agent_model = (
            model
            if model is not None
            else ScriptedChatModel(
                responses=list(responses) if responses else ["Hello there friend"], **kwargs
            )
        )
        graph = build_graph(agent_model)
        title_model = ScriptedChatModel(responses=[f'"{title}."'], usage=None)

        app.dependency_overrides[get_agent_graph] = lambda: graph
        app.dependency_overrides[get_title_llm] = lambda: title_model

        return InstalledLLM(agent=agent_model, title=title_model, graph=graph)

    yield install

    app.dependency_overrides.pop(get_agent_graph, None)
    app.dependency_overrides.pop(get_title_llm, None)
