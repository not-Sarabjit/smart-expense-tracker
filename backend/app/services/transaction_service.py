from datetime import date

from app.core.exceptions import (
    CategoryAccessDeniedException,
    CategoryNotFoundException,
    TransactionNotFoundException,
)
from app.models.transaction import Transaction
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.utils.date_utils import last_day_of_month


class TransactionService:
    def __init__(
        self, transaction_repository: TransactionRepository, category_repository: CategoryRepository
    ):
        self.transaction_repository = transaction_repository
        self.category_repository = category_repository

    def get_transaction(self, transaction_id: int, user_id: int) -> Transaction:
        """
        Fetches just a single transaction for the user
        """
        transaction = self.transaction_repository.get_by_id(
            transaction_id=transaction_id, user_id=user_id
        )

        if not transaction:
            raise TransactionNotFoundException()

        return transaction

    def create_transaction(
        self,
        user_id: int,
        amount: float,
        transaction_type: str,
        description: str,
        date: date,
        category_id: int,
    ) -> Transaction:

        # Category Validation
        if category_id is not None:
            category = self.category_repository.get_by_id(category_id)
            if not category:
                raise CategoryNotFoundException()
            if category.user_id is not None and category.user_id != user_id:
                raise CategoryAccessDeniedException()

        return self.transaction_repository.create(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            date=date,
            category_id=category_id,
        )

    def list_transactions(
        self,
        user_id: int,
        transaction_type: str | None = None,
        category_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_by: str = "date",
        sort_order: str = "desc",
    ) -> list[Transaction]:

        return self.transaction_repository.get_all_for_user(
            user_id,
            transaction_type=transaction_type,
            category_id=category_id,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def update_transaction(self, user_id: int, transaction_id: int, **fields) -> Transaction:

        transaction = self.transaction_repository.get_by_id(
            transaction_id=transaction_id, user_id=user_id
        )
        if not transaction:
            raise TransactionNotFoundException()

        ##To do: For now, all fields can get updated, later add validation to check for non-editable fields like user_id etc
        updates = {
            k: v for k, v in fields.items() if v is not None and v != getattr(transaction, k)
        }
        if updates:
            transaction = self.transaction_repository.update(transaction=transaction, **updates)
        return transaction

    def delete_transaction(self, user_id: int, transaction_id: int) -> None:

        transaction = self.transaction_repository.get_by_id(
            transaction_id=transaction_id, user_id=user_id
        )
        if not transaction:
            raise TransactionNotFoundException()

        self.transaction_repository.delete(transaction=transaction)

    def get_monthly_summary(self, user_id: int, year: int, month: int) -> dict:
        transactions = self.transaction_repository.get_all_for_user(
            user_id,
            start_date=date(year, month, 1),
            end_date=last_day_of_month(year, month),
        )
        income = sum(t.amount for t in transactions if t.type == "income")
        expense = sum(t.amount for t in transactions if t.type == "expense")
        return {
            "income": income,
            "expense": expense,
            "net": income - expense,
        }
