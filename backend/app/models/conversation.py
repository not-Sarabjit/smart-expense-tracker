# backend/app/models/conversation.py
"""Conversation model — one chat thread between a user and the assistant."""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    false,
    func,
)
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.utils.date_utils import utcnow


class Conversation(Base):
    """A chat thread. The id is a UUID because it is exposed in URLs and will
    become the LangGraph `thread_id` in Phase 4."""

    __tablename__ = "conversations"

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # NULL until the first turn is auto-titled (Step 1.6).
    title = Column(String(200), nullable=True)
    archived = Column(Boolean, nullable=False, default=False, server_default=false())
    # Python-side default gives microsecond precision on both SQLite and
    # Postgres; server_default remains as the safety net for non-ORM writes.
    created_at = Column(DateTime, nullable=False, default=utcnow, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )

    user = relationship("User", back_populates="conversations")
    # No passive_deletes: SQLite needs PRAGMA foreign_keys=ON for ON DELETE
    # CASCADE, which the test suite does not set. Letting the ORM delete the
    # children explicitly keeps behaviour identical on Postgres and SQLite.
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )

    __table_args__ = (
        # Listing a user's conversations, newest activity first.
        Index("ix_conversations_user_id_updated_at", "user_id", "updated_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Conversation id={self.id} user_id={self.user_id}>"
