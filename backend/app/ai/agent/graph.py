"""The agent graph.

One node today (``agent``). The structure - not the behaviour - is the deliverable: the tools
node (3.6), context builder (3.7), checkpointer (4.1) and guardrails (11.x) all attach here
without touching the call sites.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.messages import AnyMessage
from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from app.ai.agent.state import AgentContext, AgentState
from app.ai.llm.factory import build_resilient
from app.core.logging import get_logger

logger = get_logger(__name__)

AGENT_NODE = "agent"


def build_graph(model: Runnable | None = None) -> Runnable:
    """Compile the graph.

    ``model`` is injected so tests can pass a deterministic stand-in; production passes nothing
    and gets the primary chat model with its fallback chain (``build_resilient``). The model is
    resolved once, at build time - a compiled graph is immutable and shared across requests.

    The node is **async**: the SSE endpoint in 1.6 is an async generator, and an async-native
    graph streams tokens without bouncing through a thread pool. Nothing touching the ORM may
    ever run inside a node; the runner does all DB work before and after the graph runs.
    """
    chat_model = model if model is not None else build_resilient()

    async def agent(
        state: AgentState, runtime: Runtime[AgentContext]
    ) -> dict[str, list[AnyMessage]]:
        context = runtime.context
        metadata = context.as_trace_metadata() if context is not None else {}

        logger.info("agent.node_started", history_size=len(state["messages"]), **metadata)

        response = await chat_model.ainvoke(
            state["messages"],
            config={"run_name": "agent_llm", "metadata": metadata},
        )

        logger.info("agent.node_finished", response_id=getattr(response, "id", None), **metadata)

        # Returned as a partial update; the add_messages reducer merges it into state.
        return {"messages": [response]}

    builder = StateGraph(AgentState, context_schema=AgentContext)
    builder.add_node(AGENT_NODE, agent)
    builder.add_edge(START, AGENT_NODE)
    builder.add_edge(AGENT_NODE, END)
    return builder.compile()


@lru_cache(maxsize=1)
def get_compiled_graph() -> Runnable:
    """The process-wide compiled graph.

    Compiled on first use and reused for every request afterwards: a compiled graph is
    stateless and thread-safe, per-request data travels in state and context. Compiling per
    request re-runs node/channel validation on every chat message for no benefit.
    """
    graph = build_graph()
    logger.info("agent.graph_compiled", node_count=1)
    return graph


def reset_graph_cache() -> None:
    """Drop the cached graph. For tests that swap settings or the model."""
    get_compiled_graph.cache_clear()
