from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.ai.agent.graph import get_compiled_graph
from app.api import auth, category, chat, transaction, users
from app.core.config import Settings, get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.core.request_context import REQUEST_ID_HEADER, get_request_id
from app.middleware.logging_middleware import RequestLoggingMiddleware

setup_logging(level=get_settings().app.log_level, json_logs=get_settings().app.log_json)

logger = get_logger(__name__)


# inside the lifespan, before `yield`:
if get_settings().ai.enabled:
    get_compiled_graph()


app = FastAPI(
    title="Expense Tracker API",
    version="1.0.0",
)

# List of browser origins allowed to use backend
origins = [
    "http://localhost:3000",  # React frontend
    "http://127.0.0.1:3000",
]

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # which origins can call this API
    allow_credentials=True,  # allow cookies/Authorization headers
    allow_methods=["*"],  # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Authorization, Content-Type, etc.
    # let the browser read the pagination total and the correlation id
    expose_headers=["X-Total-Count", REQUEST_ID_HEADER],
)

# Request id + access log middleware (added last = outermost, so it wraps CORS too)
app.add_middleware(RequestLoggingMiddleware)


# --- Global exception handlers ---


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Catch-all for anything unexpected: log the traceback server-side,
    # never send it (or the exception text) to the client
    logger.error(
        "request.unhandled_exception",
        method=request.method,
        path=request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    # This handler runs outside RequestLoggingMiddleware, so add the id header here
    request_id = get_request_id()
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500,
        },
        headers={REQUEST_ID_HEADER: request_id} if request_id else None,
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
):
    # The exception text contains SQL and parameters — log it, don't return it
    logger.error(
        "request.database_error",
        method=request.method,
        path=request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=503,
        content={
            "error": True,
            "message": "A database error occurred. Please try again later.",
            "status_code": 503,
        },
    )


@app.get("/health")
def health_check(settings: Settings = Depends(get_settings)):
    """Liveness probe + which environment and feature flags this process is running with."""
    return {
        "status": "ok",
        "environment": settings.app.environment,
        "ai_enabled": settings.ai.enabled,
    }


API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX, tags=["Auth"])
app.include_router(category.router, prefix=API_PREFIX, tags=["Categories"])
app.include_router(transaction.router, prefix=API_PREFIX, tags=["Transactions"])
app.include_router(users.router, prefix=API_PREFIX, tags=["Users"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
