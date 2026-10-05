# backend/app/tests/Unit/test_conversations.py
"""Step 1.2 — chat persistence: ownership, atomicity, cascade, JSON round-trip."""

import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import ConversationNotFoundException
from app.database.unit_of_work import UnitOfWork
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.conversation_service import ConversationService
from app.tests.conftest import TestingSessionLocal


def _make_user(db, email: str) -> User:
    """Create a user directly; auth is not what this module is testing."""
    user = User(
        email=email,
        first_name="Chat",
        last_name="Tester",
        hashed_password="not-a-real-hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_service(db) -> ConversationService:
    """Same wiring the Step 1.3 router DI factory will use."""
    return ConversationService(
        conversation_repository=ConversationRepository(db),
        message_repository=MessageRepository(db),
        uow=UnitOfWork(db),
    )


@pytest.fixture
def service(db):
    return _make_service(db)


@pytest.fixture
def user_a(db):
    return _make_user(db, "chat_a@example.com")


@pytest.fixture
def user_b(db):
    return _make_user(db, "chat_b@example.com")


def test_create_conversation_assigns_uuid_and_defaults(service, user_a):
    conversation = service.create_conversation(user_a.id)

    assert isinstance(conversation.id, uuid.UUID)
    assert conversation.user_id == user_a.id
    assert conversation.title is None
    assert conversation.archived is False
    assert conversation.created_at is not None
    assert conversation.updated_at is not None


def test_create_conversation_is_committed(service, user_a):
    """Visible from a separate session => the UnitOfWork really committed."""
    conversation = service.create_conversation(user_a.id, title="  Groceries  ")
    conversation_id = conversation.id

    with TestingSessionLocal() as other:
        stored = other.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        ).scalar_one()
        assert stored.title == "Groceries"  # stripped by _clean_title


def test_blank_title_is_stored_as_null(service, user_a):
    conversation = service.create_conversation(user_a.id, title="   ")
    assert conversation.title is None


def test_get_conversation_of_another_user_raises_not_found(service, user_a, user_b):
    conversation = service.create_conversation(user_a.id)

    with pytest.raises(ConversationNotFoundException) as exc:
        service.get_conversation(user_b.id, conversation.id)

    # 404, not 403 — never confirm that someone else's id exists.
    assert exc.value.status_code == 404


def test_unknown_conversation_id_raises_not_found(service, user_a):
    with pytest.raises(ConversationNotFoundException):
        service.get_conversation(user_a.id, uuid.uuid4())


def test_list_conversations_is_user_scoped_and_newest_first(service, user_a, user_b):
    first = service.create_conversation(user_a.id, title="first")
    second = service.create_conversation(user_a.id, title="second")
    service.create_conversation(user_b.id, title="other user")

    # Baseline: no activity yet, so creation order decides — newest first.
    assert [c.id for c in service.list_conversations(user_a.id)] == [
        second.id,
        first.id,
    ]

    # Activity on `first` should float it back to the top.
    service.add_message(user_a.id, first.id, MessageRole.user, "hello")

    listed = service.list_conversations(user_a.id)
    assert [c.id for c in listed] == [first.id, second.id]
    assert service.count_conversations(user_a.id) == 2


def test_timestamps_have_sub_second_precision(service, user_a):
    """Guards the ordering above: rows written in the same second must still
    be orderable, which CURRENT_TIMESTAMP alone cannot guarantee on SQLite."""
    conversations = [service.create_conversation(user_a.id) for _ in range(5)]

    created = [c.created_at for c in conversations]
    assert len(set(created)) == 5, "timestamps collided — precision lost"
    assert created == sorted(created), "creation order not reflected in created_at"


def test_archived_conversations_are_hidden_by_default(service, user_a):
    conversation = service.create_conversation(user_a.id)
    service.update_conversation(user_a.id, conversation.id, archived=True)

    assert service.list_conversations(user_a.id) == []
    assert service.count_conversations(user_a.id) == 0
    assert len(service.list_conversations(user_a.id, include_archived=True)) == 1


def test_add_message_persists_role_content_and_json_columns(service, user_a):
    conversation = service.create_conversation(user_a.id)

    message = service.add_message(
        user_a.id,
        conversation.id,
        MessageRole.assistant,
        content=None,
        tool_calls=[{"name": "query_transactions", "args": {"preset": "this_month"}}],
        meta={"model": "test-model", "total_tokens": 42, "latency_ms": 310},
    )

    with TestingSessionLocal() as other:
        stored = other.execute(
            select(Message).where(Message.id == message.id)
        ).scalar_one()
        assert stored.role == MessageRole.assistant  # str-enum compares to "assistant"
        assert stored.content is None
        assert stored.tool_calls[0]["name"] == "query_transactions"
        assert stored.meta["total_tokens"] == 42


def test_add_message_rejects_unknown_role(service, user_a):
    conversation = service.create_conversation(user_a.id)

    with pytest.raises(ValueError):
        service.add_message(user_a.id, conversation.id, "robot", "hi")


def test_add_message_to_another_users_conversation_is_rejected(
    service, user_a, user_b
):
    conversation = service.create_conversation(user_a.id)

    with pytest.raises(ConversationNotFoundException):
        service.add_message(user_b.id, conversation.id, MessageRole.user, "sneaky")

    assert service.count_messages(user_a.id, conversation.id) == 0


def test_messages_are_returned_in_insertion_order(service, user_a):
    conversation = service.create_conversation(user_a.id)
    for i in range(5):
        service.add_message(user_a.id, conversation.id, MessageRole.user, f"m{i}")

    messages = service.list_messages(user_a.id, conversation.id)
    assert [m.content for m in messages] == ["m0", "m1", "m2", "m3", "m4"]

    page_two = service.list_messages(user_a.id, conversation.id, limit=2, offset=2)
    assert [m.content for m in page_two] == ["m2", "m3"]


def test_get_recent_messages_returns_last_n_chronologically(service, user_a):
    conversation = service.create_conversation(user_a.id)
    for i in range(10):
        service.add_message(user_a.id, conversation.id, MessageRole.user, f"m{i}")

    recent = service.get_recent_messages(user_a.id, conversation.id, limit=3)
    assert [m.content for m in recent] == ["m7", "m8", "m9"]


def test_add_message_bumps_conversation_updated_at(service, user_a, db):
    conversation = service.create_conversation(user_a.id)
    before = conversation.updated_at

    service.add_message(user_a.id, conversation.id, MessageRole.user, "hello")
    db.refresh(conversation)

    assert conversation.updated_at >= before


def test_deleting_a_conversation_cascades_to_its_messages(service, user_a):
    conversation = service.create_conversation(user_a.id)
    service.add_message(user_a.id, conversation.id, MessageRole.user, "hello")
    service.add_message(user_a.id, conversation.id, MessageRole.assistant, "hi there")
    conversation_id = conversation.id

    service.delete_conversation(user_a.id, conversation_id)

    with TestingSessionLocal() as other:
        assert (
            other.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            ).scalar_one_or_none()
            is None
        )
        orphans = other.execute(
            select(Message).where(Message.conversation_id == conversation_id)
        ).scalars().all()
        assert orphans == []


def test_failed_message_insert_rolls_back_the_activity_bump(service, user_a, db):
    """Atomicity: content exceeding no constraint is hard to force on SQLite,
    so we fail inside the same UnitOfWork block via a bad role."""
    conversation = service.create_conversation(user_a.id)
    with TestingSessionLocal() as other:
        before = other.execute(
            select(Conversation).where(Conversation.id == conversation.id)
        ).scalar_one().updated_at

    with pytest.raises(ValueError):
        service.add_message(user_a.id, conversation.id, "not-a-role", "boom")

    with TestingSessionLocal() as other:
        after = other.execute(
            select(Conversation).where(Conversation.id == conversation.id)
        ).scalar_one()
        assert after.updated_at == before
        assert (
            other.execute(
                select(Message).where(Message.conversation_id == conversation.id)
            ).scalars().all()
            == []
        )


def test_user_conversations_relationship_is_bidirectional(service, user_a, db):
    """Both sides of the back_populates pair resolve without a reload."""
    conversation = service.create_conversation(user_a.id, title="Budget chat")

    db.refresh(user_a)
    assert [c.id for c in user_a.conversations] == [conversation.id]
    assert conversation.user.id == user_a.id


def test_deleting_a_user_cascades_to_conversations_and_messages(service, user_a, db):
    """Two-level cascade: User -> Conversation -> Message, nothing orphaned."""
    conversation = service.create_conversation(user_a.id)
    service.add_message(user_a.id, conversation.id, MessageRole.user, "hello")
    service.add_message(user_a.id, conversation.id, MessageRole.assistant, "hi")
    conversation_id = conversation.id
    user_id = user_a.id

    db.delete(user_a)
    db.commit()

    with TestingSessionLocal() as other:
        assert (
            other.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
            is None
        )
        assert (
            other.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            ).scalar_one_or_none()
            is None
        )
        assert (
            other.execute(
                select(Message).where(Message.conversation_id == conversation_id)
            )
            .scalars()
            .all()
            == []
        )