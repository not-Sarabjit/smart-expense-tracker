from functools import lru_cache
from langchain_groq import ChatGroq
from app.core.config import settings


def get_llm(
    temperature: float | None = None,
    streaming: bool = False,
    max_tokens: int | None = None,
) -> ChatGroq:
    """
    Factory function — the ONLY place ChatGroq is instantiated.

    Args:
        temperature:  Override settings.GROQ_TEMPERATURE if provided.
        streaming:    Set True for SSE/streaming endpoints (Phase 4).
        max_tokens:   Override settings.GROQ_MAX_TOKENS if provided.

    Returns:
        A configured ChatGroq instance ready to use in any LCEL chain or agent.
    """
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=temperature if temperature is not None else settings.GROQ_TEMPERATURE,
        max_tokens=max_tokens if max_tokens is not None else settings.GROQ_MAX_TOKENS,
        streaming=streaming,
    )


@lru_cache(maxsize=2)
def get_llm_cached(streaming: bool = False) -> ChatGroq:
    """
    Cached version for cases where the same default LLM is reused heavily
    (e.g. embedding chains, classifiers). Uses settings defaults only.
    Don't use this where you need a custom temperature.
    """
    return get_llm(streaming=streaming)