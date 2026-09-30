from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    return CategoryService(CategoryRepository(db))


@router.get("/", response_model=list[CategoryOut])
def list_categories(
    current_user: User = Depends(get_current_user),
    category_service: CategoryService = Depends(get_category_service),
):
    """
    List all categories belonging to the current user.
    """
    return category_service.list_category(current_user.id)


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    category_service: CategoryService = Depends(get_category_service),
):
    """
    Gets a single category by category_id
    """
    return category_service.get_category(user_id=current_user.id, category_id=category_id)


@router.post("/create_category", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate,
    current_user: User = Depends(get_current_user),
    category_service: CategoryService = Depends(get_category_service),
):
    """
    Create a new category for the current user.
    """
    return category_service.create_category(
        user_id=current_user.id, name=category_in.name, category_type=category_in.category_type
    )


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    category_service: CategoryService = Depends(get_category_service),
):
    """
    Update a category owned by the current user.
    """
    return category_service.update_category(
        user_id=current_user.id,
        category_id=category_id,
        name=category_update.name,
        category_type=category_update.category_type,
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    category_service: CategoryService = Depends(get_category_service),
):
    """
    Delete a category owned by the current user.
    """
    category_service.delete_category(current_user.id, category_id)
    return None
