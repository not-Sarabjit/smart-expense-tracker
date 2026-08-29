from pydantic import BaseModel, field_validator
from typing import Literal


class CategoryCreate(BaseModel):
    name: str
    category_type: Literal['income', 'expense']

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        value = value.strip()

        if not value:
            raise ValueError("Category name cannot be empty.")

        return value

class CategoryUpdate(BaseModel):
    name: str | None = None
    category_type: Literal['income', 'expense'] | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None):
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Category name cannot be empty.")

        return value


class CategoryOut(BaseModel):
    id: int
    name: str
    category_type: Literal['income', 'expense']
    user_id: int | None
    
    # So attributes from the objects can be fetched
    class Config:
        from_attributes = True
