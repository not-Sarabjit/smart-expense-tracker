class AppException(Exception):
    """Base class for all custom application exceptions."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
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
    """ Raised when a user is trying to access a category which exists but is not a default / user's custom created category"""
    def __init__(
        self,
        message: str = "You do not have permission to access this category.",
        status_code: int = 403,
    ):
        super().__init__(message, status_code)

class CategoryNotFoundException(AppException):
    """Raised when the category user is trying to fetch does not exist """
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

# -------------------------   User Exceptions ----------------------
class AIServiceError(AppException):
    def __init__(self, message: str = "AI service temporarily unavailable.", original_error: Exception = None):
        self.original_error = original_error
        super().__init__(message=message, status_code=503)


class AIRateLimitError(AIServiceError):
    def __init__(self, message: str = "AI service rate limit reached. Please try again shortly.", original_error: Exception = None):
        super().__init__(message=message, original_error=original_error)
        self.status_code = 429


class AITokenLimitError(AIServiceError):
    def __init__(self, message: str = "Input too long for AI model.", original_error: Exception = None):
        super().__init__(message=message, original_error=original_error)
        self.status_code = 400