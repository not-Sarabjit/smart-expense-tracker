# backend/app/dependencies/rate_limit.py
"""Rate-limit dependencies.

Enforced at the HTTP boundary, like the feature flags in `dependencies/features.py`
— services stay unaware of HTTP concerns.

**Why a dependency and not middleware.** The limit is per-route and per-*user*:
middleware runs before authentication has resolved a user, and would have to
hardcode which paths are expensive. A dependency keys off `current_user.id` and
is attached only to the route that costs money.

**Ordering.** FastAPI resolves every dependency before the handler body runs, so
the limit is checked before the ownership query, before the user message row is
written, and before any byte of the SSE stream is sent — satisfying D18 (the
status code must be decided while the headers are still unsent).

`get_current_user` is already a dependency of the route; FastAPI caches
dependency results per request, so declaring it here costs no extra DB query.
"""

from __future__ import annotations

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.exceptions import RateLimitExceededException
from app.core.logging import get_logger
from app.core.rate_limit import (
    RateLimitDecision,
    SlidingWindowRateLimiter,
    chat_message_key,
)
from app.core.redis import get_redis_client
from app.dependencies.auth import get_current_user
from app.models.user import User

logger = get_logger(__name__)


def get_rate_limiter(settings: Settings = Depends(get_settings)) -> SlidingWindowRateLimiter:
    """Injectable limiter. Tests override this with a fakeredis-backed one."""
    return SlidingWindowRateLimiter(get_redis_client(settings))


async def rate_limit_chat_message(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
) -> RateLimitDecision:
    """Consume one chat-message slot for this user, or raise 429.

    Returns the decision so the route can put the RateLimit-* headers on its
    StreamingResponse: FastAPI does not merge a dependency's `Response` headers
    into a Response the handler returns itself, so they have to be passed along
    explicitly.
    """
    limits = settings.rate_limit
    if not limits.enabled:
        return RateLimitDecision.unlimited(limits.chat_messages)

    decision = await limiter.check(
        chat_message_key(current_user.id),
        limit=limits.chat_messages,
        window_seconds=limits.chat_window_seconds,
    )

    if not decision.allowed:
        logger.warning(
            "ratelimit.rejected",
            route="chat.send_message",
            limit=decision.limit,
            window_seconds=limits.chat_window_seconds,
            retry_after=decision.retry_after,
        )
        raise RateLimitExceededException(headers=decision.as_headers())

    return decision
