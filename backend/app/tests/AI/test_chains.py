import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from langchain_core.exceptions import OutputParserException
from groq import RateLimitError, APIStatusError

from app.ai.chains.summariser import summarise_text
from app.ai.chains.extractor import extract_transaction
from app.core.exceptions import AIParseError, AIRateLimitError, AIServiceError
from app.schemas.ai import ExtractedTransaction


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_ai_message(content: str) -> AIMessage:
    """Wrap a string in an AIMessage as ChatGroq would return."""
    return AIMessage(content=content)


VALID_TRANSACTION_JSON = """{
    "amount": 450.0,
    "description": "Lunch at Zomato",
    "category": "Food",
    "date": null,
    "confidence": 0.95
}"""


# ── Summariser tests ────────────────────────────────────────────────────────────

class TestSummariser:

    @patch("app.ai.chains.summariser.get_llm")
    def test_summarise_returns_string(self, mock_get_llm):
        """summarise_text() should return the LLM's text output as a plain string."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = make_ai_message("You spent ₹4,500 this month on food.")
        mock_llm.side_effect = mock_llm.invoke
        mock_get_llm.return_value = mock_llm

        result = summarise_text("January expenses: food 4500, transport 800")

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("app.ai.chains.summariser.get_llm")
    def test_summarise_passes_text_to_chain(self, mock_get_llm):
        """The input text should reach the chain's invoke call."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = make_ai_message("Summary here.")
        mock_llm.side_effect = mock_llm.invoke
        mock_get_llm.return_value = mock_llm

        summarise_text("some expense text")

        mock_llm.invoke.assert_called_once()


# ── Extractor tests ─────────────────────────────────────────────────────────────

class TestExtractor:

    @patch("app.ai.chains.extractor._extractor_chain")
    def test_extract_valid_transaction(self, mock_chain):
        """Valid LLM JSON output should return a typed ExtractedTransaction."""
        mock_chain.invoke.return_value = {
            "amount": 450.0,
            "description": "Lunch at Zomato",
            "category": "Food",
            "date": None,
            "confidence": 0.95,
        }

        result = extract_transaction("Spent 450 on lunch at Zomato")

        assert isinstance(result, ExtractedTransaction)
        assert result.amount == 450.0
        assert result.category == "Food"


    @patch("app.ai.chains.extractor._extractor_chain")
    def test_extract_raises_ai_parse_error_on_bad_json(self, mock_chain):
        """OutputParserException from LangChain should be mapped to AIParseError."""
        mock_chain.invoke.side_effect = OutputParserException("bad json")

        with pytest.raises(AIParseError):
            extract_transaction("some garbage input")

    @patch("app.ai.chains.extractor._extractor_chain")
    def test_extract_raises_ai_rate_limit_error(self, mock_chain):
        """Groq RateLimitError should be mapped to AIRateLimitError."""
        mock_chain.invoke.side_effect = RateLimitError(
            message="rate limit", response=MagicMock(), body={}
        )

        with pytest.raises(AIRateLimitError):
            extract_transaction("Spent 200 on coffee")

    @patch("app.ai.chains.extractor._extractor_chain")
    def test_extract_raises_ai_service_error_on_unexpected(self, mock_chain):
        """Any unexpected exception should be mapped to AIServiceError."""
        mock_chain.invoke.side_effect = RuntimeError("something exploded")

        with pytest.raises(AIServiceError):
            extract_transaction("Spent 200 on coffee")

    @patch("app.ai.chains.extractor._extractor_chain")
    def test_extract_confidence_within_bounds(self, mock_chain):
        """Confidence score should be between 0.0 and 1.0."""
        mock_chain.invoke.return_value = {
            "amount": 1200.0,
            "description": "Electricity bill",
            "category": "Bills",
            "date": "2024-01-15",
            "confidence": 0.88,
        }

        result = extract_transaction("Paid electricity bill 1200 on 15th Jan")

        assert 0.0 <= result.confidence <= 1.0

    @patch("app.ai.chains.extractor._extractor_chain")
    def test_extract_date_format(self, mock_chain):
        """Date should be returned in YYYY-MM-DD format when present."""
        mock_chain.invoke.return_value = {
            "amount": 500.0,
            "description": "Grocery shopping",
            "category": "Shopping",
            "date": "2024-01-20",
            "confidence": 0.9,
        }

        result = extract_transaction("Spent 500 at BigBasket on 20th Jan")

        assert result.date == "2024-01-20"