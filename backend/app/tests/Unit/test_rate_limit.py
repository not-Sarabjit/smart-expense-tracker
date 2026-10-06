"""Step 1.7 — per-user rate limiting on the chat send endpoint.

No live Redis: `fakeredis` runs the real Lua script in-process, so the algorithm
under test is the one that ships, not a stub.

Time is injected (`now_ms`) rather than slept, so window-boundary behaviour is
asserted exactly and the suite stays fast and deterministic.
"""

from __future__ import annotations

import uuid

import fakeredis.aioredis
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.api.main import app
from app.core.config import get_settings
from app.core.rate_limit import SlidingWindowRateLimiter
from app.dependencies.features import require_ai_enabled
from app.dependencies.rate_limit import get_rate_limiter

T0 = 1_000_000_000_000  # a fixed "now" in ms


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def limiter(fake_redis):
    return SlidingWindowRateLimiter(fake_redis)


# --------------------------------------------------------------------------
# the limiter itself
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_allows_up_to_the_limit(limiter):
    for i in range(3):
        decision = await limiter.check("k", limit=3, window_seconds=60, now_ms=T0 + i)
        assert decision.allowed
        assert decision.remaining == 2 - i


@pytest.mark.asyncio
async def test_rejects_the_request_after_the_limit(limiter):
    for i in range(3):
        await limiter.check("k", limit=3, window_seconds=60, now_ms=T0 + i)

    decision = await limiter.check("k", limit=3, window_seconds=60, now_ms=T0 + 3)
    assert not decision.allowed
    assert decision.remaining == 0
    assert decision.retry_after == 60  # oldest entry is ~60s from expiring


@pytest.mark.asyncio
async def test_retry_after_counts_down_as_the_window_slides(limiter):
    await limiter.check("k", limit=1, window_seconds=60, now_ms=T0)

    decision = await limiter.check("k", limit=1, window_seconds=60, now_ms=T0 + 20_000)
    assert not decision.allowed
    assert decision.retry_after == 40  # 60s window, 20s elapsed


@pytest.mark.asyncio
async def test_retry_after_is_never_zero(limiter):
    """A 0 would make a client retry instantly and be refused again."""
    await limiter.check("k", limit=1, window_seconds=60, now_ms=T0)

    decision = await limiter.check("k", limit=1, window_seconds=60, now_ms=T0 + 59_900)
    assert not decision.allowed
    assert decision.retry_after == 1


@pytest.mark.asyncio
async def test_slot_frees_once_the_oldest_entry_leaves_the_window(limiter):
    await limiter.check("k", limit=1, window_seconds=60, now_ms=T0)

    assert not (await limiter.check("k", limit=1, window_seconds=60, now_ms=T0 + 59_999)).allowed
    assert (await limiter.check("k", limit=1, window_seconds=60, now_ms=T0 + 60_000)).allowed


@pytest.mark.asyncio
async def test_limits_are_isolated_per_key(limiter):
    await limiter.check("user:1", limit=1, window_seconds=60, now_ms=T0)

    decision = await limiter.check("user:2", limit=1, window_seconds=60, now_ms=T0)
    assert decision.allowed


@pytest.mark.asyncio
async def test_key_carries_a_ttl_so_idle_users_do_not_leak_memory(limiter, fake_redis):
    await limiter.check("k", limit=5, window_seconds=60, now_ms=T0)

    ttl_ms = await fake_redis.pttl("k")
    assert 0 < ttl_ms <= 60_000


@pytest.mark.asyncio
async def test_rejected_requests_do_not_consume_a_slot(limiter):
    """A denied request must not extend the penalty — otherwise a client that
    retries in a loop can never recover."""
    await limiter.check("k", limit=1, window_seconds=60, now_ms=T0)
    for offset in range(1, 20):
        await limiter.check("k", limit=1, window_seconds=60, now_ms=T0 + offset)

    assert (await limiter.check("k", limit=1, window_seconds=60, now_ms=T0 + 60_000)).allowed


@pytest.mark.asyncio
async def test_fails_open_when_redis_is_unreachable():
    class DeadRedis:
        def register_script(self, _script):
            async def _raise(*args, **kwargs):
                raise RedisConnectionError("connection refused")

            return _raise

    decision = await SlidingWindowRateLimiter(DeadRedis()).check(
        "k", limit=1, window_seconds=60, now_ms=T0
    )
    assert decision.allowed
    assert decision.degraded


def test_headers_describe_the_budget(limiter):
    from app.core.rate_limit import RateLimitDecision

    headers = RateLimitDecision(
        allowed=False, limit=20, remaining=0, reset_seconds=37, retry_after=37
    ).as_headers()

    assert headers["RateLimit-Limit"] == "20"
    assert headers["RateLimit-Remaining"] == "0"
    assert headers["RateLimit-Reset"] == "37"
    assert headers["Retry-After"] == "37"


# --------------------------------------------------------------------------
# the endpoint
# --------------------------------------------------------------------------


@pytest.fixture
def limited_client(client, fake_redis, monkeypatch):
    """Chat routes open, AI flag bypassed, limit forced to 2/min on fakeredis."""
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_CHAT_MESSAGES", "2")
    get_settings.cache_clear()

    app.dependency_overrides[require_ai_enabled] = lambda: None
    app.dependency_overrides[get_rate_limiter] = lambda: SlidingWindowRateLimiter(fake_redis)
    yield client
    app.dependency_overrides.pop(require_ai_enabled, None)
    app.dependency_overrides.pop(get_rate_limiter, None)
    monkeypatch.undo()  # restore env first...
    get_settings.cache_clear()  # ...then rebuild Settings from it


def test_send_message_429s_past_the_limit(
    limited_client, user_a_headers, fake_graph, fake_title_model
):
    created = limited_client.post("/api/v1/chat/conversations", json={}, headers=user_a_headers)
    conversation_id = created.json()["id"]
    url = f"/api/v1/chat/conversations/{conversation_id}/messages"

    for _ in range(2):
        ok = limited_client.post(url, json={"content": "hi"}, headers=user_a_headers)
        assert ok.status_code == 200
        assert ok.headers["RateLimit-Limit"] == "2"

    blocked = limited_client.post(url, json={"content": "hi"}, headers=user_a_headers)
    assert blocked.status_code == 429
    # our AppException body shape, not FastAPI's {"detail": ...}
    assert blocked.json()["error"] is True
    assert blocked.json()["status_code"] == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    assert blocked.headers["RateLimit-Remaining"] == "0"


def test_rate_limit_is_per_user(
    limited_client, user_a_headers, user_b_headers, fake_graph, fake_title_model
):
    def send(headers):
        conversation_id = limited_client.post(
            "/api/v1/chat/conversations", json={}, headers=headers
        ).json()["id"]
        return limited_client.post(
            f"/api/v1/chat/conversations/{conversation_id}/messages",
            json={"content": "hi"},
            headers=headers,
        )

    for _ in range(3):
        send(user_a_headers)

    assert send(user_b_headers).status_code == 200


def test_throttled_request_writes_no_message_row(
    limited_client, user_a_headers, fake_graph, fake_title_model
):
    """D18: the limit runs as a dependency, so a 429 costs no DB work."""
    conversation_id = limited_client.post(
        "/api/v1/chat/conversations", json={}, headers=user_a_headers
    ).json()["id"]
    url = f"/api/v1/chat/conversations/{conversation_id}/messages"

    for _ in range(3):
        limited_client.post(url, json={"content": "hi"}, headers=user_a_headers)

    listed = limited_client.get(url, headers=user_a_headers)
    # 2 accepted turns -> 2 user + 2 assistant rows. The 429 added nothing.
    assert listed.headers["X-Total-Count"] == "4"


def test_unknown_conversation_still_404s_not_429(limited_client, user_a_headers):
    """The limit must not mask ownership errors on the first request."""
    response = limited_client.post(
        f"/api/v1/chat/conversations/{uuid.uuid4()}/messages",
        json={"content": "hi"},
        headers=user_a_headers,
    )
    assert response.status_code == 404
