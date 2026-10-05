# backend/app/tests/Unit/test_chat_api.py
"""Step 1.3 — HTTP tests for the conversation REST API.

Chat routes sit behind the AI_ENABLED kill switch, which is false in tests, so
every test here overrides `require_ai_enabled` — except the one that proves the
switch works.
"""

import uuid

import pytest

from app.api.main import app
from app.database.unit_of_work import UnitOfWork
from app.dependencies.features import require_ai_enabled
from app.models.message import MessageRole
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.conversation_service import ConversationService

BASE = "/api/v1/chat/conversations"


@pytest.fixture(autouse=True)
def ai_enabled():
    """Bypass the AI_ENABLED kill switch for the chat routes."""
    app.dependency_overrides[require_ai_enabled] = lambda: None
    yield
    app.dependency_overrides.pop(require_ai_enabled, None)


def _user_id(client, headers) -> int:
    return client.get("/api/v1/users/me", headers=headers).json()["id"]


def _service(db) -> ConversationService:
    return ConversationService(
        conversation_repository=ConversationRepository(db),
        message_repository=MessageRepository(db),
        uow=UnitOfWork(db),
    )


def _create(client, headers, title=None):
    payload = {} if title is None else {"title": title}
    response = client.post(BASE, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------- create


def test_create_conversation_defaults(client, user_a_headers):
    body = _create(client, user_a_headers)
    uuid.UUID(body["id"])  # raises if it isn't a UUID
    assert body["title"] is None
    assert body["archived"] is False
    assert body["created_at"] and body["updated_at"]


def test_create_conversation_with_title_is_cleaned(client, user_a_headers):
    body = _create(client, user_a_headers, title="  Budget review  ")
    assert body["title"] == "Budget review"


def test_create_conversation_blank_title_becomes_null(client, user_a_headers):
    body = _create(client, user_a_headers, title="   ")
    assert body["title"] is None


def test_create_conversation_title_too_long_is_422(client, user_a_headers):
    response = client.post(BASE, json={"title": "x" * 201}, headers=user_a_headers)
    assert response.status_code == 422


def test_chat_requires_authentication(client):
    response = client.get(BASE)
    assert response.status_code in (401, 403)


# ----------------------------------------------------------------------------- list


def test_list_conversations_empty(client, user_a_headers):
    response = client.get(BASE, headers=user_a_headers)
    assert response.status_code == 200
    assert response.json() == []
    assert response.headers["X-Total-Count"] == "0"


def test_list_conversations_is_user_scoped_and_newest_first(
    client, user_a_headers, user_b_headers
):
    first = _create(client, user_a_headers, title="first")
    second = _create(client, user_a_headers, title="second")
    _create(client, user_b_headers, title="other user")

    response = client.get(BASE, headers=user_a_headers)
    assert response.status_code == 200
    ids = [row["id"] for row in response.json()]
    assert ids == [second["id"], first["id"]]
    assert response.headers["X-Total-Count"] == "2"


def test_list_conversations_pagination(client, user_a_headers):
    for index in range(3):
        _create(client, user_a_headers, title=f"c{index}")

    response = client.get(f"{BASE}?limit=1&offset=1", headers=user_a_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.headers["X-Total-Count"] == "3"  # total ignores paging


def test_list_conversations_rejects_bad_paging(client, user_a_headers):
    assert client.get(f"{BASE}?limit=0", headers=user_a_headers).status_code == 422
    assert client.get(f"{BASE}?limit=201", headers=user_a_headers).status_code == 422
    assert client.get(f"{BASE}?offset=-1", headers=user_a_headers).status_code == 422


def test_list_conversations_archive_filter(client, user_a_headers):
    kept = _create(client, user_a_headers, title="kept")
    archived = _create(client, user_a_headers, title="archived")
    client.patch(f"{BASE}/{archived['id']}", json={"archived": True}, headers=user_a_headers)

    default = client.get(BASE, headers=user_a_headers)
    assert [row["id"] for row in default.json()] == [kept["id"]]
    assert default.headers["X-Total-Count"] == "1"

    with_archived = client.get(f"{BASE}?include_archived=true", headers=user_a_headers)
    assert len(with_archived.json()) == 2
    assert with_archived.headers["X-Total-Count"] == "2"


# ------------------------------------------------------------------------- retrieve


def test_get_conversation(client, user_a_headers):
    created = _create(client, user_a_headers, title="mine")
    response = client.get(f"{BASE}/{created['id']}", headers=user_a_headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_other_users_conversation_is_404(client, user_a_headers, user_b_headers):
    created = _create(client, user_a_headers)
    response = client.get(f"{BASE}/{created['id']}", headers=user_b_headers)
    assert response.status_code == 404


def test_get_unknown_conversation_is_404(client, user_a_headers):
    response = client.get(f"{BASE}/{uuid.uuid4()}", headers=user_a_headers)
    assert response.status_code == 404


def test_malformed_conversation_id_is_422(client, user_a_headers):
    response = client.get(f"{BASE}/not-a-uuid", headers=user_a_headers)
    assert response.status_code == 422


# --------------------------------------------------------------------------- update


def test_patch_title_only_leaves_archived_untouched(client, user_a_headers):
    created = _create(client, user_a_headers, title="old")
    response = client.patch(
        f"{BASE}/{created['id']}", json={"title": "new"}, headers=user_a_headers
    )
    assert response.status_code == 200
    assert response.json()["title"] == "new"
    assert response.json()["archived"] is False


def test_patch_empty_body_is_422(client, user_a_headers):
    created = _create(client, user_a_headers)
    response = client.patch(f"{BASE}/{created['id']}", json={}, headers=user_a_headers)
    assert response.status_code == 422


def test_patch_other_users_conversation_is_404(client, user_a_headers, user_b_headers):
    created = _create(client, user_a_headers)
    response = client.patch(
        f"{BASE}/{created['id']}", json={"title": "hijacked"}, headers=user_b_headers
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------- delete


def test_delete_conversation(client, user_a_headers):
    created = _create(client, user_a_headers)
    assert client.delete(f"{BASE}/{created['id']}", headers=user_a_headers).status_code == 204
    assert client.get(f"{BASE}/{created['id']}", headers=user_a_headers).status_code == 404


def test_delete_other_users_conversation_is_404(client, user_a_headers, user_b_headers):
    created = _create(client, user_a_headers)
    assert client.delete(f"{BASE}/{created['id']}", headers=user_b_headers).status_code == 404
    assert client.get(f"{BASE}/{created['id']}", headers=user_a_headers).status_code == 200


# -------------------------------------------------------------------------- messages


def test_list_messages_is_chronological_and_paginated(client, db, user_a_headers):
    created = _create(client, user_a_headers)
    conversation_id = uuid.UUID(created["id"])
    user_id = _user_id(client, user_a_headers)

    service = _service(db)
    for index in range(3):
        service.add_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role=MessageRole.user if index % 2 == 0 else MessageRole.assistant,
            content=f"m{index}",
        )

    response = client.get(f"{BASE}/{created['id']}/messages", headers=user_a_headers)
    assert response.status_code == 200
    assert [row["content"] for row in response.json()] == ["m0", "m1", "m2"]
    assert response.headers["X-Total-Count"] == "3"

    page = client.get(
        f"{BASE}/{created['id']}/messages?limit=1&offset=2", headers=user_a_headers
    )
    assert [row["content"] for row in page.json()] == ["m2"]
    assert page.headers["X-Total-Count"] == "3"


def test_message_payload_round_trips_tool_calls_and_meta(client, db, user_a_headers):
    created = _create(client, user_a_headers)
    user_id = _user_id(client, user_a_headers)

    _service(db).add_message(
        user_id=user_id,
        conversation_id=uuid.UUID(created["id"]),
        role=MessageRole.assistant,
        content=None,
        tool_calls=[{"name": "query_transactions", "args": {"month": 9}}],
        meta={"model": "fake", "prompt_tokens": 12},
    )

    body = client.get(f"{BASE}/{created['id']}/messages", headers=user_a_headers).json()
    assert body[0]["content"] is None
    assert body[0]["role"] == "assistant"
    assert body[0]["tool_calls"][0]["name"] == "query_transactions"
    assert body[0]["meta"]["prompt_tokens"] == 12


def test_list_messages_of_other_users_conversation_is_404(
    client, user_a_headers, user_b_headers
):
    created = _create(client, user_a_headers)
    response = client.get(f"{BASE}/{created['id']}/messages", headers=user_b_headers)
    assert response.status_code == 404


# ------------------------------------------------------------------- the kill switch


def test_chat_is_503_when_ai_disabled(client, user_a_headers):
    app.dependency_overrides.pop(require_ai_enabled, None)
    response = client.get(BASE, headers=user_a_headers)
    assert response.status_code == 503
