import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")


class UserCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str | None
    currency: str
    timezone: str
    created_at: datetime

    # So Pydantic can read attributes from the user object
    model_config = ConfigDict(from_attributes=True)


class UserPreferencesUpdate(BaseModel):
    """
    Body for PATCH /users/me. Only provided fields are changed.
    Email is deliberately not editable here (it is the login identity).
    """

    first_name: str | None = None
    last_name: str | None = None
    currency: str | None = None
    timezone: str | None = None

    @field_validator("first_name")
    @classmethod
    def first_name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("First name cannot be empty.")
        return value

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if not CURRENCY_CODE.match(value):
            raise ValueError("Currency must be a 3-letter ISO 4217 code, e.g. INR or USD.")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(
                "Timezone must be an IANA name, e.g. Asia/Kolkata or Europe/London."
            ) from None
        return value
