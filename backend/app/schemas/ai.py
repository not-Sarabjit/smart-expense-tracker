from pydantic import BaseModel, Field
from typing import Optional
from datetime import date as date_type




class ExtractedTransaction(BaseModel):
    amount: Optional[float] = Field(None, description="Transaction amount in the base currency")
    currency: Optional[str] = Field("INR", description="Currency code, e.g. INR, USD")
    description: Optional[str] = Field(None, description="Clean merchant or purpose description")
    date: Optional[date_type] = Field(None, description="Transaction date, if mentioned")
    category_hint: Optional[str] = Field(None, description="AI-suggested category name (not ID)")

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 340.0,
                "currency": "INR",
                "description": "Pizza delivery",
                "date": "2024-07-15",
                "category_hint": "Food & Dining"
            }
        }

# --- Response from the AI

class ExtractionResponse(BaseModel):
    success: bool = Field(..., description="True if extraction produced usable data")
    data: Optional[ExtractedTransaction] = Field(None, description="Extracted transaction fields")
    raw_text: str = Field(..., description="Original input text passed to the AI")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI confidence score between 0.0 and 1.0"
    )
    error_message: Optional[str] = Field(None, description="Human-readable error if success=False")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "amount": 340.0,
                    "currency": "INR",
                    "description": "Pizza delivery",
                    "date": "2024-07-15",
                    "category_hint": "Food & Dining"
                },
                "raw_text": "paid 340 for pizza last night",
                "confidence": 0.92,
                "error_message": None
            }
        }


# --- Request Schema for /ai/extract endpoint ---

class ExtractionRequest(BaseModel):
    text: str = Field(..., min_length=3, description="Natural language transaction description")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "paid 340 for pizza last night"
            }
        }


# --- AI Error Response ---

class AIErrorResponse(BaseModel):
    error: str = Field(..., description="Short error code, e.g. AI_SERVICE_UNAVAILABLE")
    message: str = Field(..., description="Human-readable error description")
    detail: Optional[str] = Field(None, description="Extra debug info, omitted in production")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "AI_SERVICE_UNAVAILABLE",
                "message": "The AI service is temporarily unavailable. Please try again.",
                "detail": "Groq API returned 503 after 3 retries"
            }
        }


# --- Category Suggestion ---

class CategorySuggestion(BaseModel):
    suggested_category_id: Optional[int] = Field(None, description="DB ID of the suggested category")
    suggested_category_name: Optional[str] = Field(None, description="Human-readable category name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")

    class Config:
        json_schema_extra = {
            "example": {
                "suggested_category_id": 5,
                "suggested_category_name": "Food & Dining",
                "confidence": 0.87
            }
        }


if __name__ == '__main__':
    print('Running fine')