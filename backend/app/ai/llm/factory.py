"""Chat-model factory (ports & adapters).

The *port* is langchain_core's ``BaseChatModel``. Each provider gets an *adapter*
builder registered in ``_PROVIDER_BUILDERS``. Application code asks for a model by
configuration only, so changing LLM_PROVIDER / LLM_MODEL in .env changes the model
with no code change.

Provider SDKs are imported lazily inside their builders so that an install without
the optional ``ai`` extra can still import this module.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.core.config import Settings, get_settings
from app.core.exceptions import LLMNotConfiguredException
from app.core.logging import get_logger

logger = get_logger(__name__)

# A builder takes the resolved, hashable config and returns a provider adapter.
ProviderBuilder = Callable[[str, str | None, float, float, int], BaseChatModel]


def _build_groq(
    model: str,
    api_key: str | None,
    temperature: float,
    timeout_seconds: float,
    max_retries: int,
) -> BaseChatModel:
    """Adapter for Groq. Imported lazily: requires the optional `ai` extra."""
    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:  # pragma: no cover - depends on install extras
        raise LLMNotConfiguredException(
            "The 'ai' extra is not installed (uv sync --extra ai)."
        ) from exc

    if not api_key:
        raise LLMNotConfiguredException("LLM_API_KEY is not set, so no chat model can be created.")

    return ChatGroq(
        model=model,
        api_key=api_key,
        temperature=temperature,
        timeout=timeout_seconds,
        max_retries=max_retries,
    )


_PROVIDER_BUILDERS: dict[str, ProviderBuilder] = {
    "groq": _build_groq,
}


def supported_providers() -> list[str]:
    """Provider names accepted in LLM_PROVIDER."""
    return sorted(_PROVIDER_BUILDERS)


@lru_cache(maxsize=16)
def _build_cached(
    provider: str,
    model: str,
    api_key: str | None,
    temperature: float,
    timeout_seconds: float,
    max_retries: int,
) -> BaseChatModel:
    """Build (and memoise) one chat model. Arguments are plain hashable values."""
    builder = _PROVIDER_BUILDERS.get(provider)
    if builder is None:
        raise LLMNotConfiguredException(
            f"Unknown LLM provider '{provider}'. "
            f"Supported providers: {', '.join(supported_providers())}."
        )

    chat_model = builder(model, api_key, temperature, timeout_seconds, max_retries)
    logger.info("llm.model_built", provider=provider, model=model)
    return chat_model


def _resolve_api_key(settings: Settings) -> str | None:
    """Return the API key as a plain string, whether it is str or SecretStr."""
    api_key = settings.llm.api_key
    if api_key is None:
        return None
    get_secret_value = getattr(api_key, "get_secret_value", None)
    return get_secret_value() if callable(get_secret_value) else str(api_key)


def build_chat_model(model_name: str, settings: Settings | None = None) -> BaseChatModel:
    """Build one specific model using the configured provider and tuning knobs."""
    settings = settings or get_settings()
    return _build_cached(
        settings.llm.provider.strip().lower(),
        model_name,
        _resolve_api_key(settings),
        settings.llm.temperature,
        settings.llm.timeout_seconds,
        settings.llm.max_retries,
    )


def get_chat_model(settings: Settings | None = None) -> BaseChatModel:
    """The primary chat model (LLM_PROVIDER + LLM_MODEL).

    Returns a real BaseChatModel, so callers can use .bind_tools() /
    .with_structured_output() on it. Use build_resilient() when you want fallbacks.
    """
    settings = settings or get_settings()
    return build_chat_model(settings.llm.model, settings=settings)


def get_fallback_models(settings: Settings | None = None) -> list[BaseChatModel]:
    """Models tried, in order, when the primary fails (LLM_FALLBACK_MODELS)."""
    settings = settings or get_settings()
    return [build_chat_model(name, settings=settings) for name in settings.llm.fallback_model_list]


def build_resilient(
    configure: Callable[[BaseChatModel], Runnable] = lambda chat_model: chat_model,
    settings: Settings | None = None,
) -> Runnable:
    """Primary model + fallback chain, with `configure` applied to every model.

    `configure` exists because RunnableWithFallbacks is NOT a BaseChatModel: it has
    no .bind_tools(). Tools (and any other binding) must therefore be attached to
    each model *before* the chain is composed:

        runnable = build_resilient(lambda m: m.bind_tools(tools))
    """
    settings = settings or get_settings()
    primary = configure(get_chat_model(settings=settings))
    fallbacks = [configure(model) for model in get_fallback_models(settings=settings)]
    if not fallbacks:
        return primary
    return primary.with_fallbacks(fallbacks)


def describe_llm(settings: Settings | None = None) -> dict[str, object]:
    """Non-secret summary of the active LLM config, for logs, /health and smoke tests."""
    settings = settings or get_settings()
    return {
        "provider": settings.llm.provider,
        "model": settings.llm.model,
        "fallback_models": settings.llm.fallback_model_list,
        "temperature": settings.llm.temperature,
        "timeout_seconds": settings.llm.timeout_seconds,
        "max_retries": settings.llm.max_retries,
        "api_key_set": bool(_resolve_api_key(settings)),
    }


def reset_chat_model_cache() -> None:
    """Clear the memoised models. Used by tests that override settings."""
    _build_cached.cache_clear()
