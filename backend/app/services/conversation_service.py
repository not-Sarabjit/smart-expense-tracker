import uuid

from app.core.exceptions import ConversationNotFoundException
from app.core.logging import get_logger
from app.database.unit_of_work import UnitOfWork
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository

logger = get_logger(__name__)

MAX_TITLE_LENGTH = 200


class ConversationService:
    """Messages are part of the conversation aggregate, so one service owns both.

    Every method takes user_id explicitly — ownership is enforced by passing it
    down, never by a global context.
    """

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        uow: UnitOfWork,
    ):
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository
        self.uow = uow

    # ------------------------------------------------------------------ reads

    def get_conversation(
        self, user_id: int, conversation_id: uuid.UUID
    ) -> Conversation:
        """Return the user's conversation or raise 404 (also for other users')."""
        conversation = self.conversation_repository.get_by_id(conversation_id, user_id)
        if conversation is None:
            raise ConversationNotFoundException()
        return conversation

    def list_conversations(
        self,
        user_id: int,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """Page through the user's conversations, most recent activity first."""
        return self.conversation_repository.get_all_for_user(
            user_id,
            include_archived=include_archived,
            limit=limit,
            offset=offset,
        )

    def count_conversations(self, user_id: int, include_archived: bool = False) -> int:
        """Total conversations matching the same filters as list_conversations."""
        return self.conversation_repository.count_for_user(
            user_id, include_archived=include_archived
        )

    def list_messages(
        self,
        user_id: int,
        conversation_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """Transcript page, oldest first. Ownership checked before reading."""
        self.get_conversation(user_id, conversation_id)
        return self.message_repository.get_for_conversation(
            conversation_id, limit=limit, offset=offset
        )

    def count_messages(self, user_id: int, conversation_id: uuid.UUID) -> int:
        """Total messages in the conversation, for pagination headers."""
        self.get_conversation(user_id, conversation_id)
        return self.message_repository.count_for_conversation(conversation_id)

    def get_recent_messages(
        self, user_id: int, conversation_id: uuid.UUID, limit: int = 20
    ) -> list[Message]:
        """Short-term memory window for the agent (Step 1.5), chronological."""
        self.get_conversation(user_id, conversation_id)
        return self.message_repository.get_recent(conversation_id, limit=limit)

    # ----------------------------------------------------------------- writes

    def create_conversation(
        self, user_id: int, title: str | None = None
    ) -> Conversation:
        """Create an (optionally titled) conversation. Title is auto-set in Step 1.6."""
        title = self._clean_title(title)
        with self.uow:
            conversation = self.conversation_repository.create(user_id, title=title)
            logger.info(
                "conversation.created",
                conversation_id=str(conversation.id),
                has_title=title is not None,
            )
            return conversation

    def update_conversation(
        self,
        user_id: int,
        conversation_id: uuid.UUID,
        title: str | None = None,
        archived: bool | None = None,
    ) -> Conversation:
        """Rename and/or archive. Only the fields passed are changed."""
        with self.uow:
            conversation = self.get_conversation(user_id, conversation_id)
            updates: dict = {}
            if title is not None:
                updates["title"] = self._clean_title(title)
            if archived is not None:
                updates["archived"] = archived
            if not updates:
                return conversation
            conversation = self.conversation_repository.update(conversation, **updates)
            logger.info(
                "conversation.updated",
                conversation_id=str(conversation.id),
                fields=sorted(updates),
            )
            return conversation

    def delete_conversation(self, user_id: int, conversation_id: uuid.UUID) -> None:
        """Hard-delete the conversation and, by cascade, all of its messages."""
        with self.uow:
            conversation = self.get_conversation(user_id, conversation_id)
            self.conversation_repository.delete(conversation)
            logger.info("conversation.deleted", conversation_id=str(conversation_id))

    def add_message(
        self,
        user_id: int,
        conversation_id: uuid.UUID,
        role: MessageRole | str,
        content: str | None = None,
        tool_calls: list | dict | None = None,
        meta: dict | None = None,
    ) -> Message:
        """Append a message and bump the conversation's activity timestamp.

        Both writes happen in one transaction: a conversation can never show
        'active 2 minutes ago' for a message that failed to insert.
        """
        with self.uow:
            conversation = self.get_conversation(user_id, conversation_id)
            message = self.message_repository.create(
                conversation_id=conversation.id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                meta=meta,
            )
            self.conversation_repository.touch(conversation)
            logger.info(
                "message.created",
                conversation_id=str(conversation.id),
                message_id=message.id,
                role=message.role,
                content_length=len(content or ""),
            )
            return message

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _clean_title(title: str | None) -> str | None:
        """Strip whitespace, truncate to the column width, treat blank as None."""
        if title is None:
            return None
        title = title.strip()
        if not title:
            return None
        return title[:MAX_TITLE_LENGTH]