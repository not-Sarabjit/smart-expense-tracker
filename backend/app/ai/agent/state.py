"""Agent state and per-run context.

Two different channels, on purpose:

* ``AgentState``   - conversation data the graph reads AND writes.
* ``AgentContext`` - immutable facts about *this run* (who, where, which prompt). Passed in at
  invoke time via LangGraph's runtime context, never stored in state, never fillable by the LLM.
  This is the channel that grows into ``ToolContext``, which is why ownership data
  lives here: a tool must take ``user_id`` from the runtime, not from a model-generated argument.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """What flows through the graph.

    ``add_messages`` is a reducer: a node returns ``{"messages": [msg]}`` and the runtime merges
    it into the existing list (appending, or replacing an entry with the same ``id``). Without
    the annotation the default reducer would *overwrite* the list, forcing every node to carry
    the whole history forward.
    """

    messages: Annotated[list[AnyMessage], add_messages]


@dataclass(frozen=True)
class AgentContext:
    """Immutable per-run context. Frozen so a node cannot smuggle state in here."""

    user_id: int
    first_name: str
    timezone: str
    currency: str
    prompt_version: str
    conversation_id: str | None = None
    request_id: str | None = None

    def as_trace_metadata(self) -> dict[str, Any]:
        """Flat key/values attached to every LLM call.

        Shows up in LangChain callbacks today and in the tracing backend from Phase 2, so a
        trace can be filtered by user, conversation, request id or prompt version. Never put
        anything secret or free-text in here.
        """
        return {
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "request_id": self.request_id,
            "prompt_version": self.prompt_version,
        }
