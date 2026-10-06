# backend/app/core/rate_limit.py
"""Sliding-window-log rate limiting on Redis.

### The algorithm

One Redis **sorted set** (ZSET) per subject. A ZSET is a set whose members each
carry a numeric *score*, kept ordered by it. Here one member = one accepted
request, and its score = the millisecond timestamp it happened at.

Each check, in a single Lua script so no two workers can interleave:

1. ``ZREMRANGEBYSCORE`` — forget everything older than ``now - window``.
2. ``ZCARD``            — how many requests remain inside the window?
3. under the limit -> ``ZADD`` this request and allow; otherwise deny.
4. ``PEXPIRE``          — give the key a TTL so an idle user's key disappears
                          instead of leaking memory forever.
5. read the *oldest* surviving member — it expires at ``score + window``, which
   is exactly when a slot frees up, so ``Retry-After`` is a fact, not a guess.

Chosen over a fixed-window counter (which is cheaper but allows a double burst
across the minute boundary — 40 concurrent LLM streams at a limit of 20) and
over a token bucket (whose whole selling point is a burst allowance we do not
want here). Cost is one ZSET of at most `limit` tiny members per active user.

### Failure policy

Redis down -> **allow** the request and log ``ratelimit.backend_unavailable`` at
WARNING. A rate limit guards cost, not correctness or access; a cache outage
should not take chat down. This pairs with the 250ms socket timeout in
``core/redis.py``: fail-open is only safe when failure is detected fast.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.logging import get_logger

logger = get_logger(__name__)


#: KEYS[1] = the ZSET key
#: ARGV    = now_ms, window_ms, limit, unique_member
#: returns = {allowed, remaining, reset_ms}
_SLIDING_WINDOW_LUA = """
local key    = KEYS[1]
local now    = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit  = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)

local count     = redis.call('ZCARD', key)
local allowed   = 0
local remaining = 0

if count < limit then
  redis.call('ZADD', key, now, member)
  allowed   = 1
  remaining = limit - count - 1
end

redis.call('PEXPIRE', key, window)

local reset_ms = 0
local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
if oldest[2] then
  reset_ms = (tonumber(oldest[2]) + window) - now
  if reset_ms < 0 then reset_ms = 0 end
end

return {allowed, remaining, reset_ms}
"""


@dataclass(frozen=True)
class RateLimitDecision:
    """The verdict for one request, plus everything the client should be told."""

    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int
    retry_after: int | None = None
    #: True when Redis was unreachable and we allowed the request anyway.
    degraded: bool = False

    def as_headers(self) -> dict[str, str]:
        """IETF draft RateLimit-* headers, sent on success *and* on 429.

        Telling clients their budget up front is what lets a well-behaved
        frontend back off before it gets a 429, instead of discovering the
        limit by hitting it.
        """
        headers = {
            "RateLimit-Limit": str(self.limit),
            "RateLimit-Remaining": str(max(0, self.remaining)),
            "RateLimit-Reset": str(self.reset_seconds),
        }
        if self.retry_after is not None:
            headers["Retry-After"] = str(self.retry_after)
        return headers

    @classmethod
    def unlimited(cls, limit: int, *, degraded: bool = False) -> RateLimitDecision:
        """An allow-everything verdict: limiting disabled, or Redis unreachable."""
        return cls(
            allowed=True,
            limit=limit,
            remaining=limit,
            reset_seconds=0,
            degraded=degraded,
        )


class SlidingWindowRateLimiter:
    """Checks and records requests against a Redis sliding-window log."""

    def __init__(self, client: Redis, *, fail_open: bool = True):
        self._client = client
        # register_script hashes the body once and uses EVALSHA, falling back to
        # EVAL when Redis has not cached it (e.g. after a restart). Means we ship
        # the script body over the wire once, not on every request.
        self._script = client.register_script(_SLIDING_WINDOW_LUA)
        self._fail_open = fail_open

    async def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        now_ms: int | None = None,
    ) -> RateLimitDecision:
        """Consume one slot for `key`. `now_ms` is injectable so tests can time-travel."""
        window_ms = int(window_seconds * 1000)
        now_ms = int(now_ms if now_ms is not None else time.time() * 1000)

        try:
            allowed, remaining, reset_ms = await self._script(
                keys=[key],
                args=[now_ms, window_ms, limit, uuid.uuid4().hex],
            )
        except (RedisError, OSError):
            # OSError covers connection refused / DNS / timeouts beneath redis-py.
            logger.warning("ratelimit.backend_unavailable", key=key, exc_info=True)
            if not self._fail_open:
                raise
            return RateLimitDecision.unlimited(limit, degraded=True)

        allowed = bool(allowed)
        reset_seconds = max(0, math.ceil(int(reset_ms) / 1000))
        return RateLimitDecision(
            allowed=allowed,
            limit=limit,
            remaining=int(remaining),
            reset_seconds=reset_seconds,
            # Never advertise 0 seconds: a client would retry instantly and be
            # refused again. Round a sub-second wait up to 1.
            retry_after=None if allowed else max(1, reset_seconds),
        )


def chat_message_key(user_id: int) -> str:
    """Namespaced key. The `ratelimit:` prefix keeps these scannable and separate
    from the cache, locks and Celery keys that will share this Redis later."""
    return f"ratelimit:chat:messages:{user_id}"
