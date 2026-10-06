"""Step 1.6 — SSE streaming endpoint.

No network: the agent graph and the title model are replaced with fakes through
dependency overrides. Step 1.8 broadens this with LangChain's fake chat models.
"""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk

from app.api.main import app
from app.dependencies.agent import get_agent_graph
from app.dependencies.features import require_ai_enabled
from app.dependencies.llm import get_title_llm


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


def read_events(response) -> list[tuple[str, dict]]:
    """Parse an SSE body into (event_name, payload) pairs."""
    events: list[tuple[str, dict]] = []
    name: str | None = None
    for line in response.iter_lines():
        line = line.strip()
        if not line:
            name = None
            continue
        if line.startswith("event:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and name:
            events.append((name, json.loads(line.split(":", 1)[1].strip())))
    return events


def create_conversation(client, headers) -> str:
    response = client.post("/api/v1/chat/conversations", headers=headers, json={})
    assert response.status_code == 201
    return response.json()["id"]


def test_stream_emits_contract_events(client, user_a_headers, fake_graph, fake_title_model):
    conversation_id = create_conversation(client, user_a_headers)

    with client.stream(
        "POST",
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=user_a_headers,
        json={"content": "How much did I spend on food?"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = read_events(response)

    names = [name for name, _ in events]
    assert names[0] == "message_start"
    assert names[-1] == "message_end"
    assert names.count("token") == 3

    tokens = "".join(payload["text"] for name, payload in events if name == "token")
    assert tokens == "Hello there!"

    end = events[-1][1]
    assert end["usage"]["total_tokens"] == 14
    assert end["model"] == "fake-model"
    assert end["title"] == "Groceries in September"
    assert isinstance(end["message_id"], int)


def test_both_messages_are_persisted(client, user_a_headers, fake_graph, fake_title_model):
    conversation_id = create_conversation(client, user_a_headers)

    with client.stream(
        "POST",
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=user_a_headers,
        json={"content": "Hi there"},
    ) as response:
        read_events(response)

    stored = client.get(
        f"/api/v1/chat/conversations/{conversation_id}/messages", headers=user_a_headers
    ).json()
    assert [m["role"] for m in stored] == ["user", "assistant"]
    assert stored[0]["content"] == "Hi there"
    assert stored[1]["content"] == "Hello there!"
    assert stored[1]["meta"]["prompt_version"]
    assert stored[1]["meta"]["usage"]["total_tokens"] == 14


def test_conversation_is_auto_titled_only_once(
    client, user_a_headers, fake_graph, fake_title_model
):
    conversation_id = create_conversation(client, user_a_headers)
    url = f"/api/v1/chat/conversations/{conversation_id}/messages"

    with client.stream("POST", url, headers=user_a_headers, json={"content": "First"}) as r:
        read_events(r)
    with client.stream("POST", url, headers=user_a_headers, json={"content": "Second"}) as r:
        events = read_events(r)

    assert fake_title_model.calls == 1
    assert events[-1][1]["title"] is None
    conversation = client.get(
        f"/api/v1/chat/conversations/{conversation_id}", headers=user_a_headers
    ).json()
    assert conversation["title"] == "Groceries in September"


def test_history_is_replayed_into_the_graph(client, user_a_headers, fake_graph, fake_title_model):
    conversation_id = create_conversation(client, user_a_headers)
    url = f"/api/v1/chat/conversations/{conversation_id}/messages"

    with client.stream("POST", url, headers=user_a_headers, json={"content": "First"}) as r:
        read_events(r)
    with client.stream("POST", url, headers=user_a_headers, json={"content": "Second"}) as r:
        read_events(r)

    first_state, _, stream_mode = fake_graph.calls[0]
    second_state, context, _ = fake_graph.calls[1]
    assert stream_mode == "messages"
    # turn 1: system + the new user message. turn 2: + the stored user/assistant pair.
    assert len(first_state["messages"]) == 2
    assert len(second_state["messages"]) == 4
    assert context.conversation_id is not None


def test_foreign_conversation_is_404_not_a_stream(
    client, user_a_headers, user_b_headers, fake_graph, fake_title_model
):
    conversation_id = create_conversation(client, user_a_headers)
    response = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=user_b_headers,
        json={"content": "Let me see that"},
    )
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("body", [{"content": "   "}, {"content": ""}, {}])
def test_invalid_body_is_422(client, user_a_headers, fake_graph, fake_title_model, body):
    conversation_id = create_conversation(client, user_a_headers)
    response = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=user_a_headers,
        json=body,
    )
    assert response.status_code == 422


def test_graph_failure_becomes_an_error_event(client, user_a_headers, fake_title_model):
    class ExplodingGraph:
        async def astream(self, state, *, context=None, stream_mode=None, **kwargs):
            raise RuntimeError("provider is down")
            yield  # pragma: no cover - makes this an async generator

    app.dependency_overrides[require_ai_enabled] = lambda: None
    app.dependency_overrides[get_agent_graph] = lambda: ExplodingGraph()
    try:
        conversation_id = create_conversation(client, user_a_headers)
        with client.stream(
            "POST",
            f"/api/v1/chat/conversations/{conversation_id}/messages",
            headers=user_a_headers,
            json={"content": "Hello"},
        ) as response:
            assert response.status_code == 200  # headers already sent
            events = read_events(response)

        assert events[-1][0] == "error"
        stored = client.get(
            f"/api/v1/chat/conversations/{conversation_id}/messages",
            headers=user_a_headers,
        ).json()
        assert [m["role"] for m in stored] == ["user"]  # no partial assistant row
    finally:
        app.dependency_overrides.pop(require_ai_enabled, None)
        app.dependency_overrides.pop(get_agent_graph, None)
