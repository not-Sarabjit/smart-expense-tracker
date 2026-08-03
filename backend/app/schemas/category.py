from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str

class CategoryUpdate(BaseModel):
    name: str | None = None

class CategoryOut(BaseModel):
    id: int
    name: str
    user_id: int
    
    # So attributes from the objects can be fetched
    class Config:
        from_attributes = True
