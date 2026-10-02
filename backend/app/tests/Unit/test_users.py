"""GET/PATCH /api/v1/users/me and the Step 0.7 schema additions."""

import time
from datetime import date
from decimal import Decimal

import pytest

from app.database.unit_of_work import UnitOfWork
from app.models.transaction import TransactionSource
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.transaction_service import TransactionService

ME = "/api/v1/users/me"


def test_me_returns_profile_with_default_preferences(client, user_a_headers):
    response = client.get(ME, headers=user_a_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "usera@example.com"
    assert body["currency"] == "INR"
    assert body["timezone"] == "Asia/Kolkata"
    assert "hashed_password" not in body


def test_me_requires_auth(client):
    assert client.get(ME).status_code == 401
    assert client.patch(ME, json={"currency": "USD"}).status_code == 401


def test_patch_me_updates_preferences(client, user_a_headers):
    response = client.patch(
        ME,
        json={"currency": "usd", "timezone": "Europe/London", "first_name": "Ann"},
        headers=user_a_headers,
    )

    assert response.status_code == 200
    assert response.json()["currency"] == "USD"
    assert response.json()["timezone"] == "Europe/London"
    assert response.json()["first_name"] == "Ann"
    # persisted
    assert client.get(ME, headers=user_a_headers).json()["timezone"] == "Europe/London"


def test_patch_me_partial_update_leaves_other_fields(client, user_a_headers):
    client.patch(ME, json={"currency": "EUR"}, headers=user_a_headers)

    body = client.get(ME, headers=user_a_headers).json()
    assert body["currency"] == "EUR"
    assert body["timezone"] == "Asia/Kolkata"


@pytest.mark.parametrize(
    "payload",
    [
        {"currency": "RUPEES"},
        {"currency": "U1D"},
        {"timezone": "Mars/Olympus"},
        {"timezone": "../etc/passwd"},
        {"first_name": "   "},
    ],
)
def test_patch_me_rejects_invalid_values(client, user_a_headers, payload):
    response = client.patch(ME, json=payload, headers=user_a_headers)
    assert response.status_code == 422


def test_patch_me_cannot_change_email(client, user_a_headers):
    client.patch(ME, json={"email": "hijack@example.com"}, headers=user_a_headers)

    assert client.get(ME, headers=user_a_headers).json()["email"] == "usera@example.com"


def test_patch_me_only_changes_the_caller(client, user_a_headers, user_b_headers):
    client.patch(ME, json={"currency": "JPY"}, headers=user_a_headers)

    assert client.get(ME, headers=user_b_headers).json()["currency"] == "INR"


def test_register_response_includes_preferences(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "p@example.com", "first_name": "P", "last_name": "Q", "password": "pw123"},
    )
    assert response.json()["currency"] == "INR"
    assert response.json()["timezone"] == "Asia/Kolkata"


# ------------------------------------------------------------ transactions


def test_api_transactions_are_marked_manual_and_have_updated_at(client, user_a_headers):
    response = client.post(
        "/api/v1/transactions",
        json={"amount": 5, "type": "expense", "date": "2026-08-01"},
        headers=user_a_headers,
    )

    body = response.json()
    assert body["source"] == "manual"
    assert body["updated_at"] is not None


def test_updated_at_moves_on_update(client, user_a_headers):
    created = client.post(
        "/api/v1/transactions",
        json={"amount": 5, "type": "expense", "date": "2026-08-01"},
        headers=user_a_headers,
    ).json()
    time.sleep(1.1)  # SQLite CURRENT_TIMESTAMP has 1-second resolution

    updated = client.put(
        f"/api/v1/transactions/{created['id']}", json={"amount": 6}, headers=user_a_headers
    ).json()

    assert updated["updated_at"] > created["updated_at"]
    assert updated["created_at"] == created["created_at"]


def test_service_records_import_source(db, client, user_a_headers):
    user_id = UserRepository(db).get_by_email("usera@example.com").id
    service = TransactionService(TransactionRepository(db), CategoryRepository(db), UnitOfWork(db))

    [tx] = service.create_transactions(
        user_id,
        [{"amount": "9.99", "transaction_type": "expense", "date": date(2026, 8, 1)}],
        source=TransactionSource.import_,
    )

    assert tx.source == TransactionSource.import_
    assert tx.amount == Decimal("9.99")
    response = client.get(f"/api/v1/transactions/{tx.id}", headers=user_a_headers)
    assert response.json()["source"] == "import"
