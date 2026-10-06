import asyncio
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessageChunk
from langchain_core.runnables import Runnable
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.ai.agent.history import DEFAULT_MEMORY_WINDOW, message_text
from app.ai.agent.runner import prepare_turn, stream_turn
from app.ai.agent.titler import generate_title
from app.api.sse import SSE_HEADERS, SSEEvent, format_sse
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.rate_limit import RateLimitDecision
from app.core.request_context import get_request_id
from app.database.session import get_db
from app.database.unit_of_work import UnitOfWork
from app.dependencies.agent import get_agent_graph
from app.dependencies.auth import get_current_user
from app.dependencies.features import require_ai_enabled
from app.dependencies.llm import get_title_llm
from app.dependencies.rate_limit import rate_limit_chat_message
from app.models.message import MessageRole
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageCreate,
    MessageOut,
)
from app.services.conversation_service import ConversationService

logger = get_logger(__name__)


router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(require_ai_enabled)],
)


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    """Build a ConversationService whose repositories share one Session with the UoW."""
    return ConversationService(
        conversation_repository=ConversationRepository(db),
        message_repository=MessageRepository(db),
        uow=UnitOfWork(db),
    )


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: ConversationCreate | None = None,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """Create an empty conversation. A null title is auto-filled on first turn (Step 1.6)."""
    title = payload.title if payload is not None else None
    return service.create_conversation(user_id=current_user.id, title=title)


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    response: Response,
    include_archived: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """List the current user's conversations, most recently active first.

    Total matching rows are returned in the `X-Total-Count` header.
    """
    conversations = service.list_conversations(
        user_id=current_user.id,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    total = service.count_conversations(user_id=current_user.id, include_archived=include_archived)
    response.headers["X-Total-Count"] = str(total)
    return conversations


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """Fetch one conversation. Another user's id returns 404, never 403."""
    return service.get_conversation(user_id=current_user.id, conversation_id=conversation_id)


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """Rename and/or archive a conversation. Only the fields sent are changed."""
    fields = payload.model_dump(exclude_unset=True)
    return service.update_conversation(
        user_id=current_user.id, conversation_id=conversation_id, **fields
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> None:
    """Delete a conversation and, by ORM cascade, all of its messages."""
    service.delete_conversation(user_id=current_user.id, conversation_id=conversation_id)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageOut],
)
def list_messages(
    conversation_id: uuid.UUID,
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """Page through one transcript in insertion order (oldest first).

    Total message count is returned in the `X-Total-Count` header.
    """
    messages = service.list_messages(
        user_id=current_user.id,
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )
    total = service.count_messages(user_id=current_user.id, conversation_id=conversation_id)
    response.headers["X-Total-Count"] = str(total)
    return messages


@router.post(
    "/conversations/{conversation_id}/messages",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"content": {"text/event-stream": {}}, "description": "SSE stream"},
        429: {"description": "Rate limit exceeded"},
    },
    response_model=None,
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    graph: Runnable = Depends(get_agent_graph),
    title_llm: BaseChatModel = Depends(get_title_llm),
    settings: Settings = Depends(get_settings),
    rate_limit: RateLimitDecision = Depends(rate_limit_chat_message),
) -> StreamingResponse:
    """Send a message and stream the assistant's reply as Server-Sent Events.

    Async (the graph is async-only, D15), so **every** sync DB call is pushed to
    the thread pool with `run_in_threadpool` — a blocking call here would stall
    the whole event loop.

    Two phases:
      1. Pre-flight, before any bytes are sent: rate limit (429), ownership check
         (404), history load, persist the user's message. Failures here are
         normal HTTP errors. The rate limit runs first, as a dependency, so a
         throttled request costs no DB work and writes no message row.
      2. The stream. The status line is already gone, so failures from here on
         are reported as an `error` event inside the stream.
    """
    user_id = current_user.id

    # ---- phase 1: pre-flight (ordinary request, real status codes) ----------
    conversation = await run_in_threadpool(
        service.get_conversation, user_id, conversation_id
    )  # raises ConversationNotFoundException -> 404 for missing OR foreign

    # History must be read BEFORE the new row is inserted: prepare_turn appends
    # the new user message itself, and we don't want it replayed twice.
    history = await run_in_threadpool(
        service.get_recent_messages, user_id, conversation_id, DEFAULT_MEMORY_WINDOW
    )
    user_message = await run_in_threadpool(
        service.add_message,
        user_id,
        conversation_id,
        MessageRole.user,
        content=payload.content,
    )
    inputs = await run_in_threadpool(
        prepare_turn,
        current_user,
        history,
        payload.content,
        conversation_id=conversation.id,
    )

    # Snapshot everything the generator needs as plain values. The generator
    # runs after the handler returns; we don't want it touching ORM objects.
    user_message_id = user_message.id
    needs_title = conversation.title is None
    prompt_version = inputs.context.prompt_version
    request_id = get_request_id()

    logger.info(
        "chat.turn_started",
        conversation_id=str(conversation_id),
        user_message_id=user_message_id,
        prompt_version=prompt_version,
        history_messages=len(history),
    )

    # ---- phase 2: the stream ------------------------------------------------
    async def event_stream() -> AsyncIterator[str]:
        started = time.perf_counter()
        accumulated: AIMessageChunk | None = None

        try:
            yield format_sse(
                SSEEvent.message_start,
                {
                    "conversation_id": str(conversation_id),
                    "user_message_id": user_message_id,
                    "prompt_version": prompt_version,
                },
            )

            async for chunk in stream_turn(inputs, graph=graph):
                accumulated = chunk if accumulated is None else accumulated + chunk
                text = message_text(chunk)
                if text:
                    yield format_sse(SSEEvent.token, {"text": text})

            latency_ms = int((time.perf_counter() - started) * 1000)
            final_text = message_text(accumulated) if accumulated is not None else ""

            usage = None
            model_name = settings.llm.model
            if accumulated is not None:
                if accumulated.usage_metadata:
                    usage = {
                        "input_tokens": accumulated.usage_metadata.get("input_tokens"),
                        "output_tokens": accumulated.usage_metadata.get("output_tokens"),
                        "total_tokens": accumulated.usage_metadata.get("total_tokens"),
                    }
                # The answer may have come from a fallback model, not the primary.
                model_name = accumulated.response_metadata.get("model_name") or model_name

            meta = {
                "model": model_name,
                "provider": settings.llm.provider,
                "prompt_version": prompt_version,
                "latency_ms": latency_ms,
                "usage": usage,
                "request_id": request_id,
            }
            assistant_message = await run_in_threadpool(
                service.add_message,
                user_id,
                conversation_id,
                MessageRole.assistant,
                content=final_text or None,
                meta=meta,
            )

            title = None
            if needs_title:
                title = await generate_title(title_llm, payload.content)
                if title:
                    await run_in_threadpool(
                        service.update_conversation,
                        user_id,
                        conversation_id,
                        title=title,
                    )

            logger.info(
                "chat.turn_finished",
                conversation_id=str(conversation_id),
                message_id=assistant_message.id,
                latency_ms=latency_ms,
                output_chars=len(final_text),
                usage=usage,
            )

            yield format_sse(
                SSEEvent.message_end,
                {
                    "message_id": assistant_message.id,
                    "model": model_name,
                    "usage": usage,
                    "latency_ms": latency_ms,
                    "title": title,
                },
            )

        except asyncio.CancelledError:
            # Client hung up mid-answer. The user's message is already saved;
            # the partial assistant reply is dropped. Step 11.4 does this properly.
            logger.info("chat.turn_cancelled", conversation_id=str(conversation_id))
            raise
        except Exception:
            logger.exception("chat.turn_failed", conversation_id=str(conversation_id))
            yield format_sse(
                SSEEvent.error,
                {
                    "message": "The assistant could not finish this message. Please try again.",
                    "request_id": request_id,
                },
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        # FastAPI does not merge dependency-set headers into a Response the handler
        # returns itself, so the rate-limit budget is attached explicitly here.
        headers={**SSE_HEADERS, **rate_limit.as_headers()},
    )
