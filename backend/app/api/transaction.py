from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.transaction import (
    TransactionCreate,
    TransactionOut,
    TransactionUpdate,
)
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.category_repository import CategoryRepository

from app.services.transaction_service import TransactionService

# --- Auth dependency -------------------------------------------------------
# Phase 7, Step 1 will build the real get_current_user (decodes JWT, loads
# the user, raises 401 if invalid). Until that phase exists, import it if
# present; otherwise fall back to a placeholder so this router still runs.
try:
    from app.dependencies.auth import get_current_user  # Phase 7, Step 1
except ImportError:  # pragma: no cover - temporary stub until Phase 7
    from app.models.user import User

    def get_current_user(db: Session = Depends(get_db)) -> "User":
        """
        TEMPORARY placeholder until Phase 7 - Step 1 builds the real
        JWT-based get_current_user dependency. Replace this import once
        app/dependencies/auth.py exists.
        """
        raise NotImplementedError(
            "get_current_user is not implemented yet - build it in Phase 7, Step 1."
        )


router = APIRouter(prefix="/transactions", tags=["Transactions"])




def get_transaction_service(db: Session = Depends(get_db)) -> TransactionService:
    return TransactionService(transaction_repository=TransactionRepository(db), category_repository=CategoryRepository(db))



# NOTE: defined before /{transaction_id} so "summary" isn't swallowed by the
# dynamic path parameter.
@router.get("/summary")
def get_summary(
    year: int,
    month: int,
    current_user=Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service)
):
    """
    Returns total income, total expense, and net total for the current user,
    optionally scoped to a date range. Great demo endpoint - shows the app
    doing something useful with one request.
    """
    return service.get_monthly_summary(
        user_id=current_user.id,
        month=month,
        year=year,
    )



@router.get("", response_model=list[TransactionOut])
def list_transactions(
    type: Optional[str] = Query(None, description="Filter by 'income' or 'expense'"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    sort_by: str = Query("date", description="Field to sort by, e.g. 'date' or 'amount'"),
    sort_order: str = Query("desc", description="'asc' or 'desc'"),
    current_user=Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """List the current user's transactions, with optional filtering and sorting."""
    return service.list_transactions(
        user_id=current_user.id,
        type=type,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
    )



@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    current_user=Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Create a new income or expense transaction for the current user."""
    return service.create_transaction(user_id=current_user.id, data=payload)



@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: int,
    current_user=Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Get a single transaction — service enforces that it belongs to the user."""
    return service.get_transaction(user_id=current_user.id, transaction_id=transaction_id)



@router.put("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    current_user=Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Update an existing transaction owned by the current user."""
    return service.update_transaction(
        user_id=current_user.id,
        transaction_id=transaction_id,
        data=payload,
    )


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    current_user=Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Delete a transaction owned by the current user."""
    service.delete_transaction(user_id=current_user.id, transaction_id=transaction_id)
    return None


