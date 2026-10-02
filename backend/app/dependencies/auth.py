from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.request_context import bind_user_id
from app.database.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository

# For swagger
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# For swagger testing only
oauth2_scheme = HTTPBearer()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token.credentials, settings.SECRET_KEY, algorithms=[settings.TOKEN_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception from None

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(int(user_id))
    if user is None:
        raise credentials_exception

    # Every later log line in this request carries user_id
    bind_user_id(user.id)
    return user
