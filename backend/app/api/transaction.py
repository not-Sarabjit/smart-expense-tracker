from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.unit_of_work import UnitOfWork
from app.dependencies.auth import get_current_user
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import (
    TransactionCreate,
    TransactionOut,
    TransactionUpdate,
)
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["Transactions"])

MAX_PAGE_SIZE = 200
TOTAL_COUNT_HEADER = "X-Total-Count"


def get_transaction_service(db: Session = Depends(get_db)) -> TransactionService:
    return TransactionService(
        transaction_repository=TransactionRepository(db),
        category_repository=CategoryRepository(db),
        uow=UnitOfWork(db),
    )


# NOTE: defined before /{transaction_id} so "summary" isn't swallowed by the
# dynamic path parameter.
@router.get("/summary")
def get_summary(
    year: int = Query(..., ge=1, le=9999),
    month: int = Query(..., ge=1, le=12),
    current_user=Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """
    Returns total income, total expense, and net total for the current user
    for one calendar month, summed in the database.
    """
    return service.get_monthly_summary(
        user_id=current_user.id,
        month=month,
        year=year,
    )


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    response: Response,
    transaction_type: Literal["income", "expense"] | None = Query(
        None, description="Filter by 'income' or 'expense'"
    ),
    category_id: int | None = Query(None, description="Filter by category"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    sort_by: Literal["date", "amount"] = Query("date", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE, description="Page size"),
    offset: int = Query(0, ge=0, description="Rows to skip"),
    current_user=Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """
    List one page of the current user's transactions, with optional filtering and sorting.
    The total number of matching rows is returned in the X-Total-Count header.
    """
    filters = {
        "transaction_type": transaction_type,
        "category_id": category_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    response.headers[TOTAL_COUNT_HEADER] = str(
        service.count_transactions(user_id=current_user.id, **filters)
    )
    return service.list_transactions(
        user_id=current_user.id,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
        **filters,
    )


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    current_user=Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Create a new income or expense transaction for the current user."""
    return service.create_transaction(
        user_id=current_user.id,
        amount=payload.amount,
        transaction_type=payload.transaction_type,
        description=payload.description,
        date=payload.date,
        category_id=payload.category_id,
    )


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
        **payload.model_dump(exclude_unset=True),
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
