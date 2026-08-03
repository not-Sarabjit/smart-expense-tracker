import enum
from datetime import date as date_

from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    Enum as SqlEnum,
    func,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"


class Transaction(Base):

    # Table Name Definition
    __tablename__ = "transactions"

    # Table Column Definitions
    id = Column(Integer, primary_key=True,index=True)

    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(SqlEnum(TransactionType, name="transaction_type"), nullable=False)
    description = Column(String(255), nullable=True)
    date = Column(Date, nullable=False, default=date_.today)

    user_id = Column(Integer, ForeignKey("users.id",ondelete='CASCADE'), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    created_at = Column(DateTime, server_default = func.now(), nullable=False)

    # Table Relationship Definitions

    # Relationship with user
    user = relationship(
        'User',
        back_populates='transactions'
    )

    # With Categories
    category = relationship(
        'Category',
        back_populates='transactions'
    )