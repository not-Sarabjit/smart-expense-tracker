"""Rebuild LangChain messages from the stored transcript — the short-term memory window.

The model is stateless: 'memory' is nothing more than replaying the last N rows of
``messages`` into state before each turn.
"""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage

from app.core.logging import get_logger
from app.models.message import Message

logger = get_logger(__name__)

# How many stored rows we replay per turn. A module constant for now: Step 5.1 replaces the
# count with a token budget, so a settings knob here would be short-lived.
DEFAULT_MEMORY_WINDOW = 20

# Compared against the raw stored string. ``MessageRole`` is the validator on the write path;
# on the read path the DB hands us plain text and these values are the contract.
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


def history_message_id(row_id: int | None) -> str:
    """Stable LangChain id for a stored row.

    ``add_messages`` de-duplicates by id, so replaying the same row twice (retry, resume,
    a node that re-injects history) can never produce a duplicate turn.
    """
    return f"db-{row_id}"


def to_lc_messages(rows: Sequence[Message]) -> list[AnyMessage]:
    """Map stored rows (oldest first) to LangChain messages.

    Only *complete text turns* are replayed:

    * ``user`` rows with content        -> ``HumanMessage``
    * ``assistant`` rows with content and **no** ``tool_calls`` -> ``AIMessage``
    * everything else is dropped.

    Why drop the rest: an ``AIMessage`` carrying ``tool_calls`` is only a valid history entry
    when the matching ``ToolMessage`` replies follow it. Replaying half a tool pair makes the
    provider reject the *next* request, which is a miserable bug to trace. Phase 3 owns the
    round-trip; until then a dropped turn is a small loss of context, a broken pair is a 400.
    System rows are never replayed either - the system prompt is re-rendered every turn
    (date, currency, prompt version all move).
    """
    messages: list[AnyMessage] = []
    skipped = 0

    for row in rows:
        # Tolerate both a plain string (from the DB) and a str-enum member (constructed in code).
        role = getattr(row.role, "value", row.role)
        content = row.content

        if role == ROLE_USER and content:
            messages.append(HumanMessage(content=content, id=history_message_id(row.id)))
        elif role == ROLE_ASSISTANT and content and not row.tool_calls:
            messages.append(AIMessage(content=content, id=history_message_id(row.id)))
        else:
            skipped += 1

    if skipped:
        logger.debug("agent.history_rows_skipped", skipped=skipped, kept=len(messages))

    return messages

def message_text(message: BaseMessage) -> str:
    """Flatten a message's content to plain text.

    `content` is usually a `str`, but langchain-core also allows a list of
    content blocks (dicts like `{"type": "text", "text": "..."}`). Handling both
    here means callers never have to care which provider they're on.
    """
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""
