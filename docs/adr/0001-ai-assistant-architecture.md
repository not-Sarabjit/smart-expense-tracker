# ADR 0001 — Architecture of the AI assistant

- **Status:** Accepted
- **Date:** 2026-10-03
- **Deciders:** project owner
- **Related:** `PROJECT_CONTEXT.md` §13 (decisions), `AI_TRACKER.md` (delivery plan)

## Context

Smart Expense Tracker is a FastAPI + PostgreSQL app (sync SQLAlchemy, layered
`router → service → repository → model`, JWT auth, per-user data). We are adding a
conversational assistant, in the style of Atlassian Rovo, that must be able to:

1. **Act on data** — create, edit, re-categorise and delete transactions and categories
   from natural language ("move last week's Uber rides to Transportation").
2. **Answer open-ended questions** over the user's own data ("food spend by week, last
   month vs the month before"), asking for clarification when a request is ambiguous.
3. **Do deeper analysis** (anomalies, trends, charts) that doesn't fit a fixed query shape.
4. **Ingest documents** (bank statements as CSV/XLSX/PDF/images) and import them safely.
5. **Export** results and **run on a schedule** ("every 1st at 9am send me last month's summary").

Forces and constraints:

- **Correctness over fluency.** A finance app that confidently states wrong totals or
  silently changes data is worse than no assistant. Numbers must come from the database,
  not from the model.
- **Multi-tenancy.** Every query and write must be scoped to the authenticated user. The
  model must never be able to choose whose data it sees.
- **Writes are dangerous.** Bulk edits and deletes need previews, explicit confirmation,
  an audit trail and undo.
- **Cost.** Free-tier models first (Groq), so the design can't assume a frontier model;
  switching providers must be a config change.
- **Runs locally**, but should be built the way production systems are (queues, sandbox,
  object storage, tracing) — it is also a learning and portfolio project.
- **Existing code:** services already hold the business rules (ownership checks, category
  validation, a unit of work since Step 0.6); the assistant should reuse them, not bypass them.

## Decision

Build a **tool-using agent** orchestrated with **LangGraph**, behind a **tool gateway**,
with data access split by risk: **"A + C now, B later"**.

```
Chat API (SSE) ─► LangGraph agent loop ─► tool gateway ─► tools ─► services ─► DB
                  input guardrails          validate · user-scope · policy · audit · errors
                  context builder            ├─ A: query_transactions (QuerySpec → SQLAlchemy)
                  LLM ⇄ tools (ReAct loop)   ├─ write tools ── interrupt() → user confirms
                  output guardrails          ├─ C: run_analysis → Docker sandbox (pandas)
                                             └─ documents · export · schedules · memory · skills
```

1. **Orchestration — LangGraph 1.x.** A state graph runs an agent ⇄ tools loop with a step
   cap (`recursion_limit`). We use its checkpointer (Postgres) for durable conversation
   state, `interrupt()` for human-in-the-loop confirmation, and streaming for SSE.
   LangChain 1.x provides the chat-model, embedding and vector-store abstractions.
2. **Model access — provider-agnostic gateway.** A factory builds a `BaseChatModel` from
   settings (`LLM_PROVIDER`, `LLM_MODEL`, timeouts, retries) with a fallback chain. Groq
   free models (with tool calling) first; Claude/OpenAI/etc. by config only.
3. **Tool gateway.** Every tool call passes through one wrapper: Pydantic argument
   validation → policy (risk level `read | write | destructive` → `auto | confirm | deny`)
   → timeout → execution → result truncation → structured, *fixable* error messages →
   audit log. `user_id`, timezone and currency are **injected from the authenticated
   request context**, never filled in by the model.
4. **Reads (Option A) — a query DSL, not SQL.** The model fills a validated JSON
   `QuerySpec` (filters, relative date presets resolved in the user's timezone, group-by,
   metrics, sort, `limit ≤ 200`); our compiler turns it into SQLAlchemy and **always**
   adds `user_id`. This is the Rovo/JQL pattern: the model chooses *what* to ask, our code
   decides *how* it runs.
5. **Deep analysis (Option C) — code mode in a sandbox.** For questions the DSL can't
   express, the model writes pandas code that runs in a locked-down Docker container
   (no network, CPU/memory/PID limits, read-only root, timeout) over an export of **only
   that user's** rows. Errors are fed back for a bounded number of retries.
6. **Writes — typed tools only.** Writes call the existing services (business rules,
   unit of work), are previewed and confirmed via `interrupt()`, are idempotent
   (`action_id`), are recorded with before/after images in an audit table, and can be
   undone. Generated SQL is never used for writes.
7. **Guarded text-to-SQL (Option B) — deferred.** Possible later, only for questions A can't
   express, behind a read-only role, Postgres RLS, a sqlglot AST allow-list, a statement
   timeout and a forced `LIMIT`; evaluated against A before adoption.
8. **Supporting infrastructure.** Redis (rate limits, locks, pub/sub, Celery broker),
   Celery + RedBeat (ingestion, long analysis, exports, schedules), Qdrant + local
   sentence-transformers (document RAG with mandatory user filter), MinIO (uploads,
   exports, charts), Langfuse (traces, cost), structlog JSON logs with request ids (Step 0.9).
9. **Behaviour as content.** Versioned prompt files and progressive-disclosure *skills*
   (`SKILL.md` + a `load_skill` tool) so playbooks change without code changes.
10. **Quality gates.** Deterministic tests with a fake LLM in CI; golden-dataset evals
    (read accuracy, tool trajectories, analysis, documents, safety) run on demand/nightly
    and gate prompt or model changes.

## Alternatives considered

| Alternative | Why not (now) |
|---|---|
| **Raw text-to-SQL** — the model writes SQL against the real schema | Biggest blast radius: one prompt injection or hallucinated `JOIN` can read other users' rows or write data. Tenant isolation would rest on the model. Weak models produce subtly wrong SQL that still runs. Kept only as the guarded, read-only Option B for later. |
| **Pure RAG** — embed transactions/statements and let the model answer from retrieved chunks | Retrieval returns *similar* rows, not *all* matching rows, so sums, counts and comparisons are wrong in exactly the way that matters for finance. No path to writes. RAG is kept for what it is good at: unstructured documents (statements, receipts) with citations. |
| **Hand-rolled agent loop** (a `while` loop over the provider SDK's tool-calling) | Simple to start, but we'd rebuild durable state/checkpointing, resumable human-in-the-loop interrupts, streaming of intermediate events, parallel tool calls and step limits — exactly what LangGraph provides and what Rovo-style UX needs. The loop itself stays small and explicit in LangGraph, so we keep control. |
| **CrewAI / AutoGen-style multi-agent frameworks** | Optimised for role-playing agent teams; less control over state, interrupts and tool execution, harder to make deterministic and to test. A single agent with good tools is the right starting point; subgraphs (supervisor + importer/analyst) remain possible later in LangGraph (tracker 13.2) if evals justify them. |
| **Managed assistants (provider-hosted agents/threads)** | Couples state, tools and billing to one provider, conflicts with "free models first / swap by config", and moves user financial data and conversation state into a third-party runtime. |
| **Fixed intent classifier + hard-coded handlers** | Predictable, but can't handle the long tail of questions or multi-step requests; becomes a large if/else tree. May reappear as a *fast path* in front of the agent for trivial intents (tracker 13.3). |
| **Executing model-written code in-process (`exec`)** | Not isolatable — a model (or an injected document) could read secrets, the filesystem or other users' data. Code only ever runs in the sandbox. |

## Consequences

**Positive**

- Tenant isolation is enforced by our code (forced `user_id` in the compiler, injected tool
  context, sandbox data handoff), not by prompts.
- Numbers come from SQL or pandas, so answers are reproducible and testable; evals can
  check exact values.
- Writes reuse the existing services and unit of work, so business rules (category
  ownership/type checks, block-delete-when-in-use) apply to the agent automatically.
- Human-in-the-loop, idempotency, audit and undo make bulk actions safe enough to ship.
- Provider-agnostic model access keeps cost low and allows routing (small model for titles,
  stronger model for the agent).

**Negative / costs**

- More moving parts locally: Redis, Qdrant, MinIO, Celery workers, a sandbox image,
  Langfuse. Mitigated with docker-compose and health checks.
- The `QuerySpec` DSL must grow with user questions; gaps surface as "can't answer" until
  extended (Option C covers some, Option B may cover more later).
- Sandbox runs add latency (container start) and need their own security tests.
- LangGraph/LangChain are fast-moving; pinned versions and the provider abstraction limit
  churn, and an upgrade is a tracked step (0.10 established the 1.x baseline).
- The sync SQLAlchemy stack means DB work on the chat path runs in a thread pool; an async
  path is a later, measured optimisation (tracker 13.6).

**Follow-ups**

- Revisit Option B after the Phase 3 eval harness shows which questions A misses.
- Revisit multi-agent subgraphs only if single-agent evals plateau.
- Record further significant decisions (tracing backend in 2.1, checkpointer vs `messages`
  table as source of truth in 4.1) as ADR 0002+.
- Rate limiting is hand-rolled (sliding-window log on Redis, `app/core/rate_limit.py`) to keep
  the ZSET/Lua mechanics visible and reusable for idempotency locks (4.5) and token quotas
  (11.3). If it grows beyond per-user request counts, swap in the `limits` library — the
  change is confined to `SlidingWindowRateLimiter`, since callers only see `RateLimitDecision`.
