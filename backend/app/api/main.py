import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api import auth, category, transaction
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.middleware.logging_middleware import RequestLoggingMiddleware
from fastapi import Depends, FastAPI
from app.core.config import Settings, get_settings


setup_logging()

logger = logging.getLogger(__name__)


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
)

# Logging Middleware
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
    # Catch-all for anything unexpected so the API never leaks a raw traceback
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
):
    logger.exception("DATABASE ERROR")

    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
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
