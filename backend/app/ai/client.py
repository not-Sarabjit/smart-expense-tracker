import json
import groq
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

from app.core.config import settings
from app.core.exceptions import AIServiceError, AIRateLimitError, AITokenLimitError

logger = logging.getLogger(__name__)


class AIClient:
    """
    Swap the provider here and nothing else in the codebase changes.
    """

    def __init__(self):
        self._client = groq.Groq(api_key=settings.AI_API_KEY)
        self.model = settings.AI_MODEL
        self.max_tokens = settings.AI_MAX_TOKENS
        self.temperature = settings.AI_TEMPERATURE

    @retry(
        retry=retry_if_exception_type(AIServiceError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def complete(
        self,
        prompt: str,
        system: str = "You are a helpful financial assistant.",
        max_tokens: int = None,
    ) -> str:
        """
        Send a prompt and return the text response.

        Args:
            prompt:     The user message.
            system:     The system prompt (role/instructions for the model).
            max_tokens: Override the default max_tokens from settings.

        Returns:
            The model's text response as a string.

        Raises:
            AIRateLimitError:  On 429 from the provider.
            AITokenLimitError: If the prompt exceeds the context window.
            AIServiceError:    On any other provider error after 3 retries.
        """
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content

        except groq.RateLimitError as e:
            raise AIRateLimitError()
        
        except groq.BadRequestError as e:
            # context_length_exceeded surfaces as a BadRequestError
            if "too long" in str(e).lower() or "context" in str(e).lower():
                raise AITokenLimitError(
                    message=str(e)
                )
            raise AIServiceError(message=str(e), original_error=e)
        
        except groq.APIStatusError as e:
            logger.error("Groq API error: %s — %s", e.status_code, e.message)
            raise AIServiceError(
                message=f"Provider returned {e.status_code}.",
            )
        except groq.APIConnectionError as e:
            logger.error("Groq connection error: %s", str(e))
            raise AIServiceError(
                message="Could not reach AI provider."
            )

    def complete_json(
        self,
        prompt: str,
        system: str = "You are a helpful financial assistant. Always respond with valid JSON only.",
        max_tokens: int = None,
    ) -> dict:
        """
        Like complete(), but parses and returns the response as a dict.
        Adds JSON enforcement to the system prompt automatically.

        Raises:
            AIServiceError: If the model returns non-parseable JSON after retries.
        """
        raw = self.complete(prompt=prompt, system=system, max_tokens=max_tokens)

        # Strip markdown fences if the model wraps the JSON anyway
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response: %s\nRaw: %s", e, raw)
            raise AIServiceError(
                message=f"Model returned invalid JSON: {e}"
            )


# Module-level singleton — import this everywhere instead of instantiating AIClient()
ai_client = AIClient()