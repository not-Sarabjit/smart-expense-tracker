# backend/app/tests/Unit/test_tracing.py
"""Step 2.1 -- the tracing adapter degrades safely and leaks no secrets.

These must pass whether or not the `tracing` extra is installed: CI runs without it, the dev
machine runs with it. No test here ever reaches the network (the autouse `no_network` fixture
in app/tests/conftest.py would fail it if it did).
"""

import pytest

from app.ai.observability import tracing
from app.core.config import Settings, TracingSettings, get_settings


@pytest.fixture(autouse=True)
def _reset_client():
    tracing.reset_tracing_client()
    yield
    tracing.reset_tracing_client()


def _settings(**overrides) -> Settings:
    base = get_settings()
    cfg = base.model_copy(deep=True)
    cfg.tracing = TracingSettings(**overrides)
    return cfg


# --- off by default ------------------------------------------------------


def test_disabled_by_default():
    assert get_settings().tracing.enabled is False


def test_no_callbacks_when_disabled():
    assert tracing.get_tracing_callbacks(_settings(enabled=False)) == []


def test_no_client_when_disabled():
    assert tracing.get_tracing_client(_settings(enabled=False)) is None


def test_flush_is_a_noop_when_disabled():
    tracing.flush(_settings(enabled=False))  # must not raise


def test_shutdown_is_a_noop_when_never_started():
    tracing.shutdown(_settings(enabled=False))  # must not raise


# --- misconfiguration degrades, never raises -----------------------------


def test_enabled_without_keys_degrades():
    settings = _settings(enabled=True, public_key=None, secret_key=None)
    assert settings.tracing.is_configured is False
    assert tracing.get_tracing_client(settings) is None
    assert tracing.get_tracing_callbacks(settings) == []


def test_enabled_with_only_public_key_degrades():
    settings = _settings(enabled=True, public_key="pk-lf-x", secret_key=None)
    assert settings.tracing.is_configured is False
    assert tracing.get_tracing_callbacks(settings) == []


def test_enabled_with_keys_never_raises():
    """With the SDK absent -> []. With it present -> a handler, built without touching the network."""
    settings = _settings(enabled=True, public_key="pk-lf-x", secret_key="sk-lf-x")
    callbacks = tracing.get_tracing_callbacks(settings)
    assert isinstance(callbacks, list)


def test_failure_is_sticky():
    """A broken config must warn once, not once per chat turn."""
    settings = _settings(enabled=True, public_key=None, secret_key=None)
    assert tracing.get_tracing_client(settings) is None
    assert tracing.get_tracing_client(settings) is None  # cached failure, no re-attempt


# --- validation ----------------------------------------------------------


def test_sample_rate_is_bounded():
    with pytest.raises(ValueError):
        TracingSettings(sample_rate=1.5)
    with pytest.raises(ValueError):
        TracingSettings(sample_rate=-0.1)


# --- describe_tracing never leaks the secret -----------------------------


def test_describe_omits_secrets():
    settings = _settings(enabled=True, public_key="pk-lf-public", secret_key="sk-lf-SECRET")
    status = tracing.describe_tracing(settings)
    assert "sk-lf-SECRET" not in repr(status)
    assert "pk-lf-public" not in repr(status)
    assert status.enabled is True
    assert status.configured is True


def test_describe_environment_falls_back_to_app_environment():
    settings = _settings(enabled=False, environment=None)
    assert tracing.describe_tracing(settings).environment == str(settings.app.environment)


def test_describe_environment_override_wins():
    settings = _settings(enabled=False, environment="staging")
    assert tracing.describe_tracing(settings).environment == "staging"


# --- trace_metadata is pure and vendor-key-shaped ------------------------


def test_metadata_empty_when_nothing_given():
    assert tracing.trace_metadata() == {}


def test_metadata_maps_domain_values_to_vendor_keys():
    md = tracing.trace_metadata(
        user_id=7,
        session_id="3f2e...uuid",
        request_id="req-abc",
        prompt_version="system_v1",
        tags=["chat"],
    )
    assert md["langfuse_user_id"] == "7"  # stringified
    assert md["langfuse_session_id"] == "3f2e...uuid"
    assert md["request_id"] == "req-abc"
    assert md["prompt_version"] == "system_v1"
    assert "chat" in md["langfuse_tags"]
    assert "prompt:system_v1" in md["langfuse_tags"]


def test_metadata_extra_is_merged():
    md = tracing.trace_metadata(user_id=1, extra={"feature": "chat"})
    assert md["feature"] == "chat"
