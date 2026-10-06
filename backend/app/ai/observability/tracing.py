# backend/app/ai/observability/tracing.py
"""Tracing adapter.

The ONLY module in the codebase that imports a tracing vendor's SDK. Everything else asks for
callbacks and metadata through the functions here, so swapping Langfuse for Phoenix (or dropping
tracing entirely) is a one-file change.

Three rules this module never breaks:
  1. It never raises. Tracing is a diagnostic; a broken diagnostic must not break the feature it
     observes. Every failure path logs a warning and degrades to "no tracing" (cf. D21, the rate
     limiter failing open).
  2. The vendor SDK is imported lazily, inside functions. Importing this module must work with the
     `tracing` extra uninstalled -- which is exactly how CI runs.
  3. The secret key is never returned, logged or put in a trace attribute.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

TRACING_PROVIDER = "langfuse"

# Metadata keys the Langfuse LangChain handler reads off the runnable config to populate the trace.
_USER_ID_KEY = "langfuse_user_id"
_SESSION_ID_KEY = "langfuse_session_id"
_TAGS_KEY = "langfuse_tags"

_client: Any | None = None
_client_failed = False
_lock = threading.Lock()


@dataclass(frozen=True)
class TracingStatus:
    """Non-secret summary of the tracing configuration, safe to log or return from an endpoint."""

    enabled: bool
    provider: str
    host: str
    environment: str
    sdk_installed: bool
    configured: bool
    active: bool
    sample_rate: float


def _import_sdk() -> tuple[Any, Any] | None:
    """Return (Langfuse, CallbackHandler) or None if the `tracing` extra isn't installed."""
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler
    except ImportError:
        return None
    return Langfuse, CallbackHandler


def _resolve_environment(settings: Settings) -> str:
    return settings.tracing.environment or str(settings.app.environment)


def get_tracing_client(settings: Settings | None = None) -> Any | None:
    """Lazy singleton tracing client, or None when tracing is off/unconfigured/unavailable.

    Never raises. A failure is remembered so we warn once rather than on every chat turn.
    """
    global _client, _client_failed

    settings = settings or get_settings()
    cfg = settings.tracing

    if not cfg.enabled:
        return None

    if _client is not None or _client_failed:
        return _client

    with _lock:
        if _client is not None or _client_failed:
            return _client

        if not cfg.is_configured:
            logger.warning(
                "tracing.not_configured",
                provider=cfg.provider,
                reason="TRACING_ENABLED is true but public/secret key is missing",
            )
            _client_failed = True
            return None

        sdk = _import_sdk()
        if sdk is None:
            logger.warning(
                "tracing.sdk_missing",
                provider=cfg.provider,
                reason="install the 'tracing' extra: uv sync --extra tracing",
            )
            _client_failed = True
            return None

        langfuse_cls, _ = sdk
        try:
            _client = langfuse_cls(
                public_key=cfg.public_key,
                secret_key=cfg.secret_key,
                host=cfg.host,
                environment=_resolve_environment(settings),
                sample_rate=cfg.sample_rate,
                debug=cfg.debug,
            )
        except Exception:
            logger.warning("tracing.client_build_failed", provider=cfg.provider, exc_info=True)
            _client_failed = True
            return None

        logger.info(
            "tracing.client_ready",
            provider=cfg.provider,
            host=cfg.host,
            environment=_resolve_environment(settings),
            sample_rate=cfg.sample_rate,
        )
        return _client


def get_tracing_callbacks(settings: Settings | None = None) -> list[Any]:
    """Callbacks to attach to a LangChain/LangGraph run. Empty list = tracing off.

    Callers pass the result straight into the run config; an empty list is a valid no-op, so no
    caller ever needs an `if tracing_enabled:` branch.
    """
    client = get_tracing_client(settings)
    if client is None:
        return []

    sdk = _import_sdk()
    if sdk is None:
        return []

    _, handler_cls = sdk
    try:
        # v3: the handler binds to the client constructed above; it takes no credentials itself.
        return [handler_cls()]
    except Exception:
        logger.warning("tracing.handler_build_failed", exc_info=True)
        return []


def trace_metadata(
    *,
    user_id: int | str | None = None,
    session_id: str | None = None,
    request_id: str | None = None,
    prompt_version: str | None = None,
    tags: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the `metadata` dict for a run config.

    Pure function -- no SDK import, no I/O, always testable. Vendor-specific key names are confined
    here so callers (2.2) pass plain domain values.
    """
    metadata: dict[str, Any] = {}

    if user_id is not None:
        metadata[_USER_ID_KEY] = str(user_id)
    if session_id is not None:
        metadata[_SESSION_ID_KEY] = str(session_id)

    all_tags = list(tags or [])
    if prompt_version:
        all_tags.append(f"prompt:{prompt_version}")
    if all_tags:
        metadata[_TAGS_KEY] = all_tags

    if request_id:
        metadata["request_id"] = request_id
    if prompt_version:
        metadata["prompt_version"] = prompt_version
    if extra:
        metadata.update(extra)

    return metadata


def flush(settings: Settings | None = None) -> None:
    """Send anything still buffered. Safe to call when tracing is off. Never raises."""
    client = get_tracing_client(settings)
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        logger.warning("tracing.flush_failed", exc_info=True)


def shutdown(settings: Settings | None = None) -> None:
    """Flush and stop background workers. Called from the FastAPI lifespan. Never raises."""
    global _client, _client_failed

    client = _client
    if client is None:
        return
    try:
        client.shutdown()
    except Exception:
        logger.warning("tracing.shutdown_failed", exc_info=True)
    finally:
        _client = None
        _client_failed = False


def describe_tracing(settings: Settings | None = None) -> TracingStatus:
    """Non-secret config summary -- mirrors describe_llm(). Never includes the secret key."""
    settings = settings or get_settings()
    cfg = settings.tracing
    sdk_installed = _import_sdk() is not None

    return TracingStatus(
        enabled=cfg.enabled,
        provider=cfg.provider,
        host=cfg.host,
        environment=_resolve_environment(settings),
        sdk_installed=sdk_installed,
        configured=cfg.is_configured,
        active=bool(cfg.is_configured and sdk_installed),
        sample_rate=cfg.sample_rate,
    )


def reset_tracing_client() -> None:
    """Drop the cached client -- for tests that override settings."""
    global _client, _client_failed
    with _lock:
        _client = None
        _client_failed = False
