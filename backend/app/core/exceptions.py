class AppException(Exception):
    """Base class for all custom application exceptions.

    `headers` lets an exception carry response headers (e.g. `Retry-After` on a
    429). The global handler in `api/main.py` applies them. Without this the only
    way to set a header on an error would be `HTTPException`, which renders
    FastAPI's `{"detail": ...}` body instead of ours and would make 429 the one
    endpoint with a different error shape.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        headers: dict[str, str] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.headers = headers
        super().__init__(message)


# -------------------------  User Auth Exceptions ----------------------
class EmailAlreadyExistsException(AppException):
    """Raised when a user is trying to create a new account but the email is already registered."""

    def __init__(
        self,
        message: str = "An account with this email already exists.",
        status_code: int = 409,
    ):
        super().__init__(message, status_code)


class InvalidCredentialsException(AppException):
    """Raised when a user is trying to log in but username or password is/are incorrect"""

    def __init__(
        self,
        message: str = "Invalid email or password.",
        status_code: int = 401,
    ):
        super().__init__(message, status_code)


# -------------------------   Category Exceptions ----------------------
class CategoryAccessDeniedException(AppException):
    """Raised when a user is trying to access a category which exists but is not a default / user's custom created category"""

    def __init__(
        self,
        message: str = "You do not have permission to access this category.",
        status_code: int = 403,
    ):
        super().__init__(message, status_code)


class CategoryNotFoundException(AppException):
    """Raised when the category user is trying to fetch does not exist"""

    def __init__(
        self,
        message: str = "Category does not exist",
        status_code: int = 404,
    ):
        super().__init__(message, status_code)


class CategoryAlreadyExistsException(AppException):
    def __init__(
        self,
        message: str = "A category with this name already exists.",
        status_code: int = 409,
    ):
        super().__init__(message, status_code)


class CategoryInUseException(AppException):
    """Raised when deleting a category that still has transactions attached to it."""

    def __init__(
        self,
        message: str = "Category is used by existing transactions. Move or delete them first.",
        status_code: int = 409,
    ):
        super().__init__(message, status_code)


class CategoryTypeMismatchException(AppException):
    """Raised when a transaction's type doesn't match its category's type (e.g. income in Food)."""

    def __init__(
        self,
        message: str = "Category type does not match the transaction type.",
        status_code: int = 422,
    ):
        super().__init__(message, status_code)


# -------------------------   Transaction Exceptions ----------------------


class TransactionNotFoundException(AppException):
    def __init__(
        self,
        message: str = "Transaction not found.",
        status_code: int = 404,
    ):
        super().__init__(message, status_code)


# -------------------------   User Exceptions ----------------------


class UserNotFoundException(AppException):
    def __init__(
        self,
        message: str = "User not found.",
        status_code: int = 404,
    ):
        super().__init__(message, status_code)


class FeatureDisabledException(AppException):
    """Raised when a request hits a feature that is turned off by a feature flag."""

    def __init__(
        self,
        message: str = "This feature is currently disabled",
        status_code: int = 503,
    ):
        super().__init__(message, status_code)


# -------------------------   AI Exceptions ----------------------


class LLMNotConfiguredException(AppException):
    """Raised when the configured LLM provider/model cannot be built (missing key, unknown provider)."""

    def __init__(
        self, message: str = "The AI assistant is not configured.", status_code: int = 503
    ):
        super().__init__(message, status_code)


class ConversationNotFoundException(AppException):
    """Raised when a conversation does not exist or belongs to another user.

    Deliberately 404, never 403: telling a user "this exists but isn't yours"
    confirms the id is real. Same reasoning as TransactionNotFoundException.
    """

    def __init__(self, message: str = "Conversation not found", status_code: int = 404):
        super().__init__(message, status_code)


# -------------------------   Rate limiting ----------------------


class RateLimitExceededException(AppException):
    """Raised when a user exceeds the per-window request limit for a route.

    429 is the correct code: the request was valid and authenticated, the client
    simply has to slow down. `Retry-After` tells it exactly how long.
    """

    def __init__(
        self,
        message: str = "Too many messages. Please wait a moment before sending another.",
        status_code: int = 429,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message, status_code, headers)
