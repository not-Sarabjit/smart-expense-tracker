import json
import logging
from datetime import date, datetime
from typing import Optional

from app.ai.client import ai_client
from app.ai.prompt import EXTRACT_TRANSACTION
from app.core.exceptions import AIServiceError
from app.schemas.ai import ExtractedTransaction, ExtractionResponse

logger = logging.getLogger(__name__)

today = date.today()

def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Safely parse a date string in YYYY-MM-DD format."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        logger.warning(f"Could not parse date: {date_str!r}")
        return None


def _parse_llm_json(raw: str) -> dict:
    """
    Parse JSON from LLM response.
    Handles edge cases: extra whitespace, markdown fences, trailing commas.
    """
    # Strip markdown fences if the model added them despite instructions
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]).strip()

    return json.loads(cleaned)


async def extract_transaction_from_text(text: str) -> ExtractionResponse:
    """
    Extract structured transaction data from a natural language string.

    Returns ExtractionResponse with:
    - success=True  → data is populated, confidence > 0
    - success=False → data is None, error_message explains why

    Never raises — always returns a valid ExtractionResponse.
    """
    # Render the prompt template
    rendered = EXTRACT_TRANSACTION.render({"text": text, 'today': today})

    # --- Call the LLM ---
    try:
        parsed = await ai_client.complete_json(
            prompt=rendered["user"],
            system=rendered["system"],
        )
        logger.debug(f"Raw LLM response for extraction: {parsed}")
    except AIServiceError as e:
        logger.error(f"AI service error during extraction: {e}")
        if "invalid json" in str(e).lower():
            return ExtractionResponse(
                success=False,
                data=None,
                raw_text=text,
                confidence=0.0,
                error_message="AI returned unparseable output. Please try again.",
            )
        raise
    except Exception as e:
        raise AIServiceError(
            message=f"Groq API call failed: {e}",
            original_error=e,
        ) from e

    # # --- Parse JSON ---
    # try:
    #     parsed = _parse_llm_json(raw_response)
    # except (json.JSONDecodeError, ValueError) as e:
    #     logger.warning(f"Failed to parse LLM JSON: {e} | Raw: {raw_response!r}")
    #     return ExtractionResponse(
    #         success=False,
    #         data=None,
    #         raw_text=text,
    #         confidence=0.0,
    #         error_message="AI returned malformed JSON. Please try rephrasing.",
    #     )

    # --- Validate with Pydantic ---
    try:
        extracted = ExtractedTransaction(
            amount=parsed.get("amount"),
            currency=parsed.get("currency", "INR"),
            description=parsed.get("description"),
            date=_parse_date(parsed.get("date")),
            category_hint=parsed.get("category_hint"),
            transaction_type=parsed.get('transaction_type')
        )
    except Exception as e:
        logger.warning(f"Pydantic validation failed: {e} | Parsed: {parsed}")
        return ExtractionResponse(
            success=False,
            data=None,
            raw_text=text,
            confidence=0.0,
            error_message="Extracted data failed validation.",
        )

    # --- Determine confidence & success ---
    raw_confidence: float = float(parsed.get("confidence", 0.0))
    confidence = max(0.0, min(1.0, raw_confidence))  

    # A result is only "successful" if we at least got an amount
    success = extracted.amount is not None

    if not success:
        logger.info(f"Low-confidence extraction for input: {text!r}")

    return ExtractionResponse(
        success=success,
        data=extracted if success else None,
        raw_text=text,
        confidence=confidence,
        error_message=None if success else "Could not determine the transaction amount.",
    )


if __name__ == '__main__':
    print('Running Fine')