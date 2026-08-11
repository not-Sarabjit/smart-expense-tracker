from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, category, transaction
from app.middleware.logging_middleware import RequestLoggingMiddleware


app = FastAPI(
    title="Expense Tracker API",
    version="1.0.0",
)

# List of browser origins allowed to use backend
origins = [
    "http://localhost:3000",   # React frontend
    "http://127.0.0.1:3000"
]

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # which origins can call this API
    allow_credentials=True,     # allow cookies/Authorization headers
    allow_methods=["*"],        # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],        # Authorization, Content-Type, etc.
)

# Logging Middleware
app.add_middleware(RequestLoggingMiddleware)

@app.get("/health")
def health_check():
    return {"status": "ok"}



API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX, tags=["Auth"])
# app.include_router(users.router, prefix=API_PREFIX, tags=["Users"])
app.include_router(category.router, prefix=API_PREFIX, tags=["Categories"])
app.include_router(transaction.router, prefix=API_PREFIX, tags=["Transactions"])