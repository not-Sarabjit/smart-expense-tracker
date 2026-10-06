"""Step 1.8 — deterministic chat tests with a fake LLM.

Step 1.6 faked the *compiled graph*. These tests fake only the **model**, so
`build_graph`, the agent node, `prepare_turn`, the prompt loader, history replay
and `stream_turn` all execute for real — everything except the network.

Nothing here touches a provider, and the autouse `no_network` guard in conftest
turns an accidental attempt into a loud failure rather than a slow one.
"""

from __future__ import annotations

import json
import socket
import uuid

import pytest
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.ai.prompts.loader import SYSTEM_PROMPT_VERSION
from app.core.config import get_settings
from app.models.message import Message
from app.tests.conftest import TestingSessionLocal
from app.tests.fakes import ScriptedChatModel


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


def send(client, headers, conversation_id, content="How much did I spend on food?"):
    """Drive one full turn and return its parsed events."""
    with client.stream(
        "POST",
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": content},
    ) as response:
        assert response.status_code == 200
        return read_events(response)


def stored_messages(conversation_id: str) -> list[Message]:
    """Read the transcript through a SEPARATE session — proves it was committed."""
    session = TestingSessionLocal()
    try:
        return (
            session.query(Message)
            .filter(Message.conversation_id == uuid.UUID(conversation_id))
            .order_by(Message.id)
            .all()
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# the guard itself
# ---------------------------------------------------------------------------


def test_outbound_network_is_blocked():
    """If this ever passes a connection through, every other test is suspect."""
    with pytest.raises(RuntimeError, match="Blocked outbound connection"):
        socket.create_connection(("api.groq.com", 443), timeout=1)


def test_loopback_is_still_allowed():
    """The guard must not break local sockets the test stack itself uses."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    try:
        with socket.create_connection(listener.getsockname(), timeout=1):
            pass
    finally:
        listener.close()


# ---------------------------------------------------------------------------
# the real graph, driven by a fake model
# ---------------------------------------------------------------------------


def test_real_graph_streams_the_full_contract(client, user_a_headers, scripted_llm):
    llm = scripted_llm(["Hello there friend"], chunk_size=4)
    conversation_id = create_conversation(client, user_a_headers)

    events = send(client, user_a_headers, conversation_id)
    names = [name for name, _ in events]

    assert names[0] == "message_start"
    assert names[-1] == "message_end"
    assert names.count("token") >= 1
    assert set(names) == {"message_start", "token", "message_end"}

    start = events[0][1]
    assert start["conversation_id"] == conversation_id
    assert isinstance(start["user_message_id"], int)
    assert start["prompt_version"] == SYSTEM_PROMPT_VERSION

    assert "".join(p["text"] for n, p in events if n == "token") == "Hello there friend"

    end = events[-1][1]
    assert end["model"] == "scripted-model"  # from response_metadata, not settings
    assert end["usage"]["total_tokens"] == 14
    assert end["latency_ms"] >= 0
    assert end["title"] == "Groceries in September"
    assert isinstance(end["message_id"], int)

    # The model really was invoked through the real node, exactly once.
    assert llm.agent.call_count == 1


def test_library_fake_model_also_streams(client, user_a_headers, scripted_llm):
    """LangChain's own fake: no usage, no model name — the route must cope."""
    model = GenericFakeChatModel(messages=iter([AIMessage(content="Hello there friend")]))
    scripted_llm(model=model)
    conversation_id = create_conversation(client, user_a_headers)

    events = send(client, user_a_headers, conversation_id)
    text = "".join(p["text"] for n, p in events if n == "token")

    assert text == "Hello there friend"
    end = events[-1][1]
    assert end["usage"] is None
    # No model name on the wire -> the route reports the configured model.
    assert end["model"] == get_settings().llm.model


def test_both_rows_are_committed_with_meta(client, user_a_headers, scripted_llm):
    scripted_llm(["Spent 1200 on food."])
    conversation_id = create_conversation(client, user_a_headers)
    send(client, user_a_headers, conversation_id, content="How much on food?")

    rows = stored_messages(conversation_id)
    assert [row.role for row in rows] == ["user", "assistant"]
    assert rows[0].content == "How much on food?"
    assert rows[1].content == "Spent 1200 on food."

    meta = rows[1].meta
    assert meta["model"] == "scripted-model"
    assert meta["prompt_version"] == SYSTEM_PROMPT_VERSION
    assert meta["provider"] == get_settings().llm.provider
    assert meta["usage"]["total_tokens"] == 14
    assert isinstance(meta["latency_ms"], int)
    assert meta["request_id"]


def test_system_prompt_and_history_reach_the_model(client, user_a_headers, scripted_llm):
    """Memory is real: the second turn replays the first, with stable db- ids."""
    llm = scripted_llm(["First reply", "Second reply"])
    conversation_id = create_conversation(client, user_a_headers)

    send(client, user_a_headers, conversation_id, content="First question")
    send(client, user_a_headers, conversation_id, content="Second question")

    first, second = llm.agent.calls
    assert [type(m).__name__ for m in first] == ["SystemMessage", "HumanMessage"]
    assert isinstance(first[0], SystemMessage)
    assert first[0].id == "system"
    # The prompt was rendered, not a template left unfilled.
    assert "${" not in first[0].content
    assert "Test" in first[0].content  # the user's first name
    assert first[1].content == "First question"

    assert [type(m).__name__ for m in second] == [
        "SystemMessage",
        "HumanMessage",
        "AIMessage",
        "HumanMessage",
    ]
    assert second[1].content == "First question"
    assert second[2].content == "First reply"
    assert second[3].content == "Second question"
    assert all(m.id.startswith("db-") for m in second[1:3])
    assert isinstance(second[3], HumanMessage)


def test_model_failure_before_any_token_is_an_error_event(client, user_a_headers, scripted_llm):
    scripted_llm([RuntimeError("provider is down")])
    conversation_id = create_conversation(client, user_a_headers)

    events = send(client, user_a_headers, conversation_id)
    assert [name for name, _ in events] == ["message_start", "error"]
    assert events[-1][1]["request_id"]

    # D18: a failed turn persists the user row only.
    assert [row.role for row in stored_messages(conversation_id)] == ["user"]


def test_model_failure_mid_stream_is_an_error_event(client, user_a_headers, scripted_llm):
    """Tokens already sent, then the provider dies. Still no assistant row."""
    scripted_llm(["abcdefghijklmnop"], chunk_size=4, fail_after_chunks=2)
    conversation_id = create_conversation(client, user_a_headers)

    events = send(client, user_a_headers, conversation_id)
    names = [name for name, _ in events]

    assert names[0] == "message_start"
    assert names[-1] == "error"
    assert names.count("token") == 2
    assert [row.role for row in stored_messages(conversation_id)] == ["user"]


def test_fallback_model_answers_when_the_primary_fails(client, user_a_headers, scripted_llm):
    """D13's fallback chain, exercised without a provider."""
    primary = ScriptedChatModel(responses=[RuntimeError("down")], model_name="primary-model")
    backup = ScriptedChatModel(responses=["answer from the backup"], model_name="backup-model")
    scripted_llm(model=primary.with_fallbacks([backup]))

    conversation_id = create_conversation(client, user_a_headers)
    events = send(client, user_a_headers, conversation_id)

    assert "".join(p["text"] for n, p in events if n == "token") == "answer from the backup"
    assert events[-1][1]["model"] == "backup-model"
    assert primary.call_count == 1 and backup.call_count == 1


def test_a_failed_title_does_not_fail_the_turn(client, user_a_headers, scripted_llm):
    """The titler must swallow its own errors (titler.generate_title)."""
    llm = scripted_llm(["Hello there friend"])
    llm.title.responses = [RuntimeError("title model is down")]
    conversation_id = create_conversation(client, user_a_headers)

    events = send(client, user_a_headers, conversation_id)
    assert events[-1][0] == "message_end"
    assert events[-1][1]["title"] is None
    assert [row.role for row in stored_messages(conversation_id)] == ["user", "assistant"]


# ---------------------------------------------------------------------------
# auth and the kill switch, on the same path
# ---------------------------------------------------------------------------


def test_unauthenticated_send_is_rejected(client, user_a_headers, scripted_llm):
    scripted_llm()
    conversation_id = create_conversation(client, user_a_headers)
    response = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        json={"content": "hi"},
    )
    assert response.status_code in (401, 403)


def test_foreign_conversation_is_404_before_the_model_is_called(
    client, user_a_headers, user_b_headers, scripted_llm
):
    llm = scripted_llm()
    conversation_id = create_conversation(client, user_a_headers)
    response = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=user_b_headers,
        json={"content": "let me see that"},
    )
    assert response.status_code == 404
    assert llm.agent.call_count == 0


def test_ai_disabled_returns_503(client, user_a_headers):
    """No `ai_enabled` override here: AI_ENABLED is false for the suite."""
    response = client.post("/api/v1/chat/conversations", headers=user_a_headers, json={})
    assert response.status_code == 503
