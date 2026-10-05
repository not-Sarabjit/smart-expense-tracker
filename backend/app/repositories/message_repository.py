import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.message import Message, MessageRole


class MessageRepository:
    """Messages are always reached through a conversation the caller has
    already proved ownership of, so these methods take conversation_id only."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        conversation_id: uuid.UUID,
        role: MessageRole | str,
        content: str | None = None,
        tool_calls: list | dict | None = None,
        meta: dict | None = None,
    ) -> Message:
        """Insert one message. `role` is coerced through MessageRole so an
        invalid role fails here rather than at read time."""
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole(role).value,
            content=content,
            tool_calls=tool_calls,
            meta=meta,
        )
        self.db.add(message)
        self.db.flush()
        self.db.refresh(message)
        return message

    def get_for_conversation(
        self,
        conversation_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """Oldest first — the order a transcript is read in."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_for_conversation(self, conversation_id: uuid.UUID) -> int:
        """Total messages in the conversation."""
        stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        return self.db.execute(stmt).scalar_one()

    def get_recent(self, conversation_id: uuid.UUID, limit: int = 20) -> list[Message]:
        """The last N messages in chronological order.

        This is the short-term memory window loaded into AgentState in Step 1.5:
        take the newest N in the database, then reverse in Python so the model
        reads them oldest-first.
        """
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(limit)
        )
        rows = list(self.db.execute(stmt).scalars().all())
        rows.reverse()
        return rows
