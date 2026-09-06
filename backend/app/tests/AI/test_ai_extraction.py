import json
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from app.api.main import app
from app.schemas.ai import ExtractionResponse, ExtractedTransaction


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_groq_response(content: str) -> MagicMock:
    """
    Builds a mock that looks like a real Groq ChatCompletion response.
    """
    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


def _valid_llm_json(
    amount: float = 340.0,
    currency: str = "INR",
    description: str = "pizza",
    date_str: str = "2026-09-05",
    category_hint: str = "Food",
    confidence: float = 0.92,
) -> str:
    return json.dumps({
        "amount": amount,
        "currency": currency,
        "description": description,
        "date": date_str,
        "category_hint": category_hint,
        "confidence": confidence,
    })


@pytest.fixture
def auth_headers(client: TestClient):
    """
    Registers + logs in a test user and returns Bearer headers.
    Reuses your existing /auth/register and /auth/login endpoints.
    """
    client.post("/api/v1/auth/register", json={
        "email": "ai_test@example.com",
        "password": "TestPass123!",
        "first_name": "AI",
        "last_name": "Tester",
    })
    login = client.post("/api/v1/auth/login", json={
        "email": "ai_test@example.com",
        "password": "TestPass123!",
    })
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# Unit Tests — extractor.py logic (no HTTP, no DB)
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractorService:

    @patch("app.ai.extractor.ai_client")
    @pytest.mark.anyio
    async def test_valid_input_extracts_all_fields(self, mock_client):
        """
        Happy path: well-formed natural language returns all fields populated.
        """
        from app.ai.extractor import extract_transaction_from_text

        mock_client.complete_json = AsyncMock()
        mock_client.complete_json.return_value = json.loads(
            _valid_llm_json(
                amount=340.0,
                description="pizza",
                date_str="2026-09-05",
                category_hint="Food",
                confidence=0.92,
            )
        )

        result = await extract_transaction_from_text("paid 340 for pizza last night")

        assert result.success is True
        assert result.data is not None
        assert result.data.amount == 340.0
        assert result.data.description == "pizza"
        assert result.data.category_hint == "Food"
        assert result.data.date == date(2026, 9, 5)
        assert result.data.currency == "INR"
        assert result.confidence == 0.92

    @patch("app.ai.extractor.ai_client")
    @pytest.mark.anyio
    async def test_malformed_llm_json_returns_failure(self, mock_client):
        """
        If the LLM returns garbage instead of JSON, extractor returns
        success=False with confidence=0.0 — never raises an unhandled exception.
        """
        from app.ai.extractor import extract_transaction_from_text

        from app.core.exceptions import AIServiceError
        mock_client.complete_json = AsyncMock()
        mock_client.complete_json.side_effect = AIServiceError(
            "Model returned invalid JSON"
        )

        result = await extract_transaction_from_text("paid 340 for pizza")

        assert result.success is False
        assert result.data is None
        assert result.confidence == 0.0
        assert result.error_message is not None
        assert "unparseable" in result.error_message.lower()

    @patch("app.ai.extractor.ai_client")
    @pytest.mark.anyio
    async def test_missing_amount_returns_low_confidence(self, mock_client):
        """
        LLM returns valid JSON but amount is null → confidence should be low (<0.5)
        and data.amount should be None.
        """
        from app.ai.extractor import extract_transaction_from_text

        mock_client.complete_json = AsyncMock()
        mock_client.complete_json.return_value = {
                "amount": None,
                "currency": "INR",
                "description": "something happened",
                "date": None,
                "category_hint": None,
                "confidence": 0.2,
            }

        result = await extract_transaction_from_text("something happened with money")

        assert result.success is False       # no amount means unusable extraction
        assert result.data is None
        assert result.confidence < 0.5

    @patch("app.ai.extractor.ai_client")
    @pytest.mark.anyio
    async def test_invalid_date_format_is_handled_gracefully(self, mock_client):
        """
        LLM returns a date in wrong format → date field is set to None,
        rest of the extraction still succeeds.
        """
        from app.ai.extractor import extract_transaction_from_text

        mock_client.complete_json = AsyncMock()
        mock_client.complete_json.return_value = {
                "amount": 500.0,
                "currency": "INR",
                "description": "grocery run",
                "date": "not-a-date",           # bad format
                "category_hint": "Groceries",
                "confidence": 0.75,
            }

        result = await extract_transaction_from_text("spent 500 on groceries")

        assert result.success is True
        assert result.data.amount == 500.0
        assert result.data.date is None         # bad date is silently dropped

    @patch("app.ai.extractor.ai_client")
    @pytest.mark.anyio
    async def test_groq_api_error_raises_ai_service_error(self, mock_client):
        """
        If the Groq SDK raises an APIError, the extractor wraps it in
        AIServiceError — it never surfaces a raw SDK exception.
        """
        from groq import APIError
        from app.ai.extractor import extract_transaction_from_text
        from app.core.exceptions import AIServiceError

        mock_client.complete_json = AsyncMock()
        mock_client.complete_json.side_effect = APIError(
            message="Rate limit exceeded",
            request=MagicMock(),
            body=None,
        )

        with pytest.raises(AIServiceError) as exc_info:
            await extract_transaction_from_text("paid 340 for pizza")

        assert "Groq API call failed" in str(exc_info.value)

    @patch("app.ai.extractor.ai_client")
    @pytest.mark.anyio
    async def test_realistic_indian_expense_inputs(self, mock_client):
        """
        Tests realistic Indian-context inputs that reveal prompt weaknesses early.
        (Per roadmap beginner tip.)
        """
        from app.ai.extractor import extract_transaction_from_text

        cases = [
            ("EMI debited 12500",       12500.0, "EMI"),
            ("got salary 85000",         85000.0, "Salary"),
            ("Zomato order 340 rupees",    340.0, "Food"),
        ]

        mock_client.complete_json = AsyncMock()
        for text, expected_amount, expected_hint in cases:
            mock_client.complete_json.return_value = {
                "amount": expected_amount,
                "currency": "INR",
                "description": text,
                "date": "2026-09-05",
                "category_hint": expected_hint,
                "confidence": 0.88,
            }
            result = await extract_transaction_from_text(text)
            assert result.success is True
            assert result.data.amount == expected_amount, f"Failed for: {text}"


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests — POST /ai/extract  (HTTP layer)
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractEndpoint:

    @patch("app.api.ai.extract_transaction_from_text")
    def test_extract_returns_200_for_authenticated_user(
        self, mock_extract, client, auth_headers
    ):
        """
        Authenticated user with valid text gets a 200 and a structured response.
        """
        mock_extract.return_value = ExtractionResponse(
            success=True,
            data=ExtractedTransaction(
                amount=340.0,
                currency="INR",
                description="pizza",
                date=date(2026, 9, 5),
                category_hint="Food",
            ),
            raw_text="paid 340 for pizza last night",
            confidence=0.92,
        )

        response = client.post(
            "/api/v1/ai/extract",
            json={"text": "paid 340 for pizza last night"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["amount"] == 340.0
        assert body["data"]["category_hint"] == "Food"
        assert body["confidence"] == 0.92

    def test_extract_rejects_unauthenticated_request(self, client):
        """
        No auth header → 401. The endpoint is protected by get_current_user.
        """
        response = client.post(
            "/api/v1/ai/extract",
            json={"text": "paid 340 for pizza"},
            # no headers
        )
        assert response.status_code == 401

    def test_extract_rejects_empty_text(self, client, auth_headers):
        """
        Pydantic min_length=3 on the text field → 422 Unprocessable Entity.
        """
        response = client.post(
            "/api/v1/ai/extract",
            json={"text": "hi"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_extract_rejects_missing_text_field(self, client, auth_headers):
        """
        Missing required 'text' field → 422.
        """
        response = client.post(
            "/api/v1/ai/extract",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @patch("app.api.ai.extract_transaction_from_text")
    def test_extract_returns_503_on_ai_service_error(
        self, mock_extract, client, auth_headers
    ):
        """
        If the AI service is unavailable, endpoint returns 503 — not 500.
        """
        from app.core.exceptions import AIServiceError
        mock_extract.side_effect = AIServiceError("Groq is down")

        response = client.post(
            "/api/v1/ai/extract",
            json={"text": "paid 340 for pizza"},
            headers=auth_headers,
        )

        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests — POST /ai/extract-and-save  (HTTP layer)
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractAndSaveEndpoint:

    @patch("app.api.ai.extract_transaction_from_text")
    def test_dry_run_returns_preview_without_saving(
        self, mock_extract, client, auth_headers, db
    ):
        """
        dry_run=true → ExtractionResponse is returned, nothing written to DB.
        """
        from app.models.transaction import Transaction

        mock_extract.return_value = ExtractionResponse(
            success=True,
            data=ExtractedTransaction(
                amount=850.0,
                currency="INR",
                description="Uber rides",
                date=date(2026, 9, 5),
                category_hint="Transport",
            ),
            raw_text="spent 850 on Uber rides yesterday",
            confidence=0.93,
        )

        response = client.post(
            "/api/v1/ai/extract-and-save?dry_run=true",
            json={"text": "spent 850 on Uber rides yesterday"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["dry_run"] is True
        assert body["saved_transaction"] is None
        assert body["preview"]["amount"] == 850.0
        assert "nothing was saved" in body["message"].lower()

        # Confirm nothing actually hit the DB
        count = db.query(Transaction).count()
        assert count == 0

    @patch("app.api.ai.extract_transaction_from_text")
    def test_save_succeeds_and_returns_transaction(
        self, mock_extract, client, auth_headers, db
    ):
        """
        dry_run=false with high-confidence extraction → transaction saved to DB.
        """
        from app.models.transaction import Transaction

        mock_extract.return_value = ExtractionResponse(
            success=True,
            data=ExtractedTransaction(
                amount=850.0,
                currency="INR",
                description="Uber rides",
                date=date(2026, 9, 5),
                category_hint="Transport",
            ),
            raw_text="spent 850 on Uber rides yesterday",
            confidence=0.93,
        )

        response = client.post(
            "/api/v1/ai/extract-and-save?dry_run=false",
            json={"text": "spent 850 on Uber rides yesterday"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["dry_run"] is False
        assert body["saved_transaction"] is not None
        assert body["saved_transaction"]["amount"] == 850.0
        assert body["saved_transaction"]["description"] == "Uber rides"
        assert "saved successfully" in body["message"].lower()

        # Confirm it's actually in the DB
        count = db.query(Transaction).count()
        assert count == 1

    @patch("app.api.ai.extract_transaction_from_text")
    def test_low_confidence_refuses_to_save(
        self, mock_extract, client, auth_headers, db
    ):
        """
        Confidence below 0.5 → endpoint returns success=False, nothing saved.
        """
        from app.models.transaction import Transaction

        mock_extract.return_value = ExtractionResponse(
            success=True,
            data=ExtractedTransaction(
                amount=None,
                currency="INR",
                description="something",
                date=None,
                category_hint=None,
            ),
            raw_text="something happened with money",
            confidence=0.2,
        )

        response = client.post(
            "/api/v1/ai/extract-and-save?dry_run=false",
            json={"text": "something happened with money"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["saved_transaction"] is None
        assert "confidence" in body["message"].lower()

        count = db.query(Transaction).count()
        assert count == 0

    @patch("app.api.ai.extract_transaction_from_text")
    def test_null_amount_refuses_to_save(
        self, mock_extract, client, auth_headers, db
    ):
        """
        High-confidence extraction but amount=None → refuses to save.
        Amount is required to create a valid transaction.
        """
        from app.models.transaction import Transaction

        mock_extract.return_value = ExtractionResponse(
            success=True,
            data=ExtractedTransaction(
                amount=None,            # <-- no amount
                currency="INR",
                description="transferred something",
                date=date(2026, 9, 5),
                category_hint="Transfer",
            ),
            raw_text="transferred something",
            confidence=0.75,
        )

        response = client.post(
            "/api/v1/ai/extract-and-save?dry_run=false",
            json={"text": "transferred something"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert "amount" in body["message"].lower()

        count = db.query(Transaction).count()
        assert count == 0

    def test_extract_and_save_rejects_unauthenticated_request(self, client):
        """
        No auth header → 401 on the save endpoint too.
        """
        response = client.post(
            "/api/v1/ai/extract-and-save",
            json={"text": "paid 500 for groceries"},
        )
        assert response.status_code == 401

    @patch("app.api.ai.extract_transaction_from_text")
    def test_failed_extraction_returns_failure_without_saving(
        self, mock_extract, client, auth_headers
    ):
        """
        Extractor returns success=False (e.g. bad LLM JSON) → endpoint returns
        failure cleanly, no 500, nothing saved.
        """
        mock_extract.return_value = ExtractionResponse(
            success=False,
            data=None,
            raw_text="gibberish input",
            confidence=0.0,
            message="LLM returned unparseable output.",
        )

        response = client.post(
            "/api/v1/ai/extract-and-save?dry_run=false",
            json={"text": "gibberish input xyz"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["saved_transaction"] is None