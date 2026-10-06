"""Step 1.5 - agent state, history rebuild, runner and the compiled graph.

No network and no database: the model is a RunnableLambda, the User and Message rows are
unsaved ORM objects. Async code is driven with asyncio.run() so the suite needs no
pytest-asyncio.
"""

from __future__ import annotations

import asyncio

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda

from app.ai.agent import graph as graph_module
from app.ai.agent.graph import build_graph, get_compiled_graph, reset_graph_cache
from app.ai.agent.history import history_message_id, to_lc_messages
from app.ai.agent.runner import SYSTEM_MESSAGE_ID, prepare_turn, run_turn
from app.models.message import Message
from app.models.user import User


def make_user(**overrides) -> User:
    data = {
        "id": 7,
        "email": "ada@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
    }
    data.update(overrides)
    return User(**data)


def echo_model(seen_messages: list | None = None, seen_configs: list | None = None):
    """Stand-in chat model. The two-argument form receives the RunnableConfig."""

    def _call(messages, config):
        if seen_messages is not None:
            seen_messages.append(list(messages))
        if seen_configs is not None:
            seen_configs.append(config)
        return AIMessage(content=f"ok:{len(messages)}")

    return RunnableLambda(_call)


# --- history rebuild ---------------------------------------------------------------------


def test_to_lc_messages_maps_user_and_assistant():
    rows = [
        Message(id=1, role="user", content="how much did I spend?"),
        Message(id=2, role="assistant", content="let me look"),
    ]

    out = to_lc_messages(rows)

    assert [type(m) for m in out] == [HumanMessage, AIMessage]
    assert out[0].content == "how much did I spend?"
    assert out[1].content == "let me look"


def test_to_lc_messages_skips_system_and_tool_rows():
    rows = [
        Message(id=1, role="system", content="you are an assistant"),
        Message(id=2, role="tool", content='{"total": 12}'),
        Message(id=3, role="user", content="hi"),
        Message(id=4, role="user", content=None),
    ]

    out = to_lc_messages(rows)

    assert len(out) == 1
    assert isinstance(out[0], HumanMessage)


def test_to_lc_messages_skips_assistant_turns_with_tool_calls():
    rows = [
        Message(id=1, role="user", content="hi"),
        Message(id=2, role="assistant", content=None, tool_calls=[{"name": "query"}]),
        Message(id=3, role="assistant", content="partial", tool_calls=[{"name": "query"}]),
    ]

    out = to_lc_messages(rows)

    assert [type(m) for m in out] == [HumanMessage]


def test_to_lc_messages_sets_stable_ids():
    out = to_lc_messages([Message(id=42, role="user", content="hi")])

    assert out[0].id == history_message_id(42) == "db-42"


# --- prepare_turn ------------------------------------------------------------------------


def test_prepare_turn_orders_system_history_then_input():
    history = [
        Message(id=1, role="user", content="first"),
        Message(id=2, role="assistant", content="second"),
    ]

    inputs = prepare_turn(make_user(), history, "  third  ")
    messages = inputs.state["messages"]

    assert [type(m) for m in messages] == [SystemMessage, HumanMessage, AIMessage, HumanMessage]
    assert messages[0].id == SYSTEM_MESSAGE_ID
    assert messages[-1].content == "third"


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_prepare_turn_rejects_blank_input(bad):
    with pytest.raises(ValueError):
        prepare_turn(make_user(), [], bad)


def test_prepare_turn_context_carries_profile_and_prompt_version():
    inputs = prepare_turn(
        make_user(id=99, first_name="Grace", currency="USD", timezone="America/New_York"),
        [],
        "hello",
        conversation_id="abc-123",
    )
    context = inputs.context

    assert context.user_id == 99
    assert context.first_name == "Grace"
    assert context.currency == "USD"
    assert context.timezone == "America/New_York"
    assert context.prompt_version
    assert context.conversation_id == "abc-123"
    # user context must not leak into state - the LLM can never write it
    assert set(inputs.state) == {"messages"}


# --- the graph ---------------------------------------------------------------------------


def test_run_turn_returns_ai_message():
    graph = build_graph(echo_model())
    inputs = prepare_turn(make_user(), [], "hello")

    reply = asyncio.run(run_turn(inputs, graph=graph))

    assert isinstance(reply, AIMessage)
    assert reply.content.startswith("ok:")


def test_run_turn_sends_whole_window_to_the_model():
    seen: list = []
    graph = build_graph(echo_model(seen_messages=seen))
    history = [
        Message(id=1, role="user", content="first"),
        Message(id=2, role="assistant", content="second"),
    ]

    asyncio.run(run_turn(prepare_turn(make_user(), history, "third"), graph=graph))

    # system + 2 replayed rows + the new input
    assert len(seen) == 1
    assert len(seen[0]) == 4
    assert seen[0][-1].content == "third"


def test_runtime_context_reaches_the_node():
    configs: list = []
    graph = build_graph(echo_model(seen_configs=configs))
    inputs = prepare_turn(make_user(id=77), [], "hello", conversation_id="conv-1")

    asyncio.run(run_turn(inputs, graph=graph))

    metadata = configs[0]["metadata"]
    assert metadata["user_id"] == 77
    assert metadata["conversation_id"] == "conv-1"
    assert metadata["prompt_version"] == inputs.context.prompt_version


def test_graph_is_compiled_once(monkeypatch):
    builds: list[int] = []

    def fake_build_resilient(*args, **kwargs):
        builds.append(1)
        return echo_model()

    monkeypatch.setattr(graph_module, "build_resilient", fake_build_resilient)
    reset_graph_cache()
    try:
        first = get_compiled_graph()
        second = get_compiled_graph()

        assert first is second
        assert len(builds) == 1
    finally:
        reset_graph_cache()
