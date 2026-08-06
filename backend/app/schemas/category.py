from pydantic import BaseModel
from typing import Literal


class CategoryCreate(BaseModel):
    name: str
    category_type: Literal['income', 'expense']

class CategoryUpdate(BaseModel):
    name: str | None = None
    category_type: Literal['income', 'expense'] | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    category_type: Literal['income', 'expense']
    user_id: int
    
    # So attributes from the objects can be fetched
    class Config:
        from_attributes = True
