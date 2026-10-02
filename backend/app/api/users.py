from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.unit_of_work import UnitOfWork
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserOut, UserPreferencesUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db), UnitOfWork(db))


@router.get("/me", response_model=UserOut)
def get_me(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    Return the current user's profile and preferences (currency, timezone).
    """
    return user_service.get_profile(current_user.id)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    Update the current user's name and/or preferences. Only provided fields change.
    """
    return user_service.update_profile(
        user_id=current_user.id,
        **payload.model_dump(exclude_unset=True, exclude_none=True),
    )
