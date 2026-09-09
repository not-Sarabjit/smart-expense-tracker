from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_for_user(
        self,
        user_id: int,
        transaction_type: str | None = None,
        category_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_by: str = 'date',
        sort_order: str = 'desc',
        limit: int = 50
    ) -> list[Transaction]:
        '''
        Fetches transactions made by the user ( Default returned 50 most recent ), Using the user_id
        '''

        statement = select(Transaction).where(Transaction.user_id == user_id)

        if transaction_type:
            statement = statement.where(Transaction.type == transaction_type)
        if category_id is not None:
            statement = statement.where(Transaction.category_id == category_id)
        if start_date:
            statement = statement.where(Transaction.date >= start_date)
        if end_date:
            statement = statement.where(Transaction.date <= end_date)

        sort_columns = {
            "date": Transaction.date,
            "amount": Transaction.amount,
        }

        column = sort_columns[sort_by]

        if sort_order == "asc":
            statement = statement.order_by(column.asc())
        else:
            statement = statement.order_by(column.desc())

        statement = statement.limit(limit)

        return self.db.scalars(statement).all()

    def get_by_id(self, transaction_id: int, user_id: int) -> Transaction | None:
        '''
        Fetches a single transaction by transaction id for the user
        '''
        statement = select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
        return self.db.scalars(statement).first()

    def create(
        self,
        amount: float,
        transaction_type: str,
        description: str,
        date: date,
        user_id: int,
        category_id: int | None = None
    ) -> Transaction:
        
        transaction = Transaction(
            amount=amount,
            type=transaction_type,
            description=description,
            date=date,
            user_id=user_id,
            category_id=category_id,
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def update(self, transaction: Transaction, **kwargs) -> Transaction:

        for key, value in kwargs.items():
            setattr(transaction, key, value)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def delete(self, transaction: Transaction) -> None:
        
        self.db.delete(transaction)
        self.db.commit()
