import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.unit_of_work import UnitOfWork
from app.dependencies.auth import get_current_user
from app.dependencies.features import require_ai_enabled
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
)
from app.services.conversation_service import ConversationService

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
