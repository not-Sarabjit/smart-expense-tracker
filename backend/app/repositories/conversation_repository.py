import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.utils.date_utils import utcnow


class ConversationRepository:
    """Queries are user-scoped by construction: every read takes user_id."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, title: str | None = None) -> Conversation:
        """Insert a conversation and flush so its id/defaults are populated."""
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.flush()
        self.db.refresh(conversation)
        return conversation

    def get_by_id(self, conversation_id: uuid.UUID, user_id: int) -> Conversation | None:
        """Fetch one conversation owned by this user, else None."""
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_for_user(
        self,
        user_id: int,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """Most recently active first; id breaks ties so paging is stable."""
        stmt = select(Conversation).where(Conversation.user_id == user_id)
        if not include_archived:
            stmt = stmt.where(Conversation.archived.is_(False))
        stmt = (
            stmt.order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_for_user(self, user_id: int, include_archived: bool = False) -> int:
        """Total matching rows, for the X-Total-Count header in Step 1.3."""
        stmt = select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)
        if not include_archived:
            stmt = stmt.where(Conversation.archived.is_(False))
        return self.db.execute(stmt).scalar_one()

    def update(self, conversation: Conversation, **kwargs) -> Conversation:
        """Set attributes and flush. Unknown keys are ignored by the caller's design."""
        for key, value in kwargs.items():
            setattr(conversation, key, value)
        self.db.flush()
        self.db.refresh(conversation)
        return conversation

    def touch(self, conversation: Conversation) -> Conversation:
        """Bump updated_at to the current wall clock.

        `onupdate` only fires when some other column changes, so a pure
        'a message arrived' bump has to set the value explicitly. Uses
        utcnow() rather than func.now(): on Postgres now() is the transaction
        start time, so a long agent turn would stamp a stale timestamp and tie
        with every other write in the same transaction.
        """
        conversation.updated_at = utcnow()
        self.db.flush()
        self.db.refresh(conversation)
        return conversation

    def delete(self, conversation: Conversation) -> None:
        """Delete the conversation; the ORM cascade removes its messages."""
        self.db.delete(conversation)
        self.db.flush()
