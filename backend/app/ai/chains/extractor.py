from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.ai.llm import get_llm
from app.schemas.ai import ExtractedTransaction
from langchain_core.exceptions import OutputParserException
from groq import RateLimitError, APIStatusError
from app.core.exceptions import AIParseError, AIRateLimitError, AIContextTooLongError, AIServiceError
import logging

logger = logging.getLogger(__name__)

_parser = JsonOutputParser(pydantic_object=ExtractedTransaction)

_EXTRACTION_PROMPT = PromptTemplate(
    template="""You are a financial transaction extractor. Extract transaction details from the user's text.

Respond ONLY with valid JSON matching this exact schema — no explanation, no markdown, no extra text:
{format_instructions}

Rules:
- amount must be a positive float
- category must be one of: Food, Transport, Shopping, Entertainment, Bills, Health, Other
- date must be YYYY-MM-DD format or null if not mentioned
- confidence is your certainty from 0.0 to 1.0

User text: {text}""",
    input_variables=["text"],
    partial_variables={"format_instructions": _parser.get_format_instructions()},
)

_extractor_chain = _EXTRACTION_PROMPT | get_llm() | _parser


def extract_transaction(text: str) -> ExtractedTransaction:
    """
    Extract a structured transaction from natural language text.

    Args:
        text: Raw user input e.g. "Spent 450 on lunch at Zomato"

    Returns:
        ExtractedTransaction pydantic object

    Raises:
        AIParseError: If the LLM returns invalid or unparseable JSON
    """
    try:
        result = _extractor_chain.invoke({"text": text})
        # JsonOutputParser returns a dict; validate via Pydantic
        if isinstance(result, dict):
            return ExtractedTransaction(**result)
        return result
    except RateLimitError:
        raise AIRateLimitError()

    except OutputParserException as e:
        logger.error(f"LLM returned unparseable JSON for input '{text}': {e}")
        raise AIParseError(f"Could not parse transaction from: {text}")

    except APIStatusError as e:
        if "context_length" in str(e).lower() or "too long" in str(e).lower():
            raise AIContextTooLongError()
        logger.error(f"Groq API error: {e}")
        raise AIServiceError()

    except Exception as e:
        logger.error(f"Unexpected error in extract_transaction: {e}")
        raise AIServiceError(f"Unexpected AI error: {str(e)}")