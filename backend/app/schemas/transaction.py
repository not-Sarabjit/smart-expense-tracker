from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class TransactionBase(BaseModel):
    """Base Schema for common fields and validations"""

    amount: Decimal
    date: date_type
    transaction_type: Literal["income", "expense"]
    category_id: int
    description: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Amount must be greater than zero")
        return value

    @field_validator("date")
    @classmethod
    def date_not_in_future(cls, value: date_type) -> date_type:
        if value > date_type.today():
            raise ValueError("Date cannot be in the future")
        return value


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction. All fields required."""
    pass


class TransactionUpdate(BaseModel):
    """
    Schema for partial updates.
    Only provided fields will be updated.
    """

    amount: Optional[Decimal] = None
    date: Optional[date_type] = None
    category_type: Optional[Literal["income", "expense"]] = None
    category_id: Optional[int] = None
    description: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is not None and value <= 0:
            raise ValueError("Amount must be greater than zero")
        return value

    @field_validator("date")
    @classmethod
    def date_not_in_future(cls, value: Optional[date_type]) -> Optional[date_type]:
        if value is not None and value > date_type.today():
            raise ValueError("Date cannot be in the future")
        return value


class TransactionOut(TransactionBase):
    """Schema for API responses. Reflects the full DB record."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    # So Pydantic can read attributes from the user object
    class Config:
        from_attributes = True 
