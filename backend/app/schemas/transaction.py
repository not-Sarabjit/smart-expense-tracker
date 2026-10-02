from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class TransactionBase(BaseModel):
    """Base Schema for common fields and validations"""

    amount: Decimal
    date: date_type
    transaction_type: Literal["income", "expense"] = Field(alias="type")
    category_id: int | None = None
    description: str | None = None

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

    amount: Decimal | None = None
    date: date_type | None = None
    # Accepts "type" (same key as create/read) or the legacy "transaction_type"
    transaction_type: Literal["income", "expense"] | None = Field(
        default=None, validation_alias=AliasChoices("type", "transaction_type")
    )
    category_id: int | None = None
    description: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("Amount must be greater than zero")
        return value

    @field_validator("date")
    @classmethod
    def date_not_in_future(cls, value: date_type | None) -> date_type | None:
        if value is not None and value > date_type.today():
            raise ValueError("Date cannot be in the future")
        return value


class TransactionOut(TransactionBase):
    """Schema for API responses. Reflects the full DB record."""

    id: int
    created_at: datetime
    updated_at: datetime | None = None

    # So Pydantic can read attributes from the ORM object
    model_config = ConfigDict(from_attributes=True)
