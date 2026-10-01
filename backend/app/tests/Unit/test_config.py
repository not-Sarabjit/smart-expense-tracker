import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core.config import (
    AISettings,
    AppSettings,
    AuthSettings,
    DatabaseSettings,
    QdrantSettings,
    Settings,
    get_settings,
)
from app.core.exceptions import FeatureDisabledException
from app.dependencies.features import require_ai_enabled


@pytest.fixture
def fresh_settings():
    """Clear the settings cache around a test that changes env vars."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_flat_env_names_populate_the_groups(monkeypatch, fresh_settings):
    """Env var names stay flat; the Python access path is grouped."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/expenses")
    monkeypatch.setenv("SECRET_KEY", "s3cret")
    monkeypatch.setenv("TOKEN_ALGORITHM", "HS512")
    monkeypatch.setenv("QDRANT_COLLECTION", "my_docs")
    monkeypatch.setenv("APP_ENVIRONMENT", "prod")

    settings = get_settings()

    assert settings.database.url == "postgresql://u:p@db:5432/expenses"
    assert settings.auth.secret_key == "s3cret"
    assert settings.auth.token_algorithm == "HS512"
    assert settings.qdrant.collection == "my_docs"
    assert settings.app.environment == "prod"
    assert settings.app.is_prod is True


def test_deprecated_flat_aliases_still_resolve(monkeypatch, fresh_settings):
    """The shim keeps session.py / auth_service.py / migrations working."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/expenses")
    monkeypatch.setenv("SECRET_KEY", "s3cret")

    settings = get_settings()

    assert settings.DATABASE_URL == settings.database.url
    assert settings.SECRET_KEY == settings.auth.secret_key
    assert settings.TOKEN_ALGORITHM == settings.auth.token_algorithm
    assert settings.QDRANT_COLLECTION == settings.qdrant.collection


def test_defaults_are_applied(fresh_settings):
    settings = get_settings()

    assert settings.qdrant.url == "http://localhost:6333"
    assert settings.qdrant.collection == "expense_docs"
    assert settings.database.pool_size == 20
    assert settings.auth.access_token_expire_minutes == 60
    assert settings.llm.provider == "groq"
    assert settings.embeddings.dimension == 384


def test_ai_is_disabled_by_default(monkeypatch, fresh_settings):
    """Fail-safe: a missing AI_ENABLED means off."""
    monkeypatch.delenv("AI_ENABLED", raising=False)

    assert get_settings().ai.enabled is False


def test_ai_flag_reads_env(monkeypatch, fresh_settings):
    monkeypatch.setenv("AI_ENABLED", "true")

    assert get_settings().ai.enabled is True


def test_get_settings_is_cached(fresh_settings):
    assert get_settings() is get_settings()


def test_require_ai_enabled_blocks_when_off():
    settings = Settings(
        database=DatabaseSettings(url="postgresql://x/y"),
        auth=AuthSettings(secret_key="x"),
        ai=AISettings(enabled=False),
    )

    with pytest.raises(FeatureDisabledException) as exc_info:
        require_ai_enabled(settings=settings)

    assert exc_info.value.status_code == 503


def test_require_ai_enabled_passes_when_on():
    settings = Settings(
        database=DatabaseSettings(url="postgresql://x/y"),
        auth=AuthSettings(secret_key="x"),
        ai=AISettings(enabled=True),
    )

    assert require_ai_enabled(settings=settings) is settings


def test_health_reflects_overridden_settings():
    """Tests swap the entire config without touching the environment."""

    def override() -> Settings:
        return Settings(
            app=AppSettings(environment="prod"),
            database=DatabaseSettings(url="postgresql://x/y"),
            auth=AuthSettings(secret_key="x"),
            ai=AISettings(enabled=True),
        )

    app.dependency_overrides[get_settings] = override
    try:
        response = TestClient(app).get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "environment": "prod",
            "ai_enabled": True,
        }
    finally:
        app.dependency_overrides.pop(get_settings, None)