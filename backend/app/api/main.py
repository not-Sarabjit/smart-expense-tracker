from fastapi import FastAPI

from app.api import auth, category, transaction

app = FastAPI(
    title="Expense Tracker API",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}



API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX, tags=["Auth"])
# app.include_router(users.router, prefix=API_PREFIX, tags=["Users"])
app.include_router(category.router, prefix=API_PREFIX, tags=["Categories"])
app.include_router(transaction.router, prefix=API_PREFIX, tags=["Transactions"])