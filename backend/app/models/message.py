import enum

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from app.utils.date_utils import utcnow
from app.database.base import Base

# JSONB on Postgres (binary, indexable); plain JSON on SQLite for the test suite.
JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class MessageRole(str, enum.Enum):
    """Who produced the message. Stored as a plain string :
    the set of roles will grow, and VARCHAR grows without a migration.

    Because this subclasses `str`, `message.role == MessageRole.user` is True
    for a value read back from the DB. Always store `.value`, never `str(...)`.
    """

    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"


class Message(Base):
    """One message. Integer PK: never addressed by URL, high volume, and the
    monotonic id gives free chronological ordering + keyset pagination."""

    __tablename__ = "messages"

    id = Column(
        BigInteger().with_variant(Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    conversation_id = Column(
        Uuid(), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(16), nullable=False)
    # Nullable: an assistant turn that only calls tools has no text content.
    content = Column(Text, nullable=True)

    tool_calls = Column(JSONVariant, nullable=True)

    meta = Column(JSONVariant, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=utcnow, server_default=func.now()
    )

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        # Paging one conversation's transcript in insertion order.
        Index("ix_messages_conversation_id_id", "conversation_id", "id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Message id={self.id} role={self.role}>"