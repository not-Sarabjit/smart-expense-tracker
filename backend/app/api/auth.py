from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.user import UserCreate, UserOut, UserLogin
from app.schemas.token import Token
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository



router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user.
    """
    return auth_service.register(user_in)


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate a user and return a JWT access token.
    """
    return auth_service.login(credentials)


