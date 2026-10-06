"""Auto-titling a conversation with one cheap LLM call.

Deliberately isolated from the agent graph: titling is a side errand, uses a
different (smaller) model, and must never be able to break a chat turn. The
model is passed in so the API layer can inject it and tests can fake it.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.agent.history import message_text
from app.ai.prompts.loader import load_prompt
from app.core.logging import get_logger

logger = get_logger(__name__)

TITLE_PROMPT_VERSION = "title_v1"
#: Matches the 200-char DB/schema cap with room to spare; titles live in a sidebar.
MAX_TITLE_CHARS = 60
#: Only the opening of the user's message is needed to name the topic.
MAX_INPUT_CHARS = 1000


def _clean_title(raw: str) -> str | None:
    """Models like to answer with quotes, trailing full stops or two lines."""
    title = " ".join(raw.split())
    title = title.strip().strip('"').strip("'").strip()
    title = title.rstrip(".;:,")
    if not title:
        return None
    if len(title) > MAX_TITLE_CHARS:
        title = title[:MAX_TITLE_CHARS].rstrip()
    return title or None


async def generate_title(model: BaseChatModel, first_user_message: str) -> str | None:
    """Return a short title, or None if the model is unavailable or useless.

    Never raises: a failed title must not fail (or un-persist) a chat turn.
    """
    text = (first_user_message or "").strip()[:MAX_INPUT_CHARS]
    if not text:
        return None

    try:
        system = load_prompt(TITLE_PROMPT_VERSION)
        reply = await model.ainvoke([SystemMessage(content=system), HumanMessage(content=text)])
    except Exception:
        logger.warning("chat.title_generation_failed", exc_info=True)
        return None

    title = _clean_title(message_text(reply))
    logger.info("chat.title_generated", title_length=len(title or ""))
    return title
