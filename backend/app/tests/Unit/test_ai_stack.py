"""Smoke tests for the AI dependency stack (Step 0.10). No network calls.

Skipped when the optional `ai` extra isn't installed (`uv sync --extra dev --extra ai`);
CI installs it, so they always run there.
"""

from typing import TypedDict

import pytest

langgraph_graph = pytest.importorskip("langgraph.graph")
langchain_groq = pytest.importorskip("langchain_groq")


def test_langgraph_compiles_and_runs_a_graph():
    class State(TypedDict):
        count: int

    def increment(state: State) -> State:
        return {"count": state["count"] + 1}

    builder = langgraph_graph.StateGraph(State)
    builder.add_node("increment", increment)
    builder.add_edge(langgraph_graph.START, "increment")
    builder.add_edge("increment", langgraph_graph.END)
    graph = builder.compile()

    assert graph.invoke({"count": 1}) == {"count": 2}


def test_chat_groq_builds_without_calling_the_api():
    model = langchain_groq.ChatGroq(model="llama-3.3-70b-versatile", api_key="test-key")

    assert model.model_name == "llama-3.3-70b-versatile"


def test_langchain_1x_and_qdrant_adapters_import():
    from importlib.metadata import version

    import langchain_qdrant  # noqa: F401
    import qdrant_client  # noqa: F401

    assert version("langchain").startswith("1.")
    assert version("langchain-core").startswith("1.")
    assert version("langgraph").startswith("1.")
