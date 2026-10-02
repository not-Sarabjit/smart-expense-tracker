from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import EmailAlreadyExistsException, InvalidCredentialsException
from app.database.unit_of_work import UnitOfWork
from app.repositories.user_repository import UserRepository

# For password hashing and verifying. rehashes using other algos if provided if one is deprecated
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, user_repository: UserRepository, uow: UnitOfWork):
        self.user_repository = user_repository
        self.uow = uow

    def register(self, email: str, password: str, first_name: str, last_name: str):
        """
        Checks if the email is not already registered, if not thn creates a new user and returns the user
        """

        if self.user_repository.get_by_email(email):
            raise EmailAlreadyExistsException()

        hashed_password = pwd_context.hash(password)
        with self.uow:
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

    def _create_access_token(self, user_id: int, expires_minutes: int | None = None) -> str:
        """
        Returns token in str. `exp`/`iat` are timezone-aware UTC (JWT NumericDate is UTC seconds).
        """
        auth_settings = get_settings().auth
        if expires_minutes is None:
            expires_minutes = auth_settings.access_token_expire_minutes
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=expires_minutes),
        }
        return jwt.encode(
            payload, auth_settings.secret_key, algorithm=auth_settings.token_algorithm
        )
