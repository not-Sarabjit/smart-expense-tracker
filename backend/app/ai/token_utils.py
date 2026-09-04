import tiktoken

from app.core.exceptions import AITokenLimitError


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _get_encoding(model: str):
    """
    Return the tiktoken encoding for the given model name.
    Falls back to cl100k_base (used by GPT-4, Claude-compatible tokenizer)
    if the model is not explicitly recognized by tiktoken.
    """
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Some models are not in tiktoken's registry but cl100k_base
        # is a close enough approximation for budget/guard purposes.
        return tiktoken.get_encoding("cl100k_base")



def count_tokens(text: str, model: str = "openai/gpt-oss-20b") -> int:
    """
    Count the number of tokens in `text` for the given model.

    Args:
        text:  The string to tokenize (prompt, completion, or combined).
        model: Model name used to select the correct tokenizer.
               Defaults to openai/gpt-oss-20b.

    Returns:
        Integer token count.

    Example:
        count_tokens("Paid 340 for Zomato last night")  -> 8
    """
    encoding = _get_encoding(model)
    return len(encoding.encode(text))


def assert_within_limit(
    text: str,
    limit: int,
    model: str = "openai/gpt-oss-20b",
    label: str = "prompt",
) -> int:
    """
    Raise AITokenLimitError if `text` exceeds `limit` tokens.
    Returns the token count if the check passes (useful for logging).

    Args:
        text:   The string to check.
        limit:  Maximum allowed token count.
        model:  Model name for tokenizer selection.
        label:  Human-readable name shown in the error message
                (e.g. "system prompt", "user message", "combined prompt").

    Returns:
        Token count (int) if within limit.

    Raises:
        AITokenLimitError: if token count exceeds limit.

    Example:
        >>> assert_within_limit(long_prompt, limit=4096, label="extraction prompt")
    """
    token_count = count_tokens(text, model)

    if token_count > limit:
        raise AITokenLimitError(
            f"{label} exceeds token limit: "
            f"{token_count} tokens used, limit is {limit}."
        )

    return token_count


def estimate_cost_tokens(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "openai/gpt-oss-20b",
) -> float:
    """
    Rough cost estimate in dollars based on token counts.
    Prices are hardcoded — update when provider pricing changes.
    Last updated: 2025-09.

    Returns:
        Estimated cost in USD (float).
    """
    # Prices per 1 million tokens (input / output)
    PRICING = {
    "openai/gpt-oss-20b":        {"input": 0.075, "output": 0.30},
    "openai/gpt-oss-120b":       {"input": 0.15,  "output": 0.60},
    "qwen/qwen3.6-27b":          {"input": 0.60,  "output": 3.00},
    "qwen/qwen3.8-27b":          {"input": 0.80,  "output": 4.00},
    "openai/gpt-oss-safeguard-20b": {"input": 0.075, "output": 0.30},
    "meta-llama/llama-prompt-guard-2-22m": {"input": 0.03, "output": 0.03},
    "meta-llama/llama-prompt-guard-2-86m": {"input": 0.04, "output": 0.04},
}

    rates = PRICING.get(model, PRICING['openai/gpt-oss-20b'])
    input_cost  = (prompt_tokens     / 1_000_000) * rates["input"]
    output_cost = (completion_tokens / 1_000_000) * rates["output"]
    return round(input_cost + output_cost, 6)