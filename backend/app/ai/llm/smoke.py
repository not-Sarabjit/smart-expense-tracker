
from __future__ import annotations

import sys
import time

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from app.ai.llm.factory import build_resilient, describe_llm, get_chat_model
from app.core.config import get_settings
from app.core.exceptions import LLMNotConfiguredException



@tool
def get_total_spent(category: str, month: str) -> str:
    """Return how much the user spent in a category during a month (YYYY-MM)."""
    return "0.00"


def main() -> int:
    settings = get_settings()
    config = describe_llm(settings)
    print("LLM configuration:")
    for key, value in config.items():
        print(f"  {key:<16} {value}")

    if not config["api_key_set"]:
        print("\nLLM_API_KEY is not set in backend/.env — nothing to smoke-test.")
        return 1

    try:
        chat_model = get_chat_model(settings=settings)
    except LLMNotConfiguredException as exc:
        print(f"\nCould not build the model: {exc.message}")
        return 1

    print("\n[1/3] plain completion ...")
    started = time.perf_counter()
    reply = chat_model.invoke([HumanMessage(content="Reply with exactly: pong")])
    print(f"      -> {reply.content!r}  ({time.perf_counter() - started:.2f}s)")
    usage = getattr(reply, "usage_metadata", None)
    if usage:
        print(f"      tokens: {usage}")

    print("\n[2/3] streaming ...")
    chunks = 0
    for _ in chat_model.stream([HumanMessage(content="Count from 1 to 10.")]):
        chunks += 1
    print(f"      -> {chunks} chunks received")

    print("\n[3/3] tool calling (required for Phase 3) ...")
    with_tools = chat_model.bind_tools([get_total_spent])
    result = with_tools.invoke(
        [HumanMessage(content="How much did I spend on Food in 2026-09?")]
    )
    if result.tool_calls:
        print(f"      -> model requested: {result.tool_calls}")
    else:
        print("      !! no tool call returned — this model may not support tool calling")
        print(f"         content: {result.content!r}")
        return 1

    print("\n[4/4] fallback chain composes with tools bound ...")
    resilient = build_resilient(lambda model: model.bind_tools([get_total_spent]))
    print(f"      -> {type(resilient).__name__}")

    print("\nOK — gateway works.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
    