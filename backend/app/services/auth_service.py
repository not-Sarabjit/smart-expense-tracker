from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import EmailAlreadyExistsException, InvalidCredentialsException
from app.repositories.user_repository import UserRepository

# Loading algorithm and secret key from env
TOKEN_ALGORITHM = settings.TOKEN_ALGORITHM
SECRET_KEY = settings.SECRET_KEY


# For password hashing and verifying. rehashes using other algos if provided if one is deprecated
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def register(self, email: str, password: str, first_name: str, last_name: str):
        """
        Checks if the email is not already registered, if not thn creates a new user and returns the user
        """

        if self.user_repository.get_by_email(email):
            raise EmailAlreadyExistsException()

        hashed_password = pwd_context.hash(password)
        return self.user_repository.create(
            email=email,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
        )

    def login(self, email: str, password: str) -> str:
        """
        Verifies if username and password are correct, provides token if verified
        """

        user = self.user_repository.get_by_email(email)

        if not user or not pwd_context.verify(password, user.hashed_password):
            raise InvalidCredentialsException()

        access_token = self._create_access_token(user.id)
        return access_token

    def _create_access_token(self, user_id: int, expires_minutes: int = 60) -> str:
        """
        Returns token in str
        """
        expire = datetime.now() + timedelta(minutes=expires_minutes)
        payload = {"sub": str(user_id), "exp": expire}
        return jwt.encode(payload, SECRET_KEY, algorithm=TOKEN_ALGORITHM)
