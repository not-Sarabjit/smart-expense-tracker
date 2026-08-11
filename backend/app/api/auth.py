from fastapi import APIRouter, Depends, status, HTTPException
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
    user: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user.
    """
    try:
        return auth_service.register(first_name = user.first_name, last_name = user.last_name, password = user.password, email = user.email)
    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate a user and return a JWT access token.
    """
    try:
        access_token =  auth_service.login(email = credentials.email, password = credentials.password)
        return Token(access_token=access_token)
    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )
