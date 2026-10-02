from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionSource, TransactionType

CENTS = Decimal("0.01")


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    # Whitelist of sortable columns — the router validates sort_by against these keys too.
    SORT_COLUMNS = {
        "date": Transaction.date,
        "amount": Transaction.amount,
    }

    def _filtered(
        self,
        statement: Select,
        user_id: int,
        transaction_type: str | None = None,
        category_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Select:
        """
        Applies the user scope and optional filters to a statement
        """
        statement = statement.where(Transaction.user_id == user_id)

        if transaction_type:
            statement = statement.where(Transaction.type == transaction_type)
        if category_id is not None:
            statement = statement.where(Transaction.category_id == category_id)
        if start_date:
            statement = statement.where(Transaction.date >= start_date)
        if end_date:
            statement = statement.where(Transaction.date <= end_date)

        return statement

    def get_all_for_user(
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
        """
        Fetches one page of the user's transactions ( Default: the 50 most recent ), Using the user_id
        """
        statement = self._filtered(
            select(Transaction),
            user_id,
            transaction_type=transaction_type,
            category_id=category_id,
            start_date=start_date,
            end_date=end_date,
        )

        if sort_by not in self.SORT_COLUMNS:
            raise ValueError(f"Unsupported sort_by: {sort_by!r}")
        column = self.SORT_COLUMNS[sort_by]

        # id as a tie-breaker keeps pages stable when many rows share a date/amount
        if sort_order == "asc":
            statement = statement.order_by(column.asc(), Transaction.id.asc())
        else:
            statement = statement.order_by(column.desc(), Transaction.id.desc())

        statement = statement.limit(limit).offset(offset)

        return self.db.scalars(statement).all()

    def count_for_user(
        self,
        user_id: int,
        transaction_type: str | None = None,
        category_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        """
        Counts the user's transactions matching the same filters as get_all_for_user
        """
        statement = self._filtered(
            select(func.count(Transaction.id)),
            user_id,
            transaction_type=transaction_type,
            category_id=category_id,
            start_date=start_date,
            end_date=end_date,
        )
        return self.db.scalar(statement)

    def get_totals_by_type(
        self, user_id: int, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Decimal]:
        """
        Sums amounts per transaction type in the database ( SUM ... GROUP BY type )
        Returns {"income": Decimal, "expense": Decimal}, with 0 for a type that has no rows
        """
        statement = self._filtered(
            select(Transaction.type, func.coalesce(func.sum(Transaction.amount), 0)),
            user_id,
            start_date=start_date,
            end_date=end_date,
        ).group_by(Transaction.type)

        totals = {
            TransactionType.income.value: Decimal("0"),
            TransactionType.expense.value: Decimal("0"),
        }
        for transaction_type, total in self.db.execute(statement).all():
            totals[TransactionType(transaction_type).value] = Decimal(str(total)).quantize(CENTS)
        return totals

    def get_by_id(self, transaction_id: int, user_id: int) -> Transaction | None:
        """
        Fetches a single transaction by transaction id for the user
        """
        statement = select(Transaction).where(
            Transaction.id == transaction_id, Transaction.user_id == user_id
        )
        return self.db.scalars(statement).first()

    def create(
        self,
        amount: float,
        transaction_type: str,
        description: str,
        date: date,
        user_id: int,
        category_id: int | None = None,
        source: TransactionSource = TransactionSource.manual,
    ) -> Transaction:

        transaction = Transaction(
            amount=amount,
            type=transaction_type,
            description=description,
            date=date,
            user_id=user_id,
            category_id=category_id,
            source=source,
        )
        self.db.add(transaction)
        self.db.flush()
        self.db.refresh(transaction)
        return transaction

    def update(self, transaction: Transaction, **kwargs) -> Transaction:

        for key, value in kwargs.items():
            setattr(transaction, key, value)
        self.db.flush()
        self.db.refresh(transaction)
        return transaction

    def delete(self, transaction: Transaction) -> None:

        self.db.delete(transaction)
        self.db.flush()
