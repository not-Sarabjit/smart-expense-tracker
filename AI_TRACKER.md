# AI_TRACKER.md — Rovo-style AI assistant for Smart Expense Tracker

> Phased build plan, ordered the way product teams actually ship: pay down the debt the feature will hit, get a
> thin end-to-end slice working, add observability *before* complexity, then grow capability behind tests and
> evals. Read together with **`PROJECT_CONTEXT.md`** (the current state of the code).

---

## How to use this tracker

### Set up the Claude project
1. Create a Claude project and upload **`PROJECT_CONTEXT.md`** and **`AI_TRACKER.md`**.
2. Paste this into the project's custom instructions:

```text
You are my senior engineer and mentor. I'm adding a Rovo-style agentic AI assistant to my FastAPI expense
tracker. PROJECT_CONTEXT.md describes my codebase as it is now; AI_TRACKER.md is the plan. Follow section 0 of
PROJECT_CONTEXT.md for how to answer.

When I give you a step ID (e.g. "Step 3.4"):
1. Explain the goal, the concepts involved and how production teams do this — in plain language first.
2. List the files you'll create/modify.
3. Give complete, copy-pasteable backend code, one block per file with its path, matching my existing
   conventions (layering, DI factories, AppException, naming). Show modified functions in full.
4. Give the commands to run it, the tests to add, and how to verify the "Done when" criteria.
5. For [FE] work, give me a precise prompt for Claude Code with the API contract.
6. Give 2–4 interview questions with short answers.
7. Give the PROJECT_CONTEXT.md update and a progress-log line.

If I suggest a tool or approach and you know a better professional option, explain the trade-offs and let
me decide before changing. If you need to see a file that isn't described in the context, ask for it.
Use library APIs for the versions pinned in my requirements; if unsure an API exists in that version, say so.
```

3. For each step, start a new chat in the project (keeps context small) with:

```text
Step <id>. <optional: what I've done so far / errors I hit / files I changed that aren't in the context yet>
```

### Work like a professional team
- **Branch per phase:** `feat/ai-phase-<n>`; **one commit per step** with a conventional message
  (`feat(chat): add SSE streaming endpoint`); open a PR into `dev`, let CI run, merge.
- **Definition of done for every step:** code in place · existing + new tests pass · lint clean · "Done when"
  criteria checked · `PROJECT_CONTEXT.md` updated · committed.
- Tick the checkbox here when a step is done.

### Legend
`[BE]` backend — you write it by hand · `[FE]` frontend — Claude Code does it · `[BE+FE]` both ·
**Concepts** = what to be able to explain in an interview · 🎯 **Milestone** = demo-able checkpoint.

---

## Target architecture

```
                        ┌────────────────────────── React frontend ──────────────────────────┐
                        │ chat panel · confirm cards · uploads · charts · notifications      │
                        └───────────────┬───────────────────────────────▲────────────────────┘
                              HTTPS + JWT│                          SSE │ (tokens, tool status,
                                         ▼                              │  confirmations, jobs)
┌───────────────────────────── FastAPI (API process) ─────────────────────────────────────────┐
│ auth · rate limit (Redis) · request-id · chat / files / jobs / schedules routers             │
│                                                                                              │
│  LangGraph agent harness (per chat turn, state checkpointed in Postgres)                     │
│   input guardrails → context builder → LLM ⇄ tool gateway ⇄ tools → output guardrails        │
│                         │  (loop)          │ validate · user-scope · policy · audit · errors  │
│                         │                  ├─ data tools (query spec → SQLAlchemy)  [A]       │
│                         │                  ├─ write tools ── interrupt() → user confirms      │
│                         │                  ├─ analysis tool → Docker sandbox (pandas) [C]     │
│                         │                  ├─ document tools → staged imports / RAG search    │
│                         │                  ├─ export tool · schedule tools · memory · skills  │
│                  LLM gateway (Groq / Claude / … swappable, fallbacks)                        │
└───────┬───────────────┬────────────────┬──────────────┬──────────────┬──────────────────────┘
        ▼               ▼                ▼              ▼              ▼
   PostgreSQL        Redis          Qdrant         MinIO (S3)     Langfuse
   app data,      rate limits,     document        uploads,       traces, costs,
   checkpoints,   cache, locks,    embeddings      exports,       prompts, eval
   memories       broker, pub/sub                  charts         datasets
                        │
                        ▼
              Celery workers + Beat (RedBeat)
              ingestion · analysis · exports · scheduled agent runs · notifications
```

## Target backend layout (new code)

```
backend/
├── app/
│   ├── ai/
│   │   ├── llm/            # model factory, fallbacks, token counting
│   │   ├── agent/          # state.py, graph.py, nodes/, runner.py (chat + headless)
│   │   ├── prompts/        # versioned prompt files + loader
│   │   ├── tools/          # context.py, registry.py, gateway.py, policy.py, <domain>_tools.py
│   │   ├── query/          # spec.py (QuerySpec), compiler.py (→ SQLAlchemy)
│   │   ├── memory/         # summarisation, long-term store
│   │   ├── skills/         # loader.py (skill content lives in backend/skills/)
│   │   ├── rag/            # embeddings.py, vectorstore.py, chunking.py, retriever.py
│   │   ├── documents/      # parsers/, extraction.py, categorise.py, dedup.py
│   │   ├── sandbox/        # runner.py (interface), docker_runner.py, harness/
│   │   ├── guardrails/     # input.py, output.py
│   │   └── observability/  # tracing.py, usage.py
│   ├── api/                # + chat.py, files.py, jobs.py, events.py, schedules.py, notifications.py, users.py
│   ├── workers/            # celery_app.py, tasks/
│   ├── storage/            # FileStorage interface, local + S3 implementations
│   └── core/redis.py       # Redis client
├── skills/<skill-name>/SKILL.md
├── sandbox/Dockerfile
├── evals/                  # datasets/, runners, reports
└── scripts/                # seed_demo_data.py, etc.
```

---

## Phase 0 — Groundwork: fix what the AI will trip over

*Why first:* an agent amplifies bugs. If the summary is wrong, the assistant confidently says wrong numbers; if
deleting a category silently deletes transactions, an agent will do it at scale.

- [ ] **0.1 [BE] Dev environment & dependency hygiene**
  - **Goal:** confirm OS and Python version, use a virtualenv, convert `requirements.txt` to UTF-8, split deps
    into `requirements/base.txt`, `requirements/ai.txt`, `requirements/dev.txt` (or move to `pyproject.toml` + `uv` —
    decide after the trade-off discussion), add **ruff** for lint/format, remove `backend/test.db` from git and
    ignore it.
  - **Concepts:** reproducible environments, dependency pinning, lockfiles, linters.
  - **Done when:** a fresh venv installs cleanly; `ruff check` runs; `git diff` on requirements is readable.

- [ ] **0.2 [BE] Local infrastructure in Docker Compose**
  - **Goal:** extend `docker-compose.yml` with **Redis** (and optionally Postgres, keeping your local one working),
    healthchecks, named volumes; add `.env.example` listing every variable.
  - **Concepts:** containers vs processes, healthchecks, 12-factor config, why infra runs in Docker locally.
  - **Done when:** `docker compose up -d` brings up Redis + Qdrant healthy; `redis-cli ping` → PONG.

- [ ] **0.3 [BE] Settings refactor**
  - **Goal:** `SettingsConfigDict`, grouped settings (app/env, database, auth, llm, embeddings, redis, qdrant),
    a cached `get_settings()` that tests can override, and an **`AI_ENABLED` feature flag** (kill switch).
  - **Concepts:** configuration as code, feature flags, dependency injection of config.
  - **Done when:** app runs with the new settings; tests override settings without real env vars.

- [x] **0.4 [BE] Fix confirmed backend bugs + regression tests**
  - **Goal:** fix B1 (type update crash), B2 (summary → SQL `SUM … GROUP BY type`), **B3 (category delete — decide:
    block if in use, or re-assign transactions to "Uncategorised"/NULL)**, B5 (category ownership on update),
    B6 (category type vs transaction type), B7 (pagination `limit/offset` + validated `sort_by`), B8 (don't leak
    SQL errors; log unhandled exceptions), B9 (UTC-aware JWT `exp`), B10, B11. Add a test for each.
  - **Concepts:** regression tests, aggregation in the database vs Python, safe error responses.
  - **Done when:** every bug in PROJECT_CONTEXT §12 table B1–B11 has a test that failed before and passes now.

- [x] **0.5 [FE] Fix frontend mismatches**
  - **Goal:** B4 summary keys, `amount` string→number handling, nullable `Category.user_id`, pagination support.
  - **Done when:** dashboard cards show correct totals.

- [x] **0.6 [BE] Unit of work (transaction boundaries)**
  - **Goal:** let a service run several writes in **one DB transaction** (repositories `flush()`, the service/UoW
    decides `commit()`/`rollback()`), without breaking existing endpoints. Discuss options (UoW class vs
    `commit=` flag vs session-per-request commit) and pick one.
  - **Concepts:** ACID, atomicity, unit-of-work pattern — needed for bulk imports and multi-step agent actions.
  - **Done when:** a test proves a failing 3rd insert rolls back the first two.

- [x] **0.7 [BE] Schema for the AI era**
  - **Goal:** Alembic migration adding `users.currency` (default `INR`), `users.timezone` (default
    `Asia/Kolkata`), `transactions.updated_at`, `transactions.source` (`manual|chat|import|schedule`),
    `transactions.import_batch_id` (nullable, FK added in Phase 8), indexes on `(user_id, date)` and
    `(user_id, category_id)`. Add `GET/PATCH /api/v1/users/me`.
  - **Concepts:** migrations in production (additive, backwards-compatible), provenance/auditability, indexes.
  - **Done when:** `alembic upgrade head` and `downgrade -1` both work; `/users/me` returns currency & timezone.

- [x] **0.8 [FE] Profile & preferences**
  - **Goal:** use `/users/me` instead of localStorage profile; settings screen for currency & timezone.

- [x] **0.9 [BE] Structured logging & request IDs**
  - **Goal:** **structlog** JSON logs; middleware that assigns/propagates `X-Request-ID`; `request_id` and `user_id`
    bound via `contextvars` so every log line in a request carries them.
  - **Concepts:** structured logging, correlation IDs, contextvars — the base of all AI debugging later.
  - **Done when:** one request's log lines can be filtered by its request id.

- [x] **0.10 [BE] Upgrade the AI stack**
  - **Goal:** replace the unused 0.3.x packages with LangChain 1.x / LangGraph 1.x, langchain-groq,
    langchain-qdrant, qdrant-client (versions in PROJECT_CONTEXT §11); drop what isn't needed; keep heavy deps
    (torch via sentence-transformers) out of the default CI install.
  - **Concepts:** semantic versioning, breaking changes, keeping CI fast.
  - **Done when:** `python -c "import langgraph, langchain_groq"` works; CI stays green and fast.

- [x] **0.11 [BE] Architecture Decision Record**
  - **Goal:** `docs/adr/0001-ai-assistant-architecture.md` — context, decision (PROJECT_CONTEXT §13), alternatives
    considered (raw text-to-SQL, pure RAG, hand-rolled loop, CrewAI…), consequences.
  - **Concepts:** ADRs / design docs — how senior engineers justify decisions (great interview material).

🎯 **Milestone 0:** clean repo, correct numbers, Redis running, logs you can trace.

---

## Phase 1 — Walking skeleton: streaming chat, no tools

*Why:* prove the full path (UI → API → LLM → stream → DB) end to end before adding intelligence.

- [ ] **1.1 [BE] LLM gateway (provider abstraction)**
  - **Goal:** `app/ai/llm/factory.py` returning a LangChain `BaseChatModel` from settings (`LLM_PROVIDER`,
    `LLM_MODEL`, keys, temperature, timeout, `max_retries`), with a fallback chain (`with_fallbacks`). Pick a
    Groq model that supports tool calling. Smoke script `python -m app.ai.llm.smoke`.
  - **Concepts:** ports & adapters, provider lock-in, timeouts/retries, temperature, tokens.
  - **Done when:** changing `LLM_PROVIDER`/`LLM_MODEL` in `.env` switches models with zero code changes.

- [ ] **1.2 [BE] Chat persistence models**
  - **Goal:** `conversations` (UUID id, user_id, title, timestamps, archived) and `messages` (id, conversation_id,
    role, content, tool_calls JSON, metadata JSON: model, tokens, latency, prompt_version) + repositories + service
    + migration.
  - **Concepts:** conversation data modelling, JSON columns, UUIDs vs integer IDs.

- [ ] **1.3 [BE] Conversation REST API**
  - **Goal:** `POST/GET /api/v1/chat/conversations`, `GET/PATCH/DELETE /chat/conversations/{id}`,
    `GET /chat/conversations/{id}/messages` (paginated). User-scoped, with tests incl. cross-user 404s.

- [ ] **1.4 [BE] Prompts as versioned files**
  - **Goal:** `app/ai/prompts/system_v1.md` + loader that fills variables (user name, today in user timezone,
    currency); prompt version recorded with each message.
  - **Concepts:** system prompts, prompt versioning, why prompts are code.

- [ ] **1.5 [BE] Minimal LangGraph graph**
  - **Goal:** `AgentState` (messages + user context), one `agent` node, compiled once at startup; conversation
    memory = last N messages loaded from the DB.
  - **Concepts:** state graphs, nodes/edges, reducers (`add_messages`), short-term memory.

- [ ] **1.6 [BE] SSE streaming chat endpoint**
  - **Goal:** `POST /api/v1/chat/conversations/{id}/messages` returns **Server-Sent Events**. Freeze the event
    contract now (FE depends on it): `message_start`, `token`, `tool_start`, `tool_end`, `clarification`,
    `confirm_required`, `error`, `message_end` (with `message_id`, usage). Persist user + assistant messages;
    auto-title new conversations with a cheap LLM call.
  - **Concepts:** SSE vs WebSockets vs polling, async generators, `graph.astream` stream modes, sync DB code
    inside async endpoints (thread pools).
  - **Done when:** `curl -N` shows tokens streaming; both messages are in the DB.

- [ ] **1.7 [BE] Redis intro: rate limiting the chat endpoint**
  - **Goal:** `app/core/redis.py` client; per-user limit (e.g. 20 messages/min) with an atomic Redis counter or
    sliding window; `429` + `Retry-After`.
  - **Concepts:** Redis data types, TTL, atomic ops/Lua, fixed vs sliding window, why LLM endpoints need limits.

- [ ] **1.8 [BE] Deterministic tests with a fake LLM**
  - **Goal:** inject a fake chat model (LangChain's fake models) via dependency override; test the SSE event
    sequence, persistence and auth — no network in tests.
  - **Concepts:** test doubles, determinism, why you never hit a real LLM in unit tests.

- [ ] **1.9 [FE] Chat panel**
  - **Goal:** chat drawer/page: conversation list, markdown messages, streaming via `fetch` + `ReadableStream`
    (so the Authorization header is sent), Stop button (AbortController), error/retry states.

🎯 **Milestone 1:** you chat with a model in your app and responses stream in; history persists.

---

## Phase 2 — Observability before complexity

*Why:* once the agent loops over tools, you can't debug it from logs alone. Real teams wire tracing in early.

- [ ] **2.1 [BE] Tracing backend**
  - **Goal:** choose and run a tracing tool. Options: **Langfuse** self-hosted (full-featured, but v3 needs
    Postgres + ClickHouse + Redis + S3/MinIO), **Langfuse Cloud** free tier (zero infra), or **Arize Phoenix**
    (one container, OpenTelemetry-native). Decide after the trade-off discussion.
  - **Concepts:** LLM observability, traces/spans, OpenTelemetry.

- [ ] **2.2 [BE] Trace every chat turn**
  - **Goal:** callback/instrumentation on graph runs with `user_id`, `session_id = conversation_id`, prompt version,
    tags; put the trace id in logs next to `request_id`.
  - **Done when:** one chat turn shows as one trace with LLM spans, tokens and latency.

- [ ] **2.3 [BE] Usage & cost accounting**
  - **Goal:** record tokens per message, a per-model price table in config (0 for free tier, but keep the
    mechanism), `GET /api/v1/chat/usage` (per-user daily totals).
  - **Concepts:** unit economics of LLM features, per-tenant cost tracking.

🎯 **Milestone 2:** for any answer, you can see exactly what the model saw and did.

---

## Phase 3 — Read tools & the agent loop (Option A)

- [ ] **3.1 [BE] Tool framework & ToolContext**
  - **Goal:** `ToolContext` (user_id, timezone, currency, request_id, DB session factory) injected at runtime via
    LangGraph config/runtime context — **never an argument the LLM fills**. Tool metadata: name, description,
    args schema, **risk level** (`read | write | destructive`). A registry that builds the tool list per user.
  - **Concepts:** tool/function calling, JSON schemas, injected args, least privilege.

- [ ] **3.2 [BE] Tool gateway**
  - **Goal:** a wrapper every tool runs through: validate args (Pydantic) → policy check → timeout → run →
    cap/truncate large results → on error return a **structured, fixable error** (what was wrong + valid options)
    → structured audit log line.
  - **Concepts:** gateway/middleware pattern, error recovery for agents (Rovo's "discovery probes").

- [ ] **3.3 [BE] Category tools & entity resolution**
  - **Goal:** `list_categories`, `resolve_category(text)` using fuzzy matching (rapidfuzz) + synonyms, returning
    ranked candidates so the model can ask when ambiguous ("food" → Food / Groceries?).
  - **Concepts:** entity linking/resolution.

- [ ] **3.4 [BE] Query spec — your "JQL"**
  - **Goal:** `app/ai/query/spec.py`: `QuerySpec` with filters (absolute dates or presets like `this_month`,
    `last_month`, `last_n_days`, resolved in the **user's timezone**), types, category ids, amount range, description
    contains; `group_by` (category, month, week, weekday, type, description); metrics (sum, count, avg, min, max);
    sort; `limit ≤ 200`. `compiler.py` turns it into a SQLAlchemy query and **always** adds `user_id`.
  - **Concepts:** DSLs, safe query construction, why not raw text-to-SQL, property-based testing.
  - **Done when:** unit tests cover every filter/group/metric, plus a property test (hypothesis) that *every*
    compiled query contains the user filter.

- [ ] **3.5 [BE] `query_transactions` & `get_transaction_details` tools**
  - **Goal:** rows mode vs aggregate mode; compact result format (rows + totals + "N more not shown").
  - **Concepts:** designing tool outputs for LLMs (token-efficient, unambiguous).

- [ ] **3.6 [BE] The agent loop**
  - **Goal:** `agent ⇄ tools` graph with a conditional edge (tool calls? → tools, else → end), parallel tool calls,
    `recursion_limit` as the step cap.
  - **Concepts:** ReAct loop, stopping conditions, why Rovo moved from a pre-planned DAG to a hybrid loop.

- [ ] **3.7 [BE] Context builder node**
  - **Goal:** assemble the system prompt each turn: today + timezone, currency, compact category list, tool-use
    rules (always use tools for numbers, never guess), summary placeholder for Phase 5.
  - **Concepts:** context engineering, grounding.

- [ ] **3.8 [BE] Stream tool activity**
  - **Goal:** emit `tool_start`/`tool_end` SSE events with human labels ("Looking up Food spending in Sept…").

- [ ] **3.9 [BE] Clarifying questions**
  - **Goal:** prompt rules + an `ask_user` tool that ends the turn and emits a `clarification` event with options.
  - **Concepts:** when agents should ask vs assume; disambiguation.

- [ ] **3.10 [FE] Tool chips, quick-reply buttons, tables in messages**

- [ ] **3.11 [BE] Eval harness v1**
  - **Goal:** `scripts/seed_demo_data.py` (deterministic demo user, ~6 months of realistic INR data);
    `evals/datasets/read_questions.jsonl` (20 questions, expected values computed from the DB); a runner marked
    `@pytest.mark.eval` (excluded from normal CI) that reports accuracy; compare two Groq models.
  - **Concepts:** golden datasets, eval-driven development, why evals come early.

🎯 **Milestone 3:** "How much did I spend on food last month vs the month before, by week?" → correct answer.

---

## Phase 4 — Actions with a human in the loop

- [ ] **4.1 [BE] Checkpointer**
  - **Goal:** `langgraph-checkpoint-postgres` (uses psycopg 3 — explain why it sits alongside psycopg2),
    `thread_id = conversation_id`. Decide what's the source of truth: `messages` table for UI history, checkpoint
    for agent state.
  - **Concepts:** durable execution, checkpoints, resumability.

- [ ] **4.2 [BE] Policy engine**
  - **Goal:** config mapping risk → `auto | confirm | deny`, per-tool overrides, and a `headless` profile (for
    schedules) that denies writes.
  - **Concepts:** policy as config, least privilege, separation of mechanism and policy.

- [ ] **4.3 [BE] Write tools**
  - **Goal:** `create_transactions` (batch), `update_transaction`, `delete_transactions` (by ids only — the agent must
    look them up first), `create/rename/delete_category` (respecting the B3 decision). All call services, all
    return a before/after diff.

- [ ] **4.4 [BE] Confirmation with `interrupt()`**
  - **Goal:** confirm-required tools pause the graph and emit `confirm_required` {action_id, summary, preview rows,
    risk}; `POST /api/v1/chat/conversations/{id}/resume` {action_id, decision: approve|reject|edit, edits?} resumes
    the graph.
  - **Concepts:** human-in-the-loop, interrupts, resuming from checkpoints.

- [ ] **4.5 [BE] Idempotency**
  - **Goal:** `action_id` + Redis `SET NX` lock / DB unique key so a double-click or retry can't apply twice.
  - **Concepts:** idempotency keys, at-least-once vs exactly-once.

- [ ] **4.6 [BE] Audit log & undo**
  - **Goal:** `agent_actions` table (user, conversation, tool, args, before/after, status, approved) +
    `GET /chat/actions`; undo for the last create/update/delete using the stored before-image.
  - **Concepts:** audit trails, compensating actions.

- [ ] **4.7 [FE] Confirm cards (approve / reject / edit), action history, undo**

- [ ] **4.8 [BE] Action evals**
  - **Goal:** 15 write requests; in dry-run mode, check the agent chose the right tool and arguments.
  - **Concepts:** trajectory evaluation.

🎯 **Milestone 4:** "Move all my Uber transactions from last week to Transportation" → preview → approve → done → undo works.

---

## Phase 5 — Memory, context engineering & skills

- [ ] **5.1 [BE] Token budgeting** — count tokens, trim history, budget per context section.
- [ ] **5.2 [BE] Conversation summarisation** — summarise older turns into state past a threshold.
  - **Concepts:** context windows, lossy compression of history.
- [ ] **5.3 [BE] Long-term memory**
  - **Goal:** LangGraph Store (Postgres-backed) namespaced by user; `remember_fact`/`forget_fact` tools; inject
    relevant memories; merchant→category rules ("Swiggy = Food") reused later for auto-categorisation;
    `GET/DELETE /api/v1/memories`.
  - **Concepts:** short- vs long-term memory, semantic vs episodic memory, user control over memory.
- [ ] **5.4 [BE] Skills (progressive disclosure)**
  - **Goal:** `backend/skills/<name>/SKILL.md` with front-matter (name, description); loader puts only the index in
    the prompt; `load_skill` tool pulls the full text. First skills: `bulk-edit`, `monthly-review`.
  - **Concepts:** progressive disclosure, keeping prompts small, behaviour as content not code.
- [ ] **5.5 [BE] Prompt management** — version bump workflow, prompt version in traces, optional managed prompts.
- [ ] **5.6 [FE] Memory settings page**

🎯 **Milestone 5:** the assistant remembers your rules across conversations and follows skill playbooks.

---

## Phase 6 — Background jobs & storage infrastructure

- [ ] **6.1 [BE] Celery**
  - **Goal:** `app/workers/celery_app.py` with Redis as broker/result backend; task conventions (idempotent,
    `acks_late`, retries with backoff, time limits); Windows `--pool=solo`; optional Flower for monitoring.
  - **Concepts:** message queues, workers, at-least-once delivery, retries, visibility timeouts.
- [ ] **6.2 [BE] Jobs table & API** — status, progress %, result reference, error; `GET /api/v1/jobs/{id}`.
- [ ] **6.3 [BE] Real-time events** — Redis pub/sub per user → `GET /api/v1/events/stream` (SSE).
  - **Concepts:** pub/sub vs streams vs queues.
- [ ] **6.4 [BE] Object storage** — MinIO in compose; `FileStorage` interface (local + S3 via boto3); presigned URLs.
  - **Concepts:** blob storage, presigned URLs, why files don't go in Postgres.
- [ ] **6.5 [FE] Events hook + job progress toasts**

🎯 **Milestone 6:** a dummy long task runs in a worker and its progress appears live in the UI.

---

## Phase 7 — Analysis sandbox (Option C, "code mode")

- [ ] **7.1 [BE] Sandbox image** — `sandbox/Dockerfile`: slim Python + pandas, numpy, matplotlib; non-root user.
- [ ] **7.2 [BE] `SandboxRunner`**
  - **Goal:** interface + Docker implementation (docker SDK): no network, memory/CPU/PID limits, read-only root,
    tmpfs, wall-clock timeout + kill, per-run working dir, always cleaned up. Stub for a hosted sandbox (E2B/Modal).
  - **Concepts:** isolation, defence in depth, resource limits, why `exec()` is never safe.
- [ ] **7.3 [BE] Data handoff & harness** — export only this user's transactions (with category names) to a file in
  the run dir; in-sandbox harness loads `df`, runs the code, captures stdout, a `result` object and saved charts.
- [ ] **7.4 [BE] `run_analysis` tool + `analysis` skill**
  - **Goal:** rich error feedback (trimmed traceback + schema hint) with a retry cap; short runs inline, long runs
    as Celery jobs (choose the path per request, like Rovo).
  - **Concepts:** programmatic tool calling / code mode, self-correction loops.
- [ ] **7.5 [BE] Artifacts** — charts to object storage, message attachments.
- [ ] **7.6 [BE] Sandbox security tests** — network blocked, host files unreadable, fork bomb and infinite loop
  contained, huge output truncated.
- [ ] **7.7 [FE] Render charts and result tables in chat**
- [ ] **7.8 [BE] Analysis evals** — 10 questions with numeric checks.

🎯 **Milestone 7:** "Find unusual spending this year and chart it" → correct chart + explanation.

---

## Phase 8 — Documents: ingestion, import & RAG

- [ ] **8.1 [BE] Upload API**
  - **Goal:** `POST /api/v1/files` (multipart), size limit, content sniffing (not just extension), filename
    sanitisation, object storage, `files` table (sha256, mime, size, status, error); duplicate detection; list/delete.
  - **Concepts:** secure file upload, content hashing.
- [ ] **8.2 [BE] Ingestion pipeline**
  - **Goal:** Celery chain detect → parse → extract → categorise → stage → index with progress events; parser
    registry: CSV/XLSX (pandas, header detection), digital PDF (Docling), scanned PDF/images (OCR).
  - **Concepts:** pipelines, strategy pattern, OCR.
- [ ] **8.3 [BE] Statement extraction**
  - **Goal:** LLM structured output into `StatementExtraction` for PDFs (page by page); for spreadsheets, the LLM
    maps columns once and the rest is deterministic parsing; balance reconciliation check when balances exist.
  - **Concepts:** structured output, schema-constrained generation, hybrid LLM + deterministic pipelines.
- [ ] **8.4 [BE] Normalise, dedupe, auto-categorise**
  - **Goal:** fingerprint dedup (date + amount + normalised description) within the file and against existing data;
    categorisation cascade: memory rules → similarity to past labelled descriptions → LLM batch classify, with
    confidence.
  - **Concepts:** entity normalisation, cascades (cheap → expensive), confidence thresholds.
- [ ] **8.5 [BE] Staged imports**
  - **Goal:** `import_batches` + `staged_transactions`; tools `preview_import`, `update_staged_rows`, `commit_import`
    (interrupt with preview → one DB transaction via UoW → `source='import'`); undo a whole import.
- [ ] **8.6 [BE] Embeddings & vector store**
  - **Goal:** `Embeddings` adapter (local sentence-transformers) + Qdrant adapter with payload indexes on
    `user_id`/`file_id`; chunking by page/section with overlap and metadata.
  - **Concepts:** embeddings, chunking strategies, vector indexes (HNSW), metadata filtering for multi-tenancy.
- [ ] **8.7 [BE] Retrieval & `search_documents`**
  - **Goal:** hybrid search (dense + sparse/BM25), mandatory user filter, reranking (cross-encoder), query rewriting
    from the conversation; answers cite file + page.
  - **Concepts:** RAG, hybrid search, reranking, citations, why naive RAG fails (Rovo's lesson).
- [ ] **8.8 [BE] Indirect prompt-injection defences**
  - **Goal:** delimit/"spotlight" document content, instruction hierarchy in the system prompt, documents can never
    grant permissions; tests with a statement containing malicious instructions.
- [ ] **8.9 [FE] Uploads in chat, file status, editable import preview, citations**
- [ ] **8.10 [BE] Document evals** — extraction precision/recall on 3–5 sample statements (CSV, XLSX, digital PDF,
  scanned); RAG faithfulness/context precision (DeepEval).

🎯 **Milestone 8:** upload any bank statement → "add these" → preview with categories → approve → imported, no duplicates.

---

## Phase 9 — Exports

- [ ] **9.1 [BE] Export service** — renderer per format (CSV, XLSX with formatting + summary sheet, PDF); selection
  via `QuerySpec`.
- [ ] **9.2 [BE] `export_transactions` tool** — small inline, large via Celery; stored in object storage;
  expiring presigned download link as a message attachment.
- [ ] **9.3 [FE] Download cards**

🎯 **Milestone 9:** "Give me all 2026 food expenses as Excel" → download link.

---

## Phase 10 — Schedules & the proactive agent

- [ ] **10.1 [BE] Schedules** — `schedules` table (cron, timezone, task prompt, allowed tools, enabled, last/next run,
  status); dynamic entries in **RedBeat**; run Celery Beat.
- [ ] **10.2 [BE] Schedule tools** — natural language → cron (LLM) → validated with croniter → human-readable
  preview → confirm; list/pause/resume/delete.
- [ ] **10.3 [BE] Headless agent runner** — same graph, headless policy (read/analyse/notify only, no clarifications),
  step & token budget, output to a "Scheduled reports" conversation.
  - **Concepts:** background agents, autonomy levels, blast radius.
- [ ] **10.4 [BE] Notifications** — table + API + SSE event; email through SMTP to **Mailpit** in compose.
- [ ] **10.5 [FE] Schedules page + notification bell**

🎯 **Milestone 10:** "Every 1st at 9am send me last month's summary" → it arrives.

---

## Phase 11 — Guardrails, security & resilience

- [ ] **11.1 [BE] Input guardrails** — length limits, prompt-injection/jailbreak detection (guard model if your
  provider offers one, else a small-model judge), scope check; layered, cheap first.
- [ ] **11.2 [BE] Output guardrails** — verify every id/amount in the answer belongs to the user; redact account
  numbers in logs/traces; sanitise markdown (XSS).
- [ ] **11.3 [BE] Quotas** — per-user daily token budget (Redis), max tool calls per turn, upload limits.
- [ ] **11.4 [BE] Cancellation** — stop flag in Redis checked between nodes; handle client disconnects.
- [ ] **11.5 [BE] Resilience** — retries with jitter, provider fallback chain, per-layer timeouts, circuit breaker,
  graceful degradation messages.
- [ ] **11.6 [BE] Security review** — threat model + checklist against the **OWASP Top 10 for LLM Applications**;
  red-team eval set.

🎯 **Milestone 11:** a documented threat model and red-team tests that pass.

---

## Phase 12 — Evals & the quality flywheel

- [ ] **12.1 [BE] Datasets** — consolidate into versioned datasets: read Q&A, actions, clarification, analysis,
  documents, safety.
- [ ] **12.2 [BE] Evaluators** — exact numeric, tool-trajectory match, LLM-as-judge rubric (calibrated against ~20 of
  your own labels), RAG metrics.
- [ ] **12.3 [BE] CI** — fast deterministic tests on every push; eval suite as a manual/nightly GitHub Actions
  workflow with an API-key secret and a regression threshold.
- [ ] **12.4 [BE+FE] Feedback loop** — thumbs up/down + comment → scores; triage bad conversations into the
  dataset (Rovo's "self-evolution" loop, human-approved).
- [ ] **12.5 [BE] Model comparison & routing** — accuracy/latency/cost table across 2–3 free models; small model for
  titles/classification, strong model for the agent.

🎯 **Milestone 12:** one command produces a quality report; prompt/model changes are gated by it.

---

## Phase 13 — Advanced (optional, great for interviews)

- [ ] **13.1 [BE] Guarded text-to-SQL (Option B)** — per-user views or Postgres **RLS** (`SET LOCAL app.user_id`),
  read-only DB role, **sqlglot** AST allowlist (SELECT only, whitelisted views), `statement_timeout`, forced
  `LIMIT`; used only when `QuerySpec` can't express the question; eval A vs B.
- [ ] **13.2 [BE] Subagents** — importer and analyst as LangGraph subgraphs behind a supervisor; compare with the
  single agent on evals.
- [ ] **13.3 [BE] Fast intent router** — small model or classifier for simple intents (Rovo's fast path).
- [ ] **13.4 [BE] MCP server** — expose your tools via MCP with auth; use them from Claude Desktop.
- [ ] **13.5 [BE] Containerise everything** — Dockerfiles for API/worker/beat, compose "full" profile, migrations on
  start, healthchecks.
- [ ] **13.6 [BE] Async DB on the chat path** — async SQLAlchemy; measure before/after with Locust.

---

## Concept → step index (interview prep)

| Concept | Steps |
|---|---|
| LLM basics (tokens, temperature, system prompts) | 1.1, 1.4 |
| Provider abstraction / ports & adapters | 1.1, 6.4, 7.2, 8.6 |
| Streaming (SSE) | 1.6, 1.9, 6.3 |
| Tool calling & tool design | 3.1, 3.2, 3.5 |
| Agent loop (ReAct) & orchestration | 1.5, 3.6, 13.2 |
| Entity resolution | 3.3 |
| Query DSL vs text-to-SQL | 3.4, 13.1 |
| Context engineering | 3.7, 5.1, 5.2 |
| Clarification | 3.9 |
| Human-in-the-loop / interrupts / checkpointing | 4.1, 4.4 |
| Idempotency, audit, undo | 4.5, 4.6 |
| Memory (short/long-term) | 1.5, 5.2, 5.3 |
| Skills / progressive disclosure | 5.4 |
| Redis (rate limits, locks, pub/sub, broker) | 1.7, 4.5, 6.1, 6.3, 11.3 |
| Job queues & scheduling | 6.1, 6.2, 10.1 |
| Sandboxing / code mode | 7.2–7.6 |
| Document AI (parsing, OCR, structured extraction) | 8.2–8.4 |
| RAG (embeddings, chunking, hybrid search, reranking) | 8.6, 8.7 |
| Prompt injection (direct & indirect) | 8.8, 11.1 |
| Guardrails & multi-tenancy | 3.1, 3.4, 11.1, 11.2, 13.1 |
| Observability & cost | 0.9, 2.1–2.3 |
| Evals (golden sets, LLM-as-judge, trajectory, RAG) | 3.11, 4.8, 7.8, 8.10, 12.x |
| Resilience (retries, fallbacks, circuit breakers) | 1.1, 11.5 |
| Professional practice (ADRs, migrations, CI, UoW) | 0.1–0.11, 12.3 |
