"""Regression tests for the bugs listed in PROJECT_CONTEXT §12 (B1–B11).

Each test failed before its fix landed (Step 0.4) and must keep passing.
"""

import time
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.exc import OperationalError

from app.api.main import app
from app.api.transaction import get_transaction_service
from app.core.config import get_settings
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.tests.conftest import register_and_login


def create_transaction(client, headers, **overrides):
    payload = {
        "amount": 10.00,
        "type": "expense",
        "description": "Test",
        "date": "2026-08-01",
    }
    payload.update(overrides)
    response = client.post("/api/v1/transactions", json=payload, headers=headers)
    assert response.status_code == 201, response.json()
    return response.json()


def current_user_id(db, email="usera@example.com") -> int:
    return UserRepository(db).get_by_email(email).id


# --------------------------------------------------------------------- B1


@pytest.mark.parametrize("field", ["type", "transaction_type"])
def test_b1_update_transaction_type(client, user_a_headers, field):
    """Changing income <-> expense used to crash with AttributeError (500)."""
    tx = create_transaction(client, user_a_headers)

    response = client.put(
        f"/api/v1/transactions/{tx['id']}", json={field: "income"}, headers=user_a_headers
    )

    assert response.status_code == 200
    assert response.json()["type"] == "income"


# --------------------------------------------------------------------- B2


def test_b2_monthly_summary_counts_every_transaction(client, db, user_a_headers):
    """The summary used to sum only the 50 most recent transactions."""
    user_id = current_user_id(db)
    repo = TransactionRepository(db)
    for day in range(1, 31):
        repo.create(Decimal("1.00"), "expense", "x", date(2026, 7, day), user_id)
        repo.create(Decimal("1.50"), "expense", "y", date(2026, 7, day), user_id)
    repo.create(Decimal("100.25"), "income", "salary", date(2026, 7, 31), user_id)
    # Outside the month — must be ignored
    repo.create(Decimal("999.00"), "expense", "z", date(2026, 8, 1), user_id)

    response = client.get(
        "/api/v1/transactions/summary", params={"year": 2026, "month": 7}, headers=user_a_headers
    )

    assert response.status_code == 200
    assert response.json() == {"income": 100.25, "expense": 75.0, "net": 25.25}


def test_b2_summary_of_empty_month_is_zero(client, user_a_headers):
    response = client.get(
        "/api/v1/transactions/summary", params={"year": 2026, "month": 1}, headers=user_a_headers
    )
    assert response.status_code == 200
    assert response.json() == {"income": 0, "expense": 0, "net": 0}


def test_b2_summary_rejects_invalid_month(client, user_a_headers):
    """month=13 used to reach date() and 500."""
    response = client.get(
        "/api/v1/transactions/summary", params={"year": 2026, "month": 13}, headers=user_a_headers
    )
    assert response.status_code == 422


# --------------------------------------------------------------------- B3


def test_b3_deleting_a_category_in_use_is_blocked(client, db, user_a_headers, category_id):
    """Deleting a category used to cascade-delete all of its transactions."""
    tx = create_transaction(client, user_a_headers, category_id=category_id)

    response = client.delete(f"/api/v1/categories/{category_id}", headers=user_a_headers)

    assert response.status_code == 409
    assert "1 transaction" in response.json()["message"]
    assert client.get(f"/api/v1/transactions/{tx['id']}", headers=user_a_headers).status_code == 200
    assert (
        client.get(f"/api/v1/categories/{category_id}", headers=user_a_headers).status_code == 200
    )


def test_b3_deleting_an_unused_category_still_works(client, user_a_headers, category_id):
    tx = create_transaction(client, user_a_headers, category_id=category_id)
    client.delete(f"/api/v1/transactions/{tx['id']}", headers=user_a_headers)

    response = client.delete(f"/api/v1/categories/{category_id}", headers=user_a_headers)

    assert response.status_code == 204
    assert (
        client.get(f"/api/v1/categories/{category_id}", headers=user_a_headers).status_code == 404
    )


def test_b3_orm_never_cascades_category_delete_to_transactions(db, client, user_a_headers):
    """Defence in depth: even a direct ORM delete must not take transactions with it."""
    user_id = current_user_id(db)
    category = Category(name="Temp", category_type="expense", user_id=user_id)
    db.add(category)
    db.commit()
    tx = TransactionRepository(db).create(
        Decimal("5"), "expense", "keep me", date(2026, 8, 1), user_id, category.id
    )

    db.delete(category)
    db.commit()

    assert db.get(Transaction, tx.id) is not None


# --------------------------------------------------------------------- B5


def test_b5_cannot_move_transaction_to_another_users_category(
    client, user_a_headers, user_b_headers
):
    """update_transaction didn't check category ownership."""
    b_category = client.post(
        "/api/v1/categories/create_category",
        json={"name": "B private", "category_type": "expense"},
        headers=user_b_headers,
    ).json()["id"]
    tx = create_transaction(client, user_a_headers)

    response = client.put(
        f"/api/v1/transactions/{tx['id']}",
        json={"category_id": b_category},
        headers=user_a_headers,
    )

    assert response.status_code == 403


def test_b5_cannot_move_transaction_to_missing_category(client, user_a_headers):
    tx = create_transaction(client, user_a_headers)

    response = client.put(
        f"/api/v1/transactions/{tx['id']}", json={"category_id": 9999}, headers=user_a_headers
    )

    assert response.status_code == 404


# --------------------------------------------------------------------- B6


def test_b6_create_rejects_category_of_the_other_type(client, user_a_headers, category_id):
    """An income transaction could be filed under an expense category."""
    response = client.post(
        "/api/v1/transactions",
        json={"amount": 5, "type": "income", "date": "2026-08-01", "category_id": category_id},
        headers=user_a_headers,
    )

    assert response.status_code == 422
    assert response.json()["error"] is True


def test_b6_update_type_rejects_mismatch_with_existing_category(
    client, user_a_headers, category_id
):
    tx = create_transaction(client, user_a_headers, category_id=category_id)

    response = client.put(
        f"/api/v1/transactions/{tx['id']}", json={"type": "income"}, headers=user_a_headers
    )

    assert response.status_code == 422


def test_b6_update_type_and_category_together(
    client, user_a_headers, category_id, income_category_id
):
    tx = create_transaction(client, user_a_headers, category_id=category_id)

    response = client.put(
        f"/api/v1/transactions/{tx['id']}",
        json={"type": "income", "category_id": income_category_id},
        headers=user_a_headers,
    )

    assert response.status_code == 200
    assert response.json()["type"] == "income"
    assert response.json()["category_id"] == income_category_id


# --------------------------------------------------------------------- B7


def test_b7_invalid_sort_by_is_a_validation_error(client, user_a_headers):
    """sort_by=foo used to raise KeyError -> 500."""
    response = client.get("/api/v1/transactions", params={"sort_by": "foo"}, headers=user_a_headers)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 201}, {"offset": -1}, {"sort_order": "sideways"}]
)
def test_b7_invalid_paging_params_are_rejected(client, user_a_headers, params):
    response = client.get("/api/v1/transactions", params=params, headers=user_a_headers)
    assert response.status_code == 422


def test_b7_pagination_with_total_count(client, db, user_a_headers):
    """The list was hard-capped at 50 rows with no way to get the rest."""
    user_id = current_user_id(db)
    repo = TransactionRepository(db)
    for i in range(1, 61):
        repo.create(Decimal(i), "expense", f"tx {i}", date(2026, 8, 1), user_id)

    seen = []
    for offset in (0, 25, 50):
        response = client.get(
            "/api/v1/transactions",
            params={"limit": 25, "offset": offset, "sort_by": "amount", "sort_order": "asc"},
            headers=user_a_headers,
        )
        assert response.status_code == 200
        assert response.headers["X-Total-Count"] == "60"
        seen.extend(Decimal(tx["amount"]) for tx in response.json())

    assert seen == [Decimal(i) for i in range(1, 61)]


def test_b7_total_count_respects_filters(client, user_a_headers):
    create_transaction(client, user_a_headers, type="expense")
    create_transaction(client, user_a_headers, type="income")

    response = client.get(
        "/api/v1/transactions", params={"transaction_type": "income"}, headers=user_a_headers
    )

    assert response.headers["X-Total-Count"] == "1"
    assert [tx["type"] for tx in response.json()] == ["income"]


# --------------------------------------------------------------------- B8


@pytest.fixture
def raw_client(client):
    """Same test DB as `client`, but returns 500s instead of re-raising server exceptions."""
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(get_transaction_service, None)


def test_b8_database_errors_do_not_leak_sql(raw_client, user_a_headers, caplog):
    def broken_service():
        raise OperationalError("SELECT hashed_password FROM users", {}, Exception("db down"))

    app.dependency_overrides[get_transaction_service] = broken_service

    response = raw_client.get("/api/v1/transactions", headers=user_a_headers)

    assert response.status_code == 503
    assert "SELECT" not in response.text
    assert response.json()["error"] is True
    assert any("Database error" in r.getMessage() and r.exc_info for r in caplog.records)


def test_b8_unhandled_errors_are_logged_but_not_leaked(raw_client, user_a_headers, caplog):
    def broken_service():
        raise RuntimeError("secret internal detail")

    app.dependency_overrides[get_transaction_service] = broken_service

    response = raw_client.get("/api/v1/transactions", headers=user_a_headers)

    assert response.status_code == 500
    assert response.json() == {
        "error": True,
        "message": "Internal server error",
        "status_code": 500,
    }
    assert any(
        "Unhandled exception" in r.getMessage() and r.exc_info and r.exc_info[0] is RuntimeError
        for r in caplog.records
    )


# --------------------------------------------------------------------- B9


def test_b9_token_expiry_is_utc_based(client):
    """exp used naive local time, so expiry was off by the machine's UTC offset."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "t@example.com", "first_name": "T", "last_name": "U", "password": "pw12345"},
    )
    token = client.post(
        "/api/v1/auth/login", json={"email": "t@example.com", "password": "pw12345"}
    ).json()["access_token"]

    settings = get_settings().auth
    claims = jwt.decode(token, settings.secret_key, algorithms=[settings.token_algorithm])
    expected = time.time() + settings.access_token_expire_minutes * 60

    assert abs(claims["exp"] - expected) < 60
    assert abs(claims["iat"] - time.time()) < 60


def test_b9_expired_token_is_rejected(client, db):
    headers = register_and_login(client, "exp@example.com")
    user_id = current_user_id(db, "exp@example.com")
    expired = AuthService(UserRepository(db))._create_access_token(user_id, expires_minutes=-1)

    assert client.get("/api/v1/transactions", headers=headers).status_code == 200
    response = client.get("/api/v1/transactions", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


# -------------------------------------------------------------------- B10


def test_b10_update_profile_applies_changes(db):
    """update_profile passed the updates dict positionally -> TypeError."""
    user = User(email="p@example.com", first_name="Old", last_name="Name", hashed_password="x")
    db.add(user)
    db.commit()

    updated = UserService(UserRepository(db)).update_profile(
        user.id, first_name="New", email="new@example.com"
    )

    assert updated.first_name == "New"
    assert updated.email == "new@example.com"
    assert updated.last_name == "Name"


# -------------------------------------------------------------------- B11


def test_b11_register_does_not_mask_unexpected_errors_as_401(raw_client, monkeypatch):
    """register() turned any ValueError into a misleading 401 'unauthorized'."""

    def boom(self, **kwargs):
        raise ValueError("unexpected")

    monkeypatch.setattr(AuthService, "register", boom)

    response = raw_client.post(
        "/api/v1/auth/register",
        json={"email": "v@example.com", "first_name": "V", "last_name": "E", "password": "pw"},
    )

    assert response.status_code == 500


# ------------------------------------------------------- default categories


def test_default_categories_are_listed_for_every_user(client, db, user_a_headers):
    """CategoryRepository used `Category.user_id is None` (always False), hiding defaults."""
    db.add(Category(name="Food", category_type="expense", user_id=None))
    db.commit()

    names = [c["name"] for c in client.get("/api/v1/categories/", headers=user_a_headers).json()]
    duplicate = client.post(
        "/api/v1/categories/create_category",
        json={"name": "food", "category_type": "expense"},
        headers=user_a_headers,
    )

    assert "Food" in names
    assert duplicate.status_code == 409
