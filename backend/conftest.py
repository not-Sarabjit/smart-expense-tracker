# backend/conftest.py
"""Test environment bootstrap.

Runs before any test module (and therefore before app.core.config is imported),
so the test suite never needs a real .env, real secrets, or a real database.

setdefault, not assignment: an explicitly-exported env var still wins, which lets
you point the suite at something else from the shell when you need to.
"""

import os

# Never connected to — app/tests/conftest.py overrides get_db with SQLite.
# It must still be a Postgres-style URL because app/database/session.py passes
# pool_size/max_overflow to create_engine, which SQLite's pool rejects.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/test_db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-used-outside-tests")
os.environ.setdefault("TOKEN_ALGORITHM", "HS256")
os.environ.setdefault("APP_ENVIRONMENT", "test")
os.environ.setdefault("AI_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
