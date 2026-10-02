"""Unit of work: several writes commit together or not at all (Step 0.6)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import CategoryNotFoundException
from app.database.unit_of_work import UnitOfWork
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.transaction_service import TransactionService
from app.tests.conftest import TestingSessionLocal


@pytest.fixture
def user_id(db) -> int:
    user = User(email="uow@example.com", first_name="U", last_name="W", hashed_password="x")
    db.add(user)
    db.commit()
    return user.id


def committed_transaction_count() -> int:
    """Counts rows through a separate connection, so only committed data is visible."""
    other = TestingSessionLocal()
    try:
        return other.scalar(select(func.count(Transaction.id)))
    finally:
        other.close()


def make_service(db) -> TransactionService:
    return TransactionService(TransactionRepository(db), CategoryRepository(db), UnitOfWork(db))


def item(amount="10.00", **overrides) -> dict:
    data = {
        "amount": amount,
        "transaction_type": "expense",
        "description": "batch",
        "date": date(2026, 8, 1),
        "category_id": None,
    }
    data.update(overrides)
    return data


def test_failing_third_insert_rolls_back_the_first_two(db, user_id):
    """A DB-level failure on the 3rd write undoes writes 1 and 2."""
    repo = TransactionRepository(db)

    with pytest.raises(IntegrityError), UnitOfWork(db):
        repo.create(Decimal("1"), "expense", "first", date(2026, 8, 1), user_id)
        repo.create(Decimal("2"), "expense", "second", date(2026, 8, 1), user_id)
        repo.create(None, "expense", "third: amount is NOT NULL", date(2026, 8, 1), user_id)

    assert committed_transaction_count() == 0
    assert db.scalar(select(func.count(Transaction.id))) == 0


def test_batch_create_is_all_or_nothing(db, user_id):
    """A business-rule failure on the 3rd item of a batch saves nothing."""
    service = make_service(db)

    with pytest.raises(CategoryNotFoundException):
        service.create_transactions(
            user_id, [item("1.00"), item("2.00"), item("3.00", category_id=9999)]
        )

    assert committed_transaction_count() == 0


def test_batch_create_commits_every_item(db, user_id):
    created = make_service(db).create_transactions(user_id, [item("1.00"), item("2.50")])

    assert [t.amount for t in created] == [Decimal("1.00"), Decimal("2.50")]
    assert committed_transaction_count() == 2


def test_nested_blocks_commit_only_at_the_outermost_level(db, user_id):
    uow = UnitOfWork(db)
    repo = TransactionRepository(db)

    with uow:
        with uow:
            repo.create(Decimal("1"), "expense", "inner", date(2026, 8, 1), user_id)
        assert committed_transaction_count() == 0
        repo.create(Decimal("2"), "expense", "outer", date(2026, 8, 1), user_id)

    assert committed_transaction_count() == 2


def test_repositories_do_not_commit_on_their_own(db, user_id):
    TransactionRepository(db).create(Decimal("1"), "expense", "x", date(2026, 8, 1), user_id)

    assert committed_transaction_count() == 0
    db.rollback()
    assert db.scalar(select(func.count(Transaction.id))) == 0


def test_api_writes_are_still_committed(client, user_a_headers):
    response = client.post(
        "/api/v1/transactions",
        json={"amount": 5, "type": "expense", "date": "2026-08-01"},
        headers=user_a_headers,
    )

    assert response.status_code == 201
    assert committed_transaction_count() == 1
