from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import ExtractionRequest, ExtractionResponse, ExtractAndSaveResponse
from app.ai.extractor import extract_transaction_from_text
from app.core.exceptions import AIServiceError
from app.database.session import get_db
from app.repositories.category_repository import CategoryRepository
from app.schemas.transaction import TransactionCreate
from app.repositories.transaction_repository import TransactionRepository
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post(
    "/extract",
    response_model=ExtractionResponse,
    summary="Extract structured transaction data from natural language text",
)
async def extract_transaction(
    payload: ExtractionRequest,
    current_user: User = Depends(get_current_user),
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




@router.post(
    "/extract-and-save",
    response_model=ExtractAndSaveResponse,
    summary="Extract transaction from text and optionally save to the database",
)
async def extract_and_save(
    payload: ExtractionRequest,
    dry_run: bool = Query(
        default=False,
        description="If true, returns the extracted preview without saving to the database.",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExtractAndSaveResponse:
    """
    Two-in-one endpoint:
    - dry_run=false (default): extracts from text AND saves the transaction to the DB.
    - dry_run=true: extracts and returns the preview — nothing is written to the DB.

    If extraction confidence is below 0.5, the endpoint refuses to save and asks
    the user to clarify, even when dry_run=false.
    """

    # ── Step 1: Extract ──────────────────────────────────────────────────────
    try:
        extraction = await extract_transaction_from_text(payload.text)
    except AIServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service unavailable: {str(e)}",
        )

    # ── Step 2: Dry-run — return preview without saving ──────────────────────
    if dry_run:
        return ExtractAndSaveResponse(
            success=extraction.success,
            dry_run=True,
            extraction=extraction,
            preview=extraction.data,
            message="Dry run — nothing was saved. Set dry_run=false to save.",
        )

    # ── Step 3: Guard — refuse to save low-confidence extractions ────────────
    if not extraction.success or extraction.data is None:
        return ExtractAndSaveResponse(
            success=False,
            dry_run=False,
            extraction=extraction,
            message="Extraction failed — could not parse the transaction. Please rephrase.",
        )

    if extraction.confidence < 0.5:
        return ExtractAndSaveResponse(
            success=False,
            dry_run=False,
            extraction=extraction,
            message=(
                f"Confidence too low ({extraction.confidence:.0%}) to save automatically. "
                "Please add more detail (e.g. amount, date) or use dry_run=true to review."
            ),
        )

    if extraction.data.amount is None:
        return ExtractAndSaveResponse(
            success=False,
            dry_run=False,
            extraction=extraction,
            message="Amount could not be extracted. Cannot save without a valid amount.",
        )

    # ── Step 4: Resolve category_id from category_hint (best-effort) ─────────
    category_id: Optional[int] = None
    if extraction.data.category_hint:
        category_repo = CategoryRepository(db)
        user_categories = category_repo.get_all_for_user(current_user.id)
        hint_lower = extraction.data.category_hint.lower()
        for cat in user_categories:
            if hint_lower in cat.name.lower() or cat.name.lower() in hint_lower:
                category_id = cat.id
                break   # take the first match

    

    # ── Step 5: Build TransactionCreate and save ──────────────────────────────
    transaction_date = extraction.data.date or date.today()


    transaction_in = TransactionCreate(
        amount=extraction.data.amount,
        type="expense",                         # default; user can update later
        description=extraction.data.description or payload.text,
        date=transaction_date,
        category_id=category_id,               # None is fine — saves as uncategorized
    )

    try:
        transaction_repo = TransactionRepository(db)
        category_repo = CategoryRepository(db)
        transaction_service = TransactionService(transaction_repo,category_repo)
        saved = transaction_service.create_transaction(
            user_id=current_user.id,
            amount = transaction_in.amount,
            transaction_type = transaction_in.transaction_type,
            description = transaction_in.description,
            date= transaction_in.date,
            category_id = transaction_in.category_id
        )


    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction succeeded but database save failed: {str(e)}",
        )

    # ── Step 6: Return the saved transaction ──────────────────────────────────
    return ExtractAndSaveResponse(
        success=True,
        dry_run=False,
        extraction=extraction,
        saved_transaction={
            "id": saved.id,
            "amount": float(saved.amount),
            "type": saved.type,
            "description": saved.description,
            "date": str(saved.date),
            "category_id": saved.category_id,
            "user_id": saved.user_id,
            "created_at": str(saved.created_at),
        },
        message="Transaction extracted and saved successfully.",
    )