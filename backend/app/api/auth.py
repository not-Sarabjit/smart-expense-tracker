from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.unit_of_work import UnitOfWork
from app.repositories.user_repository import UserRepository
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db), UnitOfWork(db))


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    user: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user.
    """
    # Domain errors (e.g. EmailAlreadyExistsException -> 409) are AppExceptions,
    # rendered by the global handler in main.py — no try/except needed here.
    return auth_service.register(
        first_name=user.first_name,
        last_name=user.last_name,
        password=user.password,
        email=user.email,
    )


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate a user and return a JWT access token.
    """
    access_token = auth_service.login(email=credentials.email, password=credentials.password)
    return Token(access_token=access_token)
