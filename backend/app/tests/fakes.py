"""Test doubles — the only models the suite is ever allowed to talk to.

Two kinds live here:

* **Library fakes** (``GenericFakeChatModel`` et al. from langchain-core) are
  re-exported for convenience. They are maintained by LangChain, so they stay
  correct across upgrades — use them whenever a scripted reply is all you need.
* **:class:`ScriptedChatModel`** is ours, for the four things the library fakes
  cannot express: ``usage_metadata``, a chosen ``model_name``, failing on a
  specific call (or part-way through a stream), and recording the exact message
  list it was handed.

``FakeGraph``/``FakeTitleModel`` (Step 1.6) stand in for the *compiled graph*.
``ScriptedChatModel`` stands in one layer deeper, for the *model*, so the real
graph, runner, prompt loader and history replay all execute for real.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any

from langchain_core.language_models import (
    BaseChatModel,
    FakeMessagesListChatModel,
    GenericFakeChatModel,
    ParrotFakeChatModel,
)
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

__all__ = [
    "DEFAULT_USAGE",
    "FakeGraph",
    "FakeMessagesListChatModel",
    "FakeTitleModel",
    "GenericFakeChatModel",
    "ParrotFakeChatModel",
    "ScriptedChatModel",
]

#: Token counts every scripted reply reports unless a test overrides them.
DEFAULT_USAGE: dict[str, int] = {"input_tokens": 11, "output_tokens": 3, "total_tokens": 14}


class ScriptedChatModel(BaseChatModel):
    """A real ``BaseChatModel`` that answers from a script instead of a provider.

    ``responses`` is consumed one entry per call; the last entry is reused once
    exhausted, so a one-entry script answers every turn the same way. An entry
    may be:

    * ``str``        -> that text as an ``AIMessage``
    * ``AIMessage``  -> used as-is (tool calls, metadata preserved)
    * ``Exception``  -> raised on that call (provider outage, fallback tests)
    * ``callable``   -> called with the message list, returns one of the above

    Streaming is implemented, so LangGraph's ``stream_mode="messages"`` sees
    genuine token chunks exactly as it would from Groq: LangChain switches
    ``ainvoke`` to the streaming path whenever a streaming callback is attached,
    which is what the agent node relies on in production.
    """

    responses: list[Any] = Field(default_factory=lambda: ["ok"])
    #: Characters per streamed chunk. Small values make token counts assertable.
    chunk_size: int = 4
    #: Reported on the final chunk. ``None`` mimics a provider that sends none.
    usage: dict[str, int] | None = Field(default_factory=lambda: dict(DEFAULT_USAGE))
    #: Lands in ``response_metadata["model_name"]`` — what the route records as `model`.
    model_name: str = "scripted-model"
    #: Raise part-way through a stream, after this many chunks have been yielded.
    fail_after_chunks: int | None = None
    #: Every message list this model was handed, in order. The spy half of the fake.
    calls: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def last_call(self) -> list[BaseMessage]:
        return self.calls[-1]

    def _next_message(self, messages: Sequence[BaseMessage]) -> AIMessage:
        """Record the call, then resolve this call's scripted reply."""
        self.calls.append(list(messages))
        item = self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]

        if isinstance(item, BaseException):
            raise item
        if callable(item):
            item = item(list(messages))
        if isinstance(item, str):
            item = AIMessage(content=item)

        return AIMessage(
            content=item.content,
            tool_calls=list(getattr(item, "tool_calls", []) or []),
            usage_metadata=item.usage_metadata or self.usage,
            response_metadata={"model_name": self.model_name, **(item.response_metadata or {})},
        )

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._next_message(messages))])

    def _stream(
        self, messages, stop=None, run_manager=None, **kwargs
    ) -> Iterator[ChatGenerationChunk]:
        message = self._next_message(messages)
        text = message.content if isinstance(message.content, str) else ""
        pieces = [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)] or [
            ""
        ]

        for index, piece in enumerate(pieces):
            if self.fail_after_chunks is not None and index >= self.fail_after_chunks:
                raise RuntimeError("scripted mid-stream failure")

            last = index == len(pieces) - 1
            chunk = ChatGenerationChunk(
                message=AIMessageChunk(
                    content=piece,
                    # Usage and model name arrive with the final chunk, like a real provider.
                    usage_metadata=message.usage_metadata if last else None,
                    response_metadata=message.response_metadata if last else {},
                )
            )
            if run_manager is not None:
                run_manager.on_llm_new_token(piece, chunk=chunk)
            yield chunk


class FakeGraph:
    """Step 1.6 double for a *compiled graph*: only `astream` is used."""

    def __init__(self, pieces: list[str], usage: dict | None = None):
        self.pieces = pieces
        self.usage = usage or dict(DEFAULT_USAGE)
        self.calls: list = []

    async def astream(self, state, *, context=None, stream_mode=None, **kwargs):
        self.calls.append((state, context, stream_mode))
        meta = {"langgraph_node": "agent"}
        for index, piece in enumerate(self.pieces):
            last = index == len(self.pieces) - 1
            yield (
                AIMessageChunk(
                    content=piece,
                    usage_metadata=self.usage if last else None,
                    response_metadata={"model_name": "fake-model"} if last else {},
                ),
                meta,
            )


class FakeTitleModel:
    """Step 1.6 double for the small title model."""

    def __init__(self, title: str = "Groceries in September"):
        self.title = title
        self.calls = 0

    async def ainvoke(self, messages, **kwargs):
        self.calls += 1
        return AIMessage(content=f'"{self.title}."')
