import pytest

from app.ai.llm.factory import (
    build_chat_model,
    build_resilient,
    describe_llm,
    get_chat_model,
    get_fallback_models,
    reset_chat_model_cache,
    supported_providers,
)
from app.core.config import Settings
from app.core.exceptions import LLMNotConfiguredException

pytest.importorskip("langchain_groq", reason="requires the optional 'ai' extra")


@pytest.fixture(autouse=True)
def _clear_cache():
    """The factory memoises models; each test must build its own."""
    reset_chat_model_cache()
    yield
    reset_chat_model_cache()


def make_settings(**llm_overrides) -> Settings:
    """A Settings object with a dummy key — enough to construct a client offline."""
    settings = Settings()
    defaults = {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "api_key": "test-key-not-real",
        "temperature": 0.0,
        "timeout_seconds": 30.0,
        "max_retries": 2,
        "fallback_models": "llama-3.1-8b-instant",
    }
    defaults.update(llm_overrides)
    for field, value in defaults.items():
        setattr(settings.llm, field, value)
    return settings


def test_builds_the_configured_model():
    settings = make_settings(model="llama-3.3-70b-versatile")
    chat_model = get_chat_model(settings=settings)
    assert "llama-3.3-70b-versatile" in repr(chat_model.model_name)


def test_changing_the_model_setting_changes_the_model():
    """The 'Done when' criterion, as a test: config drives the model, not code."""
    first = get_chat_model(settings=make_settings(model="llama-3.3-70b-versatile"))
    second = get_chat_model(settings=make_settings(model="llama-3.1-8b-instant"))
    assert first.model_name != second.model_name


def test_tuning_knobs_reach_the_adapter():
    chat_model = get_chat_model(settings=make_settings(temperature=0.7, max_retries=5))
    assert chat_model.temperature == 0.7
    assert chat_model.max_retries == 5


def test_models_are_cached_per_configuration():
    settings = make_settings()
    assert get_chat_model(settings=settings) is get_chat_model(settings=settings)


def test_unknown_provider_raises_a_503_app_exception():
    with pytest.raises(LLMNotConfiguredException) as exc_info:
        get_chat_model(settings=make_settings(provider="definitely-not-a-provider"))
    assert exc_info.value.status_code == 503
    assert "groq" in exc_info.value.message


def test_missing_api_key_raises_rather_than_building_a_broken_client():
    with pytest.raises(LLMNotConfiguredException):
        get_chat_model(settings=make_settings(api_key=None))


def test_provider_name_is_case_and_whitespace_insensitive():
    assert get_chat_model(settings=make_settings(provider="  GROQ ")) is not None


def test_fallback_list_is_parsed_and_excludes_the_primary():
    settings = make_settings(
        model="llama-3.3-70b-versatile",
        fallback_models=" llama-3.1-8b-instant , , llama-3.3-70b-versatile ",
    )
    assert settings.llm.fallback_model_list == ["llama-3.1-8b-instant"]
    assert len(get_fallback_models(settings=settings)) == 1


def test_primary_model_supports_bind_tools():
    """Phase 3 depends on this: get_chat_model must return a real BaseChatModel."""
    assert hasattr(get_chat_model(settings=make_settings()), "bind_tools")


def test_build_resilient_applies_configure_to_every_model():
    settings = make_settings()
    calls = []

    def configure(model):
        calls.append(model.model_name)
        return model

    runnable = build_resilient(configure, settings=settings)
    assert len(calls) == 2  # primary + one fallback
    assert hasattr(runnable, "invoke")


def test_build_resilient_without_fallbacks_returns_the_model_itself():
    settings = make_settings(fallback_models="")
    assert hasattr(build_resilient(settings=settings), "bind_tools")


def test_describe_llm_never_leaks_the_key():
    described = describe_llm(make_settings())
    assert described["api_key_set"] is True
    assert "test-key-not-real" not in str(described)


def test_supported_providers_lists_groq():
    assert "groq" in supported_providers()


def test_build_chat_model_can_build_a_non_default_model():
    settings = make_settings(model="llama-3.3-70b-versatile")
    other = build_chat_model("llama-3.1-8b-instant", settings=settings)
    assert other.model_name == "llama-3.1-8b-instant"