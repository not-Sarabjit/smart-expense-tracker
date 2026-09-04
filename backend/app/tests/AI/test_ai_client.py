
import pytest
from unittest.mock import patch, MagicMock

from app.ai.client import AIClient
from app.core.exceptions import AIServiceError, AITokenLimitError


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────

def _make_mock_response(text: str) -> MagicMock:
    """Build a fake Groq SDK response object."""
    message = MagicMock()
    message.content = text

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]

    return response


# ─────────────────────────────────────────────
# 1. Successful call returns the expected text
# ─────────────────────────────────────────────

@patch("app.ai.client.Groq")
def test_complete_returns_text_on_success(mock_groq_class):
    """A successful Groq SDK call should return the model's text content."""

    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client

    fake_response = _make_mock_response("Test response from Groq")
    mock_client.chat.completions.create.return_value = fake_response

    ai_client = AIClient()

    result = ai_client.complete(
        prompt="Hello",
        system="You are a helpful assistant."
    )

    assert result == "Test response from Groq"
    mock_client.chat.completions.create.assert_called_once()


# ─────────────────────────────────────────────
# 2. SDK error triggers retry
# ─────────────────────────────────────────────

@patch("app.ai.client.Groq")
def test_complete_retries_on_sdk_error(mock_groq_class):
    """
    If the SDK raises on the first call but succeeds on the second,
    the retry logic should recover and return the text.
    """

    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client

    fake_response = _make_mock_response("Recovered after retry")

    # First call raises, second call succeeds
    mock_client.chat.completions.create.side_effect = [
        Exception("Temporary API error"),
        fake_response,
    ]

    ai_client = AIClient()

    result = ai_client.complete(prompt="Hello")

    assert result == "Recovered after retry"
    assert mock_client.chat.completions.create.call_count == 2


# ─────────────────────────────────────────────
# 3. Three failures raise AIServiceError
# ─────────────────────────────────────────────

@patch("app.ai.client.Groq")
def test_complete_raises_ai_service_error_after_max_retries(
    mock_groq_class
):
    """
    After exhausting all retries (3 attempts), the client must raise
    AIServiceError — never let a raw SDK exception bubble up.
    """

    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client

    mock_client.chat.completions.create.side_effect = Exception(
        "Persistent API failure"
    )

    ai_client = AIClient()

    with pytest.raises(AIServiceError):
        ai_client.complete(prompt="Hello")

    # Tenacity retries 3 times total
    assert mock_client.chat.completions.create.call_count == 3


# ─────────────────────────────────────────────
# 4. Token limit guard fires before the API call
# ─────────────────────────────────────────────

@patch("app.ai.client.Groq")
@patch("app.ai.token_utils.assert_within_limit")
def test_token_limit_guard_raises_before_api_call(
    mock_assert_limit,
    mock_groq_class
):
    """
    If the prompt exceeds the token limit, AITokenLimitError should be
    raised immediately — before any API call is made.
    """

    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client

    mock_assert_limit.side_effect = AITokenLimitError(
        "Prompt exceeds token limit"
    )

    ai_client = AIClient()

    with pytest.raises(AITokenLimitError):
        ai_client.complete(prompt="A" * 100_000)

    # The SDK must NOT have been called
    mock_client.chat.completions.create.assert_not_called()


# ─────────────────────────────────────────────
# 5. complete_json parses valid JSON correctly
# ─────────────────────────────────────────────

@patch("app.ai.client.Groq")
def test_complete_json_returns_parsed_dict(mock_groq_class):
    """complete_json() should parse the LLM's JSON string into a dict."""

    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client

    fake_json = (
        '{"amount": 250.0, '
        '"description": "Grocery run", '
        '"category": "Food"}'
    )

    mock_client.chat.completions.create.return_value = (
        _make_mock_response(fake_json)
    )

    ai_client = AIClient()

    result = ai_client.complete_json(
        prompt="Extract this transaction."
    )

    assert isinstance(result, dict)
    assert result["amount"] == 250.0
    assert result["category"] == "Food"


# ─────────────────────────────────────────────
# 6. complete_json raises AIServiceError on malformed JSON
# ─────────────────────────────────────────────

@patch("app.ai.client.Groq")
def test_complete_json_raises_on_malformed_response(mock_groq_class):
    """Malformed JSON should result in AIServiceError."""

    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client

    mock_client.chat.completions.create.return_value = (
        _make_mock_response(
            "Sorry, I cannot help with that."
        )
    )

    ai_client = AIClient()

    with pytest.raises(AIServiceError):
        ai_client.complete_json(
            prompt="Extract this transaction."
        )