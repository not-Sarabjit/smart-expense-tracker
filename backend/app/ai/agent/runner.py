"""Assemble a turn and run it through the graph.

Split in two on purpose:

* ``prepare_turn`` is **sync** and is the only place that touches ORM objects.
* ``run_turn`` is **async** and touches no ORM object at all.

That split is what keeps lazy-loading out of the event loop when the SSE endpoint (1.6) calls
this from an async context.

Persistence is *not* done here - 1.6 owns writing the user and assistant rows.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    AnyMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.runnables import Runnable

from app.ai.agent.graph import AGENT_NODE, get_compiled_graph
from app.ai.agent.history import to_lc_messages
from app.ai.agent.state import AgentContext, AgentState
from app.ai.prompts.loader import PromptContext, render_system_prompt
from app.core.logging import get_logger
from app.core.request_context import get_request_id
from app.models.message import Message
from app.models.user import User

logger = get_logger(__name__)

# Stable id so re-injecting the system prompt replaces it instead of stacking copies
# (add_messages de-duplicates by id).
SYSTEM_MESSAGE_ID = "system"


@dataclass(frozen=True)
class TurnInputs:
    """Everything the graph needs for one turn, with no ORM object left in it."""

    state: AgentState
    context: AgentContext


def prepare_turn(
    user: User,
    history: Sequence[Message],
    user_input: str,
    *,
    conversation_id: UUID | str | None = None,
    now: datetime | None = None,
) -> TurnInputs:
    """Build the message list and runtime context for one turn.

    ``history`` is the memory window, oldest first - typically
    ``ConversationService.get_recent_messages(user_id, conversation_id, limit=DEFAULT_MEMORY_WINDOW)``.

    The system prompt is re-rendered every turn: 'today' moves, and the prompt version must be
    the one shipped right now, not the one in use when the conversation started.
    """
    text = (user_input or "").strip()
    if not text:
        # A programming error, not a user-facing domain error - the 1.6 request schema
        # rejects blank input long before this. Deliberately not an AppException.
        raise ValueError("user_input must not be blank")

    prompt_context = PromptContext.from_user(user, now=now)
    rendered = render_system_prompt(prompt_context)

    messages: list[AnyMessage] = [SystemMessage(content=rendered.text, id=SYSTEM_MESSAGE_ID)]
    messages.extend(to_lc_messages(history))
    messages.append(HumanMessage(content=text))

    try:
        request_id = get_request_id()
    except LookupError:
        # Outside a request (smoke script, Celery worker in Phase 6).
        request_id = None

    context = AgentContext(
        user_id=user.id,
        first_name=prompt_context.user_first_name,
        timezone=prompt_context.timezone,
        currency=prompt_context.currency,
        prompt_version=rendered.version,
        conversation_id=str(conversation_id) if conversation_id is not None else None,
        request_id=request_id,
    )

    return TurnInputs(state={"messages": messages}, context=context)


async def run_turn(inputs: TurnInputs, *, graph: Runnable | None = None) -> AIMessage:
    """Run one turn and return the assistant's reply.

    ``graph`` is injectable for tests; production uses the process-wide compiled graph.
    """
    graph = graph or get_compiled_graph()

    result = await graph.ainvoke(inputs.state, context=inputs.context)
    reply = result["messages"][-1]

    if not isinstance(reply, AIMessage):
        raise RuntimeError(f"agent graph ended on a {type(reply).__name__}, expected AIMessage")

    return reply


async def stream_turn(
    inputs: TurnInputs,
    *,
    graph: Runnable | None = None,
) -> AsyncIterator[AIMessageChunk]:
    """Run one turn and yield the assistant's message chunks as they arrive.

    Uses LangGraph's `stream_mode="messages"`, which surfaces the LLM's own
    token chunks from inside the node as `(chunk, metadata)` pairs. The caller
    accumulates them (`acc = acc + chunk`) to get the final message — chunks add
    together into a complete `AIMessageChunk`, usage metadata included.

    Like `run_turn`, this persists nothing: the API layer owns the DB.
    """
    graph = graph or get_compiled_graph()

    async for chunk, metadata in graph.astream(
        inputs.state,
        context=inputs.context,
        stream_mode="messages",
    ):
        # Only the agent node's own output is the assistant's reply. In Phase 3
        # other nodes will produce LLM calls we don't want echoed to the user.
        node = (metadata or {}).get("langgraph_node")
        if node is not None and node != AGENT_NODE:
            continue

        if isinstance(chunk, AIMessageChunk):
            yield chunk
        elif isinstance(chunk, AIMessage):
            # A model that didn't stream hands back a whole AIMessage. Wrap it
            # so the caller's accumulation logic stays uniform.
            yield AIMessageChunk(
                content=chunk.content,
                id=chunk.id,
                usage_metadata=chunk.usage_metadata,
                response_metadata=chunk.response_metadata,
            )
