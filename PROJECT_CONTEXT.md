# PROJECT_CONTEXT.md — Smart Expense Tracker

> **What this file is.** A factual snapshot of the codebase *as it exists today*, written so that an assistant
> answering a tracker step (see `AI_TRACKER.md`) can produce code that fits this repo exactly: right folders,
> right import paths, right patterns, right field names.
>
> **Snapshot:** repo `github.com/not-Sarabjit/smart-expense-tracker`, branch `main`, commit `df9d454` ("fix bug"),
> read on **2026-09-30**, and kept up to date as steps land — the sections below always describe the current state.
>
> **Which tracker steps are done is *not* recorded here.** That lives in a separate spreadsheet,
> **`PROGRESS_LOG.xlsx`** (one row per completed step: date, step id, what changed). Open it only when you
> actually need to know what has been completed; for writing code, this file alone is the source of truth.

---

## 0. Instructions for the assistant using this file

1. **Ground every answer in this file.** Use the exact paths, class names, function signatures and field names
   below. If a step needs something this file doesn't describe, say so and ask for the file's contents instead of
   guessing.
2. **The learner writes the backend by hand.** For each step, explain *what* and *why* (the concept, and how
   production teams do it), then give complete, copy-pasteable code with the file path at the top of each block,
   then say how to run and test it. Mark anything that's new vs. a modification of an existing file, and show
   modifications as the full updated function/class (not a vague "add this somewhere").
3. **Frontend work is done with Claude Code**, not by hand. For steps tagged `[FE]`, give a precise prompt the
   learner can paste into Claude Code, including the API contract (URL, method, request/response JSON, SSE event
   shapes) and which existing frontend files it should touch.
4. **Preferences, not orders.** The learner's suggested tools/approaches are preferences. If you see a better
   professional approach, explain the trade-offs and let the learner decide *before* changing course.
5. **Interview angle.** End each step with 2–4 likely interview questions on the step's concepts, with short
   model answers.
6. **Keep this file current.** At the end of each step that changes structure (new table, endpoint, env var,
   folder, dependency), give the exact text to add or change in this file. Then, separately, give one row for
   `PROGRESS_LOG.xlsx` in the form `Date | Step | What changed` — don't add it to this file.

---

## 1. Tech stack

| Layer | What's used | Notes |
|---|---|---|
| Backend framework | **FastAPI 0.139.0**, Uvicorn 0.51.0 | All existing endpoints are **sync** (`def`), so FastAPI runs them in a thread pool. |
| Language | Python — CI uses **3.12**; local version not recorded | |
| Database | **PostgreSQL** (installed locally, *not* in docker-compose), driver **psycopg2-binary 2.9.12** | Tests use **SQLite** (`backend/test.db`). |
| ORM / migrations | **SQLAlchemy 2.0.51** (legacy `Column(...)` declarative style, `declarative_base()`), **Alembic 1.18.5** | Queries use 2.0-style `select()` mostly; `UserRepository` still uses legacy `db.query()`. |
| Validation / config | **Pydantic 2.13.4**, **pydantic-settings 2.9.1**, email-validator, **tzdata 2025.2** | tzdata gives `zoneinfo` an IANA database on Windows (used to validate `users.timezone`) |
| Auth | JWT via **python-jose 3.5.0**, password hashing via **passlib 1.7.4 + bcrypt 4.0.1** | bcrypt is pinned to 4.0.1 because passlib breaks with newer bcrypt. |
| AI deps (optional extras) | `ai`: **langchain 1.4.3, langchain-core 1.6.6, langgraph 1.2.12, langchain-groq 1.1.3** (pulls groq 0.30.0), **langchain-qdrant 1.1.0, qdrant-client 1.19.1**. `embeddings`: **sentence-transformers 6.1.0** (pulls torch) | Upgraded in Step 0.10. No app code imports them yet (only `test_ai_stack.py`). `langchain-community` dropped. |
| Vector DB | **Qdrant** (docker-compose, ports 6333 REST / 6334 gRPC) | Config exists in `Settings`, no code uses it. |
| Logging | **structlog 26.1.0** | JSON lines with `request_id` / `user_id` (Step 0.9), see §4.2 |
| Tests | pytest 9.1.1, httpx 0.27.2 (TestClient), locust 2.46.4 (load test) | |
| Dependency management | **uv** + `pyproject.toml` | `uv.lock` committed; deps split into core and optional `ai` (light agent stack), `embeddings` (heavy, torch), `dev` |
| Linter / formatter | **Ruff** ≥0.7.0 | Config in `pyproject.toml [tool.ruff]`; also sets `pythonpath=["backend"]` for pytest (see §9) |
| CI | GitHub Actions `.github/workflows/tests.yml` | |
| Frontend | React 18 + TypeScript 5.6 + Vite 5 + Tailwind 3, axios, recharts, react-router-dom 7, vitest + Testing Library + fast-check | See §10. |

---

## 2. Repository layout

```
smart-expense-tracker/
├── pyproject.toml              # deps (core + optional ai/embeddings/dev), ruff config, pytest config (pythonpath=["backend"])
├── uv.lock                     # pinned transitive deps — committed
├── docker-compose.yml          # Only a `qdrant` service. Declares an unused `postgres_data` volume.
├── README.md                   # One line: "FastAPI + PostgreSQL expense tracking API with AI-assisted categorization."
├── docs/adr/                   # Architecture Decision Records: README.md (index + template), 0001-ai-assistant-architecture.md
├── .gitignore                  # includes backend/test.db
├── .github/workflows/tests.yml # uv sync --locked --extra dev --extra ai, ruff check + format --check, AI import check, pytest
├── .kiro/specs/smart-expense-tracker-frontend/   # Kiro spec-driven docs (requirements/design/tasks) for the frontend
├── .vscode/settings.json
├── backend/
│   ├── alembic.ini             # script_location = %(here)s/migrations ; URL injected from settings in env.py
│   ├── migrations/
│   │   ├── env.py              # sets sqlalchemy.url from settings.DATABASE_URL; target_metadata = Base.metadata; `import app.models`
│   │   └── versions/
│   │       ├── 4eedc669f0a4_initial_schema.py        # users, categories, transactions (downgrade also drops PG enums)
│   │       ├── 7fef2427edd8_add_default_categories.py # 18 default categories
│   │       └── b3c1d2e4f5a6_ai_era_schema.py         # users.currency/timezone, transactions.updated_at/source/import_batch_id, indexes (HEAD)
│   ├── conftest.py             # sets test env vars (DATABASE_URL, SECRET_KEY, …) before the app is imported
│   ├── locustfile.py           # Load test: register → login → create/list transactions
│   ├── test.db                 # SQLite test DB — untracked as of Step 0.1 (generated locally by pytest, in .gitignore)
│   └── app/
│       ├── __init__.py
│       ├── api/                # Routers (HTTP layer) + the FastAPI app
│       │   ├── main.py         # app = FastAPI(...), CORS, logging middleware, exception handlers, routers, /health
│       │   ├── auth.py         # /auth/register, /auth/login
│       │   ├── category.py     # /categories/...
│       │   ├── transaction.py  # /transactions/...
│       │   └── users.py        # /users/me (GET, PATCH)
│       ├── core/
│       │   ├── config.py       # Settings (pydantic-settings) → `settings` singleton
│       │   ├── exceptions.py   # AppException + domain exceptions
│       │   ├── logging.py      # setup_logging(), get_logger(), build_formatter() — structlog JSON
│       │   └── request_context.py # RequestContext ContextVar (request_id, user_id) + structlog processor
│       ├── database/
│       │   ├── base.py         # Base = declarative_base()
│       │   ├── session.py      # engine, SessionLocal, get_db()
│       │   └── unit_of_work.py # UnitOfWork(db): `with uow:` commits on success / rolls back on error
│       ├── dependencies/
│       │   ├── auth.py         # get_current_user (HTTPBearer + JWT decode)
│       │   └── features.py     # require_ai_enabled (AI_ENABLED kill switch → 503)
│       ├── middleware/
│       │   └── logging_middleware.py  # RequestLoggingMiddleware (pure ASGI): X-Request-ID + access log
│       ├── models/             # SQLAlchemy models; __init__.py imports Category, Transaction, User
│       │   ├── user.py
│       │   ├── category.py
│       │   └── transaction.py
│       ├── repositories/       # Data access (one class per aggregate, holds a Session)
│       │   ├── user_repository.py
│       │   ├── category_repository.py
│       │   └── transaction_repository.py
│       ├── schemas/            # Pydantic request/response models
│       │   ├── user.py  token.py  category.py  transaction.py
│       ├── services/           # Business logic
│       │   ├── auth_service.py  user_service.py  category_service.py  transaction_service.py
│       ├── utils/
│       │   └── date_utils.py   # last_day_of_month(year, month)
│       └── tests/
│           ├── conftest.py     # SQLite engine; db, client, user_a/b_headers, category_id, income_category_id; register_and_login()
│           └── Unit/
│               ├── test_auth.py
│               ├── test_config.py
│               ├── test_regressions.py   # one test (or more) per bug B1–B11
│               ├── test_unit_of_work.py  # atomicity: failing 3rd insert rolls back the first two
│               ├── test_users.py         # /users/me, preferences validation, source/updated_at
│               ├── test_logging.py       # JSON logs filtered by request_id; X-Request-ID handling
│               └── test_transaction.py
└── frontend/                   # see §10
```

**Note:** `app/api/` holds both the app (`main.py`) and routers. The app import path is `app.api.main:app`.

---

## 3. Running locally

All backend commands run **from `backend/`**, because `Settings` loads `.env` relative to the current working
directory and logs go to `./logs/`. `uv sync` and lint commands run **from the repo root** (where `pyproject.toml`
lives).

```bash
# backend/.env (not committed)
DATABASE_URL=postgresql://<user>:<pass>@localhost:5432/<db>
SECRET_KEY=<random string>
TOKEN_ALGORITHM=HS256
# optional (defaults shown)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=expense_docs
```

| Task | Command |
|---|---|
| Install deps | from repo root: `uv sync --extra dev --extra ai` (what CI installs). Add `--extra embeddings` only when you need local embedding models (downloads torch). Note `uv sync` removes extras you don't list. |
| Migrate DB | from `backend/`: `alembic upgrade head` |
| Run API | from `backend/`: `uvicorn app.api.main:app --reload` → http://localhost:8000, Swagger at `/docs` |
| Health | `GET /health` → `{"status":"ok"}` (no `/api/v1` prefix) |
| Lint | from repo root: `ruff check backend/` and `ruff format backend/ --check` |
| Tests | from `backend/`: `uv run pytest -v` (no env vars needed — `backend/conftest.py` sets test defaults; tests use SQLite). `test_ai_stack.py` is skipped if the `ai` extra isn't installed. |
| Qdrant | from repo root: `docker compose up -d qdrant` |
| Frontend | from `frontend/`: `npm install && npm run dev` → http://localhost:3000 (Vite proxies `/api` → `http://localhost:8000`) |
| Load test | from `backend/`: `locust` |

**Windows dev machine** (confirmed in Step 0.1). This matters later for Celery (needs `--pool=solo` on Windows)
and Docker (Docker Desktop).

---

## 4. Architecture & conventions (follow these in new code)

**Layering:** `router (app/api/*) → service (app/services/*) → repository (app/repositories/*) → model (app/models/*)`.

- **Routers** are thin: parse input via Pydantic schemas, get the user via `Depends(get_current_user)`, call a
  service, return a model (FastAPI serialises via `response_model`).
- **Dependency injection** uses small factory functions in each router file, e.g.
  ```python
  def get_transaction_service(db: Session = Depends(get_db)) -> TransactionService:
      return TransactionService(transaction_repository=TransactionRepository(db),
                                category_repository=CategoryRepository(db),
                                uow=UnitOfWork(db))
  ```
  Every service that writes takes a `uow: UnitOfWork` built on the **same** `Session` as its repositories.
- **Services** hold business rules (ownership checks, duplicate checks) and raise domain exceptions from
  `app.core.exceptions`. They receive `user_id: int` explicitly on every call — ownership is enforced by passing
  `user_id` down, not by a global context.
- **Repositories** wrap one `Session`, build queries with `select(...)`, and **only `flush()`** in write methods
  (`create`, `update`, `delete`) — they never commit.
- **Transactions (unit of work, Step 0.6):** services own the boundary. Wrap every write path in
  `with self.uow:` (`app.database.unit_of_work.UnitOfWork`): it commits when the block exits normally and rolls
  back on any exception, so several writes are atomic. Blocks nest — only the outermost commits — so a batch method
  can call single-item service methods (see `TransactionService.create_transactions`). A write made outside a
  `with uow:` block is **not** committed (the session is rolled back when `get_db` closes it).
- **Models** use legacy `Column(...)` style on `Base = declarative_base()`. New models should match this style unless
  a tracker step decides to modernise to `Mapped[...]`.
- **Schemas** use Pydantic v2 but `class Config: from_attributes = True` (deprecated style; `TransactionBase` uses
  `ConfigDict` import but not for config). New schemas should use `model_config = ConfigDict(from_attributes=True)`.
- **Naming:** snake_case files; one router/service/repository file per resource; exceptions named `XxxException`.
- **Docstrings:** short triple-quoted descriptions on routes and repository methods.
- **API prefix:** every router is mounted with `prefix="/api/v1"` in `main.py`.

### 4.1 Error handling (`app/api/main.py`, `app/core/exceptions.py`)

| Exception | Handler | Response |
|---|---|---|
| `AppException(message, status_code=400)` and subclasses | `app_exception_handler` | `{"error": true, "message": ..., "status_code": ...}` with that status |
| `HTTPException` | FastAPI default | `{"detail": ...}` |
| Pydantic validation | FastAPI default | 422 `{"detail": [...]}` |
| `SQLAlchemyError` | `database_exception_handler` | 503 `{"error": true, "message": "A database error occurred. Please try again later.", "status_code": 503}`; error + traceback logged server-side, never returned |
| any other `Exception` | `unhandled_exception_handler` | 500 `{"error": true, "message": "Internal server error", "status_code": 500}`; logged with traceback (`"Unhandled exception on METHOD path"`) |

Domain exceptions (all subclass `AppException`): `EmailAlreadyExistsException` (409), `InvalidCredentialsException`
(401), `CategoryAccessDeniedException` (403), `CategoryNotFoundException` (404), `CategoryAlreadyExistsException` (409),
`CategoryInUseException` (409), `CategoryTypeMismatchException` (422), `TransactionNotFoundException` (404),
`UserNotFoundException` (404), `FeatureDisabledException` (503).

Routers do **not** wrap service calls in try/except — services raise `AppException` subclasses and the global
handler renders them.

### 4.2 Logging (`app/core/logging.py`, `app/core/request_context.py`, `app/middleware/logging_middleware.py`)

- **structlog, JSON lines.** `setup_logging(level, json_logs)` runs at import of `main.py` (from
  `settings.app.log_level` / `settings.app.log_json`). structlog loggers **and** plain `logging.getLogger()` loggers
  go through the same processor chain (`ProcessorFormatter`) to stdout and `logs/app.log` (rotating 5 MB × 5, always
  JSON). `APP_LOG_JSON=false` switches the console to coloured key=value for local dev.
- Each line: `event`, `level`, `logger`, `timestamp` (ISO, UTC, `Z`), any key/values passed, plus **`request_id`**
  and **`user_id`** during a request, and `exception` (formatted traceback) when `exc_info` is given.
- **New code:** `from app.core.logging import get_logger`; `logger = get_logger(__name__)`;
  `logger.info("domain.event_name", some_id=..., count=...)`. Event names are dotted, past tense
  (`transaction.created`, `category.delete_blocked`, `auth.login_failed`). Never log passwords, tokens or emails.
- **Request ids:** `RequestLoggingMiddleware` (pure ASGI, outermost) reuses a well-formed incoming `X-Request-ID`
  (`[A-Za-z0-9._:-]{1,128}`) or generates `uuid4().hex`, stores a mutable `RequestContext` in a ContextVar, echoes
  `X-Request-ID` (exposed via CORS) and `request-process-time` on the response, and logs one `request.finished`
  line (`method`, `path`, `status_code`, `duration_ms`). `get_current_user` calls `bind_user_id(user.id)` so every
  later line carries `user_id` (works across thread-pool hops because the context object is shared, not re-bound).
  `get_request_id()` returns the current id (e.g. to pass into traces/jobs later). The 500 handler adds
  `X-Request-ID` itself (it runs outside the middleware). uvicorn's access log is silenced (WARNING) to avoid
  duplicate, id-less lines.
- Domain events logged today: `transaction.created/updated/deleted/batch_created`, `category.created/deleted/
  delete_blocked`, `auth.registered/logged_in/login_failed`, `request.database_error`,
  `request.unhandled_exception`.
- Filter one request: `grep '"request_id": "<id>"' backend/logs/app.log` (or `jq 'select(.request_id=="<id>")'`).
- **Not present yet:** tracing, metrics.

### 4.3 Config (`app/core/config.py`)

Grouped `pydantic-settings` classes (all `SettingsConfigDict(env_file=".env", extra="ignore")`); env var names stay
flat via `env_prefix`, Python access is grouped:

| Group (`settings.<x>`) | Class | Env vars (defaults) |
|---|---|---|
| `app` | `AppSettings` | `APP_NAME`, `APP_ENVIRONMENT` (`dev`\|`test`\|`prod`, default `dev`), `APP_DEBUG`, `APP_API_PREFIX`, `APP_LOG_LEVEL` (`INFO`), `APP_LOG_JSON` (`true`); `.is_prod` |
| `database` | `DatabaseSettings` | `DATABASE_URL` (required), `DATABASE_POOL_SIZE` 20, `DATABASE_MAX_OVERFLOW` 50, `DATABASE_POOL_TIMEOUT` 30, `DATABASE_ECHO` |
| `auth` | `AuthSettings` | `SECRET_KEY` (required), `TOKEN_ALGORITHM` HS256, `ACCESS_TOKEN_EXPIRE_MINUTES` 60 |
| `llm` | `LLMSettings` | `LLM_PROVIDER` groq, `LLM_MODEL`, `LLM_API_KEY`, `LLM_TEMPERATURE`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES` |
| `embeddings` | `EmbeddingSettings` | `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION` 384, `EMBEDDING_BATCH_SIZE` |
| `redis` | `RedisSettings` | `REDIS_URL` `redis://localhost:6379/0`, `REDIS_MAX_CONNECTIONS` |
| `qdrant` | `QdrantSettings` | `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION` |
| `ai` | `AISettings` | `AI_ENABLED` (default **false** — kill switch; enforce with `Depends(require_ai_enabled)`) |

Use `get_settings()` (lru-cached) in new code; in routes `settings: Settings = Depends(get_settings)` so tests can
override via `app.dependency_overrides[get_settings]`. The module-level `settings` object and its flat properties
(`settings.DATABASE_URL`, `SECRET_KEY`, `TOKEN_ALGORITHM`, `QDRANT_*`) are a deprecated shim still used by
`database/session.py`, `dependencies/auth.py` and `migrations/env.py`.

### 4.4 Database session (`app/database/session.py`)

```python
engine = create_engine(settings.DATABASE_URL, pool_size=20, max_overflow=50, pool_timeout=30)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
def get_db():            # one Session per request, closed in finally
```
Sync engine only; no async engine exists.

---

## 5. Data model

### `users` (`app/models/user.py`)
| column | type | notes |
|---|---|---|
| id | Integer PK | indexed |
| email | String | unique, indexed, not null |
| first_name | String | not null |
| last_name | String | nullable |
| hashed_password | String | not null |
| created_at | DateTime | `server_default=now()` |
| currency | String(3) | not null, default / server_default `'INR'` — ISO 4217, stored upper-case |
| timezone | String(64) | not null, default / server_default `'Asia/Kolkata'` — IANA name, validated with `zoneinfo` |

Relationships: `transactions` (cascade all, delete-orphan), `custom_categories` (cascade all, delete-orphan).
Read/update preferences via `GET/PATCH /api/v1/users/me`. For "today"/"this month" in the assistant, use
`ZoneInfo(user.timezone)`.

### `categories` (`app/models/category.py`)
| column | type | notes |
|---|---|---|
| id | Integer PK | |
| name | String | not null |
| category_type | Enum `'expense' \| 'income'` (PG enum `category_type`) | not null |
| user_id | FK → users.id, `ON DELETE CASCADE` | **NULL = default/global category**, else user's custom category |
| created_at | Date | `server_default=current_date` |

Unique constraint `uq_user_category_name_type (user_id, name, category_type)` — note: in PostgreSQL, rows with
`user_id IS NULL` never conflict, so the DB doesn't prevent duplicate defaults; the service does a case-insensitive
duplicate check instead.
Relationships: `user`, `transactions` (**no delete cascade**). Deleting a category that still has transactions is
refused by `CategoryService.delete_category` with `CategoryInUseException` (409) — the user must move or delete
those transactions first (B3 decision, Step 0.4).

**Default categories** (migration `7fef2427edd8`, `user_id = NULL`):
- income: Awards, Coupons, Grants, Lottery, Refunds, Rental, Salary, Sale
- expense: Bills, Clothing, Education, Electronics, Entertainment, Food, Health, Shopping, Sport, Transportation

### `transactions` (`app/models/transaction.py`)
| column | type | notes |
|---|---|---|
| id | Integer PK | indexed |
| amount | Numeric(12,2) | not null, always positive (sign comes from `type`) |
| type | Enum `TransactionType` (`income` / `expense`; PG enum `transaction_type`) | ⚠ Python attribute is `type`, API field alias is also `type`, but internal kwarg name is `transaction_type` |
| description | String(255) | nullable — the only free-text field (merchant/notes live here) |
| date | Date | not null, default today |
| user_id | FK → users.id `ON DELETE CASCADE` | not null |
| category_id | FK → categories.id | nullable, no ON DELETE rule at DB level |
| created_at | DateTime | `server_default=now()` |
| updated_at | DateTime | not null, `server_default=now()`, ORM `onupdate=now()`; backfilled from `created_at` |
| source | Enum `TransactionSource` (PG enum `transaction_source`: `manual`\|`chat`\|`import`\|`schedule`) | not null, default `manual`. Python member for "import" is `TransactionSource.import_` (`values_callable` stores values) |
| import_batch_id | Integer | nullable; **no FK yet** (FK to `import_batches` added in Phase 8) |

Indexes: `ix_transactions_id`, **`ix_transactions_user_id_date (user_id, date)`**,
**`ix_transactions_user_id_category_id (user_id, category_id)`**. No merchant/account/currency columns, no soft-delete.

Enum classes: `from app.models.transaction import TransactionType, TransactionSource`.
`TransactionRepository.create(..., source=TransactionSource.manual)`; `TransactionService.create_transaction(...,
source=...)` and `create_transactions(user_id, items, source=...)` pass it through (API writes are `manual`; chat
tools must pass `chat`, imports `import_`, schedules `schedule`).

**Migration head:** `b3c1d2e4f5a6`. New migrations: `alembic revision --autogenerate -m "..."` from `backend/`
(env.py imports `app.models`, so **new model modules must be imported in `app/models/__init__.py`** to be seen).
`alembic check` reports no drift between models and migrations. Migration rules used so far: additive only, new
columns nullable or with a server default, `op.add_column` with a PG enum needs an explicit
`<enum>.create(op.get_bind(), checkfirst=True)` (and `.drop` in downgrade). `migrations/env.py` escapes `%` in the
URL (URL-encoded passwords).

---

## 6. Authentication flow

1. `POST /api/v1/auth/register` → `AuthService.register` checks `get_by_email`, hashes with
   `pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")`, creates user, returns `UserOut`.
2. `POST /api/v1/auth/login` → verifies password, `_create_access_token(user.id)` →
   payload `{"sub": str(user_id), "iat": now_utc, "exp": now_utc + ACCESS_TOKEN_EXPIRE_MINUTES (default 60)}`
   signed with `settings.auth.secret_key` / `settings.auth.token_algorithm`.
   Returns `{"access_token": ..., "token_type": "bearer"}`.
3. Protected routes use `Depends(get_current_user)` (`app/dependencies/auth.py`): `HTTPBearer()` extracts the
   token → `jwt.decode` → `sub` → `UserRepository.get_by_id(int(sub))` → returns the `User` ORM object.
   Failure → 401 `{"detail": "Could not validate credentials"}`.
4. Frontend stores the token in `localStorage["access_token"]` and sends `Authorization: Bearer <token>`.

5. `GET /api/v1/users/me` returns the profile incl. `currency`/`timezone`; `PATCH /api/v1/users/me` updates
   `first_name`, `last_name`, `currency`, `timezone` (email is not editable there).

Not present: refresh tokens, logout/revocation, roles, rate limiting, account lockout.

**Reuse for new endpoints:** `current_user: User = Depends(get_current_user)` then use `current_user.id`.
For SSE/streaming endpoints the same header-based auth works (the frontend must use `fetch`, not `EventSource`,
to send headers).

---

## 7. API reference (current)

Base: `http://localhost:8000/api/v1`. All except auth require `Authorization: Bearer <jwt>`.

| Method & path | Input | Output | Behaviour / rules |
|---|---|---|---|
| POST `/auth/register` | `{email, first_name, last_name, password}` | 201 `UserOut {id, email, first_name, last_name, currency, timezone, created_at}` | 409 if email exists |
| POST `/auth/login` | `{email, password}` | `{access_token, token_type}` | 401 on bad creds |
| GET `/users/me` | – | `UserOut` | current user's profile + preferences |
| PATCH `/users/me` | `UserPreferencesUpdate {first_name?, last_name?, currency?, timezone?}` | `UserOut` | currency: 3 letters (upper-cased) else 422; timezone: valid IANA name else 422; blank first_name 422; unknown fields (e.g. email) ignored |
| GET `/categories/` | – | `CategoryOut[] {id, name, category_type, user_id}` | defaults (`user_id=null`) + user's custom |
| GET `/categories/{id}` | – | `CategoryOut` | 404 / 403 if another user's custom |
| POST `/categories/create_category` | `{name, category_type}` | 201 `CategoryOut` | name stripped, non-empty; 409 on case-insensitive duplicate (incl. defaults) |
| PUT `/categories/{id}` | `{name?, category_type?}` | `CategoryOut` | custom only (defaults → 403); duplicate check |
| DELETE `/categories/{id}` | – | 204 | custom only; **409 `CategoryInUseException` if any transaction uses it** (never deletes transactions) |
| GET `/transactions/summary?year=&month=` | `month` 1–12 (else 422) | `{income, expense, net}` (JSON numbers) | `SUM(amount) … GROUP BY type` in the DB over the whole month |
| GET `/transactions` | query: `transaction_type` (`income`\|`expense`), `category_id`, `start_date`, `end_date`, `sort_by` (`date`\|`amount`), `sort_order` (`asc`\|`desc`), `limit` (1–200, default 50), `offset` (≥0, default 0) | `TransactionOut[]` + header **`X-Total-Count`** (total matching rows; exposed via CORS) | invalid enum/paging values → 422; ties broken by `id` so pages are stable |
| POST `/transactions` | `{amount>0, date<=today, type, category_id?, description?}` | 201 `TransactionOut` | category must exist (404), be default or own (403), and its `category_type` must equal `type` (422) |
| GET `/transactions/{id}` | – | `TransactionOut` | other user's → 404 |
| PUT `/transactions/{id}` | `TransactionUpdate {amount?, date?, type? (alias: transaction_type), category_id?, description?}` | `TransactionOut` | when `type` or `category_id` changes, the (new or existing) category is re-validated: exists / owned / type matches |
| DELETE `/transactions/{id}` | – | 204 | other user's → 404 |

`TransactionOut` JSON example (note `amount` is a **string** because it's `Decimal`):
```json
{"amount": "42.50", "date": "2026-08-01", "type": "expense", "category_id": 3,
 "description": "Weekly groceries", "id": 17, "source": "manual",
 "created_at": "2026-08-01T10:22:31", "updated_at": "2026-08-01T10:22:31"}
```

---

## 8. Services & repositories (signatures to reuse from AI tools)

```python
# app/repositories/transaction_repository.py
class TransactionRepository:
    def __init__(self, db: Session)
    SORT_COLUMNS = {"date": ..., "amount": ...}            # whitelist; unknown sort_by -> ValueError
    def get_all_for_user(self, user_id, transaction_type=None, category_id=None, start_date=None,
                         end_date=None, sort_by='date', sort_order='desc', limit=50, offset=0) -> list[Transaction]
    def count_for_user(self, user_id, transaction_type=None, category_id=None, start_date=None,
                       end_date=None) -> int
    def get_totals_by_type(self, user_id, start_date=None, end_date=None) -> {'income': Decimal, 'expense': Decimal}
    def get_by_id(self, transaction_id, user_id) -> Transaction | None
    def create(self, amount, transaction_type, description, date, user_id, category_id=None) -> Transaction  # commits
    def update(self, transaction, **kwargs) -> Transaction   # setattr + commit
    def delete(self, transaction) -> None                    # commits

# app/repositories/category_repository.py
class CategoryRepository:
    def get_all_for_user(self, user_id) -> list[Category]    # defaults + custom
    def get_by_id(self, id) -> Category | None               # NOT user-scoped; service checks ownership
    def count_transactions(self, category_id) -> int         # used to block deleting a category in use
    def create(self, name, category_type, user_id) -> Category
    def update(self, category, **kwargs) -> Category
    def delete(self, category) -> None

# app/repositories/user_repository.py
class UserRepository:
    def get_by_id(self, user_id) / get_by_email(self, email) / create(...) / update(self, user, **kwargs)

# app/database/unit_of_work.py
class UnitOfWork:
    def __init__(self, db: Session)
    __enter__/__exit__   # outermost exit: commit (rollback + re-raise if commit fails); any exception: rollback
    def commit(self) / rollback(self)

# app/services/transaction_service.py
class TransactionService(transaction_repository, category_repository, uow):
    get_transaction(transaction_id, user_id)
    create_transaction(user_id, amount, transaction_type, description, date, category_id)
    create_transactions(user_id, items: Iterable[dict]) -> list[Transaction]   # atomic batch; item keys =
                                                     # amount, transaction_type, description?, date, category_id?
    list_transactions(user_id, transaction_type=None, category_id=None, start_date=None, end_date=None,
                      sort_by='date', sort_order='desc', limit=50, offset=0)
    count_transactions(user_id, transaction_type=None, category_id=None, start_date=None, end_date=None)
    update_transaction(user_id, transaction_id, **fields)   # accepts transaction_type=…, mapped to model attr `type`
    delete_transaction(user_id, transaction_id)
    get_monthly_summary(user_id, year, month) -> {'income', 'expense', 'net'}   # Decimals, aggregated in SQL
    _validate_category(user_id, category_id, transaction_type)  # exists / owned-or-default / type matches

# app/services/category_service.py
class CategoryService(category_repository, uow):
    list_category(user_id) / get_category(user_id, category_id) / create_category(user_id, name, category_type)
    update_category(user_id, category_id, name=None, category_type=None) / delete_category(user_id, category_id)

# app/services/auth_service.py  — AuthService(user_repository, uow): register(...), login(email, password) -> token
#   JWT payload {"sub", "iat", "exp"}; iat/exp are UTC-aware; lifetime = settings.auth.access_token_expire_minutes
# app/services/user_service.py  — UserService(user_repository, uow): get_profile(user_id),
#   update_profile(user_id, first_name=None, last_name=None, email=None, currency=None, timezone=None)  — used by api/users.py
```

AI tools should call **services** (so business rules are reused), never repositories directly, and always pass
`user_id` from the authenticated context.

---

## 9. Tests & CI

- `backend/app/tests/conftest.py`: SQLite file `./test.db`; `db` fixture does `Base.metadata.create_all` / `drop_all`
  per test; `client` fixture overrides `get_db` and yields a `TestClient(app)`.
- Helper `register_and_login(client, email)` lives in `app/tests/conftest.py` (import it with
  `from app.tests.conftest import register_and_login`) and returns auth headers. Fixtures: `user_a_headers`,
  `user_b_headers`, `category_id` (user A's **expense** category "Groceries"), `income_category_id` (user A's
  **income** category "Paycheck"). A transaction's category must match its type (B6).
- `backend/conftest.py` sets `DATABASE_URL` / `SECRET_KEY` / `TOKEN_ALGORITHM` / `APP_ENVIRONMENT=test` /
  `AI_ENABLED=false` defaults, so the suite needs no `.env`.
- `test_regressions.py` has one test (or more) per bug B1–B11, each verified to fail on the pre-fix code. For
  asserting 500 responses use `TestClient(app, raise_server_exceptions=False)` (the `raw_client` fixture there).
- Logs: structlog passes stdlib an event **dict** as `record.msg` — in `caplog` assertions read
  `record.msg["event"]` / `record.msg["exc_info"]`; or use the `json_logs` fixture in `test_logging.py` to assert on
  the rendered JSON lines.
- `test_unit_of_work.py` checks commits through a **separate** session (`TestingSessionLocal` from
  `app/tests/conftest.py`) so only committed data is visible — reuse that pattern for atomicity tests.
- `pyproject.toml [tool.pytest.ini_options]` sets `pythonpath = ["backend"]` so bare `pytest` / `uv run pytest`
  resolves `import app...`.
- CI: GitHub Actions, Python 3.12, uv with cache, `uv sync --locked --extra dev --extra ai` (no `embeddings` extra →
  no torch download), `ruff check backend/` + `ruff format backend/ --check`,
  `python -c "import langgraph, langchain_groq"`, then `uv run pytest -v` in `backend/`. No secrets needed.
- `ruff check backend/` and `ruff format backend/ --check` are both clean.

---

## 10. Frontend (for `[FE]` steps done with Claude Code)

- **Stack:** React 18, TS, Vite 5 (dev port **3000**, proxy `/api` → `:8000`), Tailwind 3 (dark mode via
  `utils/theme.ts`), axios, recharts, react-router-dom 7. Tests: vitest + Testing Library + fast-check.
- **Routes (`src/App.tsx`):** `/login` (AuthPage; redirects to `/dashboard` if logged in), protected
  `/dashboard` (DashboardPage), `/categories` (CategoriesPage) and `/settings` (SettingsPage: name, currency,
  timezone via `GET/PATCH /users/me`) under `ProtectedRoute`; `*` → `/dashboard`. `ProtectedRoute` renders the
  single `Navbar` (Dashboard · Categories · Settings links) — pages must not render their own.
- **Current user (Step 0.8):** `ProtectedRoute` wraps everything in `context/CurrentUserProvider.tsx`, which loads
  `GET /users/me` once. Read it with `useCurrentUser()` → `{user, loading, error, refresh, setUser}` or
  `useCurrency()` → ISO code (default `"INR"` before load), both in `hooks/useCurrentUser.ts`. The profile is
  **not** stored in localStorage any more (`useAuth` only removes the legacy `user_profile` key).
- **Money formatting:** `utils/formatters.ts` `formatMoney(amount, currency)` (Intl, e.g. `₹1,234.50`) — use it with
  `useCurrency()` everywhere money is shown (SummaryCards, TransactionList do). `formatCurrency(amount, symbol)` is
  the older symbol-prefix helper.
- **API layer (`src/api/`):** `client.ts` = axios instance, `baseURL: "/api/v1"`, request interceptor adds the
  Bearer token from `localStorage["access_token"]`, response interceptor on 401 clears the token and does
  `window.location.href = "/login"`. Resource modules: `auth.ts`, `transactions.ts`, `categories.ts`, `users.ts`
  (`getMe()`, `updateMe(payload)`).
  `transactions.ts` normalises the API's string `amount` to a number (`normalizeTransaction`); `getTransactions(params)`
  returns one page `{items, total}` (`limit`/`offset`, total from `X-Total-Count`); `getAllTransactions(params)` pages
  through everything (200/request, cap 5000); `getSummary` returns `{income, expense, net}` as numbers.
- **Errors:** `utils/errorHandling.ts` `extractErrorMessage(err, fallback)` understands the AppException body
  (`message`), FastAPI `detail` (string or array) and network errors — use it for every API error shown in the UI.
- **Hooks (`src/hooks/`):** `useAuth` (login/register/logout/isAuthenticated; token in localStorage only),
  `useCurrentUser` / `useCurrency`, `useTransactions` (all rows for the period via `getAllTransactions`; exposes
  `transactions`, `total`), `useCategories`, `useDashboardSummary`.
- **Components:** `layout/` (Navbar, ProtectedRoute), `dashboard/` (MonthPicker, TransactionList, BarChartWidget,
  DonutChartWidget, SummaryCards), `transactions/TransactionForm`, `ui/` (LoadingSpinner, ConfirmModal, EmptyState).
- **Types:** `src/types/index.ts` — `User` (incl. `currency`, `timezone`; `last_name: string | null`),
  `UserPreferencesUpdatePayload`, `TransactionResponse` (wire shape, `amount: string`) vs `Transaction` (app shape,
  `amount: number`); `category_id: number | null`; `Category.user_id: number | null` (null = default category,
  shown with a "Default" badge and no edit/delete on CategoriesPage); `MonthlySummary {income, expense, net}`;
  `TransactionPage {items, total}`.
- `TransactionList` renders 50 rows at a time ("Show more") with a "Showing N of total" footer.
- FE/BE contract mismatches from the snapshot (B4 etc.) were fixed in Step 0.5. Checks: from `frontend/`,
  `npx tsc -b`, `npx eslint src`, `npx vitest run` (all clean).
- **For the chat feature:** there's no chat UI, no SSE handling, no global state library (state is in hooks),
  no file upload component. A chat panel will need `fetch` + `ReadableStream` for SSE (so it can send the
  Authorization header).

---

## 11. Existing AI groundwork

- **Step 0.10 upgraded the stack** to LangChain 1.x / LangGraph 1.x (versions in §1): optional extra `ai` (light,
  installed in CI) and `embeddings` (sentence-transformers → torch, never in CI). `langchain-community` and the
  0.3.x line are gone. Still no app code imports them; `app/tests/Unit/test_ai_stack.py` proves a LangGraph
  `StateGraph` compiles/runs and `ChatGroq` constructs offline. Write new code against the 1.x APIs
  (`langgraph.graph.StateGraph`, `START`/`END`, `langchain_groq.ChatGroq`, `langchain_qdrant.QdrantVectorStore`).
- Qdrant settings in `Settings` and a Qdrant container in `docker-compose.yml`.
- README mentions "AI-assisted categorization" — **not implemented**.
- Versions available on PyPI as of 2026-09-30 (for the upgrade step): langchain 1.4.3, langchain-core 1.6.6,
  langgraph 1.2.12, langchain-groq 1.1.3, langchain-qdrant 1.1.0, langgraph-checkpoint-postgres 3.1.2,
  qdrant-client 1.19.1, sentence-transformers 6.1.0, celery 5.6.3, celery-redbeat 2.4.2, redis 8.1.0,
  langfuse 4.16.0, docling 2.131.0, sqlglot 30.20.0, sse-starlette 3.5.0, psycopg 3.3.6, fastapi 0.142.2.
  Not yet added (later phases): langgraph-checkpoint-postgres, psycopg 3, celery, celery-redbeat, redis, langfuse,
  docling, sqlglot, sse-starlette.

---

## 12. Known issues & gaps

**Confirmed by running the code** (a probe test on 2026-09-30):

| # | Issue | Where | Impact |
|---|---|---|---|
| ~~B1~~ | **Resolved in Step 0.4** — `update_transaction` maps `transaction_type` → `type`; `TransactionUpdate` accepts `type` or `transaction_type`. | | |
| ~~B2~~ | **Resolved in Step 0.4** — summary uses `TransactionRepository.get_totals_by_type` (`SUM … GROUP BY type`); `month` validated 1–12. | | |
| ~~B3~~ | **Resolved in Step 0.4** — ORM cascade removed; deleting a category in use → 409 `CategoryInUseException`. | | |
| ~~B4~~ | **Resolved in Step 0.5** — FE uses `income`/`expense`/`net`. | | |

**Found by reading the code:**

| # | Issue | Where |
|---|---|---|
| ~~B5~~ | **Resolved in Step 0.4** — category re-validated (exists / owned) on update. | |
| ~~B6~~ | **Resolved in Step 0.4** — category_type must equal the transaction type on create/update → 422 `CategoryTypeMismatchException`. | |
| ~~B7~~ | **Resolved in Step 0.4** — `limit` (≤200) / `offset` + `X-Total-Count`; `sort_by` / `sort_order` / `transaction_type` validated (422). | |
| ~~B8~~ | **Resolved in Step 0.4** — DB and unhandled errors return generic bodies and are logged with tracebacks. | |
| ~~B9~~ | **Resolved in Step 0.4** — `iat` / `exp` are UTC-aware. | |
| ~~B10~~ | **Resolved in Step 0.4** — `update(user, **updates)`. | |
| ~~B11~~ | **Resolved in Step 0.4** — try/except removed from `register` / `login`. | |
| ~~B12~~ | **Resolved in Step 0.4** — `CategoryRepository.get_all_for_user` used `Category.user_id is None` (Python identity → always False), so **default categories were never listed** and the duplicate check ignored them. Now `.is_(None)`. | |
| ~~G1~~ | ~~`requirements.txt` is UTF-16 LE/CRLF...~~ **Resolved in Step 0.1** — migrated to `pyproject.toml` (UTF-8) + `uv.lock`; deps split into core/`ai`/`dev` groups; Ruff added. | repo root |
| ~~G2~~ | **Resolved in Step 0.6** — repositories flush; `UnitOfWork` in services owns commit/rollback. | |
| ~~G3~~ | **Resolved in Step 0.7** — `ix_transactions_user_id_date`, `ix_transactions_user_id_category_id`. | |
| ~~G4~~ | **Resolved in Step 0.7** — `users.currency` / `users.timezone`. | |
| ~~G5~~ | **Resolved in Steps 0.7 (BE) + 0.8 (FE)** — `GET/PATCH /users/me`; FE reads the profile from it, settings page edits preferences. | |
| G6 | ~~Request IDs, structured logs~~ (**resolved in Step 0.9**). Still missing: tracing, metrics, rate limiting, Redis client code, background jobs, object storage. | – |
| G7 | ~~`test.db` committed~~ **Partially resolved in Step 0.1** — removed from git tracking, added to `.gitignore` (file still exists locally, generated by pytest). `Settings` still needs env vars even for tests. | tests |
| G8 | Postgres not in docker-compose (unused `postgres_data` volume declared). | docker-compose |

---

## 13. Decisions already made for the AI feature

Agreed during planning (details and order live in `AI_TRACKER.md`). Recorded formally, with alternatives and
consequences, in **`docs/adr/0001-ai-assistant-architecture.md`** — add ADR 0002+ for later significant decisions
(e.g. tracing backend in 2.1, checkpoint vs `messages` table as source of truth in 4.1):

- **Goal:** a Rovo-style agentic chat assistant: natural-language CRUD on transactions/categories, dynamic
  questions over the user's data (with clarifying questions), bulk analysis/insights, document upload
  (statements, Excel) → import/analyse, exports (xlsx/csv/pdf), and user-defined schedules.
- **Architecture:** Chat API (SSE) → **LangGraph** orchestrator running an agent loop → **tool gateway** (validation,
  user-scoping, policy, audit, rich errors) → tools. Context builder, layered guardrails, human-in-the-loop
  confirmation for writes, observability and evals as first-class parts.
- **Data access strategy — "A + C now, B later":**
  - **A** — one flexible `query_transactions` tool: the LLM fills a validated JSON *query spec* (filters, group-by,
    aggregations, sort, limit) that our code compiles to SQLAlchemy with `user_id` always forced. (Rovo's JQL pattern.)
  - **C** — "code mode": for deep analysis the LLM writes pandas code run in a locked-down **Docker sandbox** over
    only the user's data.
  - **B** — guarded text-to-SQL (read-only role, Postgres RLS, sqlglot validation) as a later, optional phase.
  - **Writes always go through typed tools, never generated SQL.**
- **Stack:** LangGraph 1.x (orchestration, checkpointer, interrupts), LangChain 1.x (chat/embedding/vector-store
  abstractions), **Groq free models** first (must support tool calling), provider-swappable via config
  (ports & adapters), local **sentence-transformers** embeddings, **Qdrant** (already present), **Redis**,
  **Celery + RedBeat**, **MinIO** (S3-compatible), Docker-based sandbox, **Langfuse** (self-hosted) for tracing,
  structlog, Docling/pandas/openpyxl for parsing, DeepEval for evals.
- **Skills:** our own progressive-disclosure implementation (`SKILL.md` files + a `load_skill` tool).
- **Runs locally**, but infra is built the way production apps do it (queues, sandbox, object storage, tracing).
- **Division of labour:** learner hand-writes backend Python from step instructions; frontend via Claude Code.

---

## 14. Where progress is tracked

Completed tracker steps are **not** listed in this file. They live in **`PROGRESS_LOG.xlsx`**, one row per
completed step, newest at the bottom:

| Column | Meaning |
|---|---|
| `Date` | `YYYY-MM-DD` the step was finished |
| `Step` | tracker step id (`0.1`, `3.4`, …) or `snapshot` |
| `What changed` | files/tables/endpoints/env vars touched, and anything worth remembering |

**Only open it when the question is "what has been done so far?"** — for example when planning what to do next,
or when a step's prerequisites are unclear. For writing code against the current state of the repo, sections
1–13 above are the source of truth and are kept current as steps land, so the spreadsheet adds nothing.

After finishing a step, update the relevant sections above **and** append one row to `PROGRESS_LOG.xlsx`.
