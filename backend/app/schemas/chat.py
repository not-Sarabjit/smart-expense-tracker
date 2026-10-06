import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_TITLE_LENGTH = 200


class ConversationCreate(BaseModel):
    """Body for POST /chat/conversations. Everything is optional."""

    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)


class ConversationUpdate(BaseModel):
    """Body for PATCH /chat/conversations/{id}.

    At least one field must be present; absent fields are left untouched.
    """

    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)
    archived: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ConversationUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one of: title, archived")
        return self


class ConversationOut(BaseModel):
    """A conversation as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    archived: bool
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    """A persisted chat message. `content` is null for tool-only assistant turns."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: uuid.UUID
    role: str
    content: str | None
    tool_calls: Any | None
    meta: dict[str, Any] | None
    created_at: datetime

class MessageCreate(BaseModel):
    """Body of POST /chat/conversations/{id}/messages."""

    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content must not be blank")
        return cleaned
