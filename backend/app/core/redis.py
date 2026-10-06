# backend/app/core/redis.py
"""Process-wide async Redis client.

One client, one connection pool, shared by every request. redis-py's asyncio
client is safe to share across coroutines and pools connections internally, so
creating one per request would only waste handshakes.

**Async, not sync.** The chat endpoint is `async def` (D15). A blocking socket
read inside an async handler stalls the event loop for *every* concurrent user,
not just the caller — so anything the chat path touches must be awaited.

Nothing here raises on a dead Redis: callers decide what an outage means. The
rate limiter (``core/rate_limit.py``) fails open; a future quota check (11.3)
may well choose differently.
"""

from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: aioredis.Redis | None = None


def get_redis_client(settings: Settings | None = None) -> aioredis.Redis:
    """Return the shared client, creating it on first use.

    Creating the client does **not** connect — redis-py connects lazily on the
    first command — so this is safe to call at import time or in a healthy-path
    dependency without paying a round trip.
    """
    global _client
    if _client is None:
        settings = settings or get_settings()
        _client = aioredis.from_url(
            settings.redis.url,
            max_connections=settings.redis.max_connections,
            socket_timeout=settings.redis.socket_timeout_seconds,
            socket_connect_timeout=settings.redis.socket_connect_timeout_seconds,
            # Return str instead of bytes — our values are ids and counters.
            decode_responses=True,
            # Proactively drop connections a firewall/proxy silently killed.
            health_check_interval=30,
        )
        logger.info("redis.client_created", url=_redacted_url(settings.redis.url))
    return _client


async def close_redis_client() -> None:
    """Close the pool on shutdown. Called from the FastAPI lifespan."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("redis.client_closed")


def reset_redis_client() -> None:
    """Drop the cached client without closing it. Tests that swap settings."""
    global _client
    _client = None


async def ping(settings: Settings | None = None) -> bool:
    """True if Redis answers. Never raises — for healthchecks and diagnostics."""
    try:
        return bool(await get_redis_client(settings).ping())
    except Exception:
        logger.warning("redis.ping_failed", exc_info=True)
        return False


def _redacted_url(url: str) -> str:
    """Strip any password before a URL reaches the logs."""
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    _, _, host = rest.rpartition("@")
    return f"{scheme}://***@{host}"
