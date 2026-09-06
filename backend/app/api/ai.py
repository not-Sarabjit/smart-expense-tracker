from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import ExtractionRequest, ExtractionResponse
from app.ai.extractor import extract_transaction_from_text
from app.core.exceptions import AIServiceError

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post(
    "/extract",
    response_model=ExtractionResponse,
    summary="Extract structured transaction data from natural language text",
)
async def extract_transaction(
    payload: ExtractionRequest,
   
) -> ExtractionResponse:
    """
    Accepts a free-text description and returns a structured transaction object.
    Does NOT save anything to the database — use /ai/extract-and-save for that.
    """
    try:
        result = await extract_transaction_from_text(payload.text)
        return result
    except AIServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service unavailable: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during extraction: {str(e)}",
        )