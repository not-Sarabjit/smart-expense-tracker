"""FastAPI dependency for the compiled agent graph.

Mirrors ``dependencies/llm.py``: routes depend on this, tests override it with
``app.dependency_overrides[get_agent_graph] = lambda: build_graph(fake_model)``.
Used by the SSE endpoint in Step 1.6.
"""

from __future__ import annotations

from langchain_core.runnables import Runnable

from app.ai.agent.graph import get_compiled_graph


def get_agent_graph() -> Runnable:
    return get_compiled_graph()
