from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class ExtractedTransaction(BaseModel):
    amount: float = Field(..., description="The transaction amount as a positive number")
    description: str = Field(..., description="A short description of what was spent on")
    category: str = Field(..., description="Category: Food, Transport, Shopping, Entertainment, Bills, Health, or Other")
    date: Optional[str] = Field(None, description="Transaction date in YYYY-MM-DD format if mentioned, else Current Date")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")