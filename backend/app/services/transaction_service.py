from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from app.core.exceptions import (
    CategoryAccessDeniedException,
    CategoryNotFoundException,
    CategoryTypeMismatchException,
    TransactionNotFoundException,
)
from app.database.unit_of_work import UnitOfWork
from app.models.category import Category
from app.models.transaction import Transaction, TransactionSource
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.utils.date_utils import last_day_of_month

# API field name -> Transaction model attribute, for fields whose names differ
_UPDATE_FIELD_TO_ATTRIBUTE = {"transaction_type": "type"}


def _type_value(transaction_type) -> str:
    """Normalises a TransactionType enum or plain string to 'income' / 'expense'."""
    return getattr(transaction_type, "value", transaction_type)


class TransactionService:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        category_repository: CategoryRepository,
        uow: UnitOfWork,
    ):
        self.transaction_repository = transaction_repository
        self.category_repository = category_repository
        self.uow = uow

    def _validate_category(self, user_id: int, category_id: int, transaction_type) -> Category:
        """
        Checks the category exists, is a default or the user's own, and matches the transaction type
        """
        category = self.category_repository.get_by_id(category_id)
        if not category:
            raise CategoryNotFoundException()
        if category.user_id is not None and category.user_id != user_id:
            raise CategoryAccessDeniedException()

        transaction_type = _type_value(transaction_type)
        if category.category_type != transaction_type:
            raise CategoryTypeMismatchException(
                f"Category '{category.name}' is an {category.category_type} category "
                f"and cannot be used for an {transaction_type} transaction."
            )
        return category

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
        source: TransactionSource = TransactionSource.manual,
    ) -> Transaction:

        with self.uow:
            if category_id is not None:
                self._validate_category(user_id, category_id, transaction_type)

            return self.transaction_repository.create(
                user_id=user_id,
                amount=amount,
                transaction_type=transaction_type,
                description=description,
                date=date,
                category_id=category_id,
                source=source,
            )

    def create_transactions(
        self,
        user_id: int,
        items: Iterable[dict],
        source: TransactionSource = TransactionSource.manual,
    ) -> list[Transaction]:
        """
        Creates several transactions atomically: every item is validated and inserted inside one
        DB transaction, so if any item fails nothing is saved. Each item takes the keyword
        arguments of create_transaction (amount, transaction_type, description, date, category_id).
        """
        with self.uow:
            return [
                self.create_transaction(
                    user_id=user_id,
                    amount=Decimal(str(item["amount"])),
                    transaction_type=item["transaction_type"],
                    description=item.get("description"),
                    date=item["date"],
                    category_id=item.get("category_id"),
                    source=source,
                )
                for item in items
            ]

    def list_transactions(
        self,
        user_id: int,
        transaction_type: str | None = None,
        category_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_by: str = "date",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:

        return self.transaction_repository.get_all_for_user(
            user_id,
            transaction_type=transaction_type,
            category_id=category_id,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )

    def count_transactions(
        self,
        user_id: int,
        transaction_type: str | None = None,
        category_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        """
        Total number of the user's transactions matching the filters (for pagination)
        """
        return self.transaction_repository.count_for_user(
            user_id,
            transaction_type=transaction_type,
            category_id=category_id,
            start_date=start_date,
            end_date=end_date,
        )

    def update_transaction(self, user_id: int, transaction_id: int, **fields) -> Transaction:

        transaction = self.transaction_repository.get_by_id(
            transaction_id=transaction_id, user_id=user_id
        )
        if not transaction:
            raise TransactionNotFoundException()

        # Translate API field names to model attributes (transaction_type -> type)
        fields = {_UPDATE_FIELD_TO_ATTRIBUTE.get(k, k): v for k, v in fields.items()}

        ##To do: For now, all fields can get updated, later add validation to check for non-editable fields like user_id etc
        updates = {
            k: v for k, v in fields.items() if v is not None and v != getattr(transaction, k)
        }
        if not updates:
            return transaction

        with self.uow:
            # Re-validate the category whenever the category or the type changes
            if "category_id" in updates or "type" in updates:
                category_id = updates.get("category_id", transaction.category_id)
                if category_id is not None:
                    self._validate_category(
                        user_id, category_id, updates.get("type", transaction.type)
                    )

            return self.transaction_repository.update(transaction=transaction, **updates)

    def delete_transaction(self, user_id: int, transaction_id: int) -> None:

        transaction = self.transaction_repository.get_by_id(
            transaction_id=transaction_id, user_id=user_id
        )
        if not transaction:
            raise TransactionNotFoundException()

        with self.uow:
            self.transaction_repository.delete(transaction=transaction)

    def get_monthly_summary(self, user_id: int, year: int, month: int) -> dict:
        """
        Income, expense and net for one calendar month, aggregated in the database
        """
        totals = self.transaction_repository.get_totals_by_type(
            user_id,
            start_date=date(year, month, 1),
            end_date=last_day_of_month(year, month),
        )
        income = totals["income"]
        expense = totals["expense"]
        return {
            "income": income,
            "expense": expense,
            "net": income - expense,
        }
