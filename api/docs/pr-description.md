# Production-harden API: auth, rate limiting, middleware, tests

## Summary

Comprehensive production readiness hardening of the FastAPI backend. This PR takes the API from a working prototype to a deployable service with proper security, error handling, observability, and test coverage.

### Security & Auth
- **API key authentication** (`X-Trace-Key` header) with SHA-256 hashing — keys are never stored in plaintext
- **Auth failure rate limiting** — 10 failures per 60s per IP, returns 429
- **Per-org request rate limiting** — 10K requests per 60s per org, sliding window
- **X-Forwarded-For trust** gated behind `TRUST_PROXY_HEADERS=true` (off by default)
- **Request body size limit** — 10MB max via ASGI middleware, returns 413
- **CORS** configured with `X-Trace-Key`, `Content-Type`, `Accept` headers

### API Endpoints
- `POST /ingest/batch` — batch span ingestion (up to 1000 spans) with savepoint-per-trace-group isolation
- `GET /traces` — cursor-based keyset pagination with filter support (function_name, environment, status)
- `GET /traces/{trace_id}` — trace detail with nested spans
- `GET /spans/{span_id}` — single span detail
- `POST /api-keys` — create new API key (returns raw key once)
- `GET /api-keys` — list org keys (hashes only)
- `DELETE /api-keys/{key_id}` — soft-revoke with 409 on re-revoke
- `GET /health` — liveness probe (no DB)
- `GET /health/ready` — readiness probe (DB connectivity check)

### Data Layer
- **Postgres-only** — removed all SQLite fallback code and `aiosqlite` dependency
- **Upsert traces** via `ON CONFLICT DO UPDATE` — widens time window, accumulates tokens, escalates status
- **Bulk insert spans** via `ON CONFLICT DO NOTHING` — idempotent re-ingestion
- **Auto-commit/rollback session lifecycle** in `get_db()` dependency
- **Alembic migration 003** — adds `output` JSON column to spans table

### Observability
- **Request ID correlation** — `X-Request-ID` header (auto-generated UUID or client passthrough) propagated via `ContextVar` into all log lines
- **Structured JSON logging** in production, plain text in debug mode
- **Consistent error responses** — all errors return `{"error": "..."}` format
- **Global 500 handler** — catches unhandled exceptions, logs traceback in debug mode only
- **422 validation handler** — normalizes Pydantic errors to match app error shape
- **Graceful shutdown** — lifespan handler disposes DB engine on exit

### Code Quality
- **Status constants** (`STATUS_OK`, `STATUS_ERROR`) replace magic strings across models, DAL, services, schemas
- **Custom exception hierarchy** — `TraceAppError` base with `AuthenticationError`, `NotFoundError`, `ConflictError`, `RateLimitError`, `InvalidCursorError`
- **Pydantic field validators** for byte-budget enforcement on `inputs` (512KB), `output` (512KB), `tags` (64KB)
- **Seed script** uses `secrets.token_hex()` instead of hardcoded key, uses project logger instead of `print()`

### Tests (58 tests, 0 lint errors)
- Auth: unauthenticated requests return 401, revoked keys rejected
- Ingestion: happy path, duplicate spans idempotent, status escalation, token accumulation, batch validation
- Traces: list pagination, cursor mechanics, filters, cross-org isolation
- API keys: create, list, revoke, re-revoke returns 409, cross-org isolation
- Rate limiting: auth failure limiter, per-org limiter, independence across orgs
- Health: liveness, readiness, request ID generation and passthrough
- All tests run against real Postgres (`trace_test` database)

### New Files

| File | Purpose |
|------|---------|
| `src/api/constants.py` | `STATUS_OK` / `STATUS_ERROR` constants |
| `src/api/rate_limit.py` | Auth failure + per-org rate limiters |
| `src/api/request_id.py` | Request ID middleware + ContextVar |
| `src/api/exceptions.py` | Custom exception hierarchy |
| `src/api/dal/api_keys.py` | API key DAL (create, list, revoke, lookup) |
| `src/api/routes/api_keys.py` | API key route handlers |
| `src/api/schemas/api_keys.py` | API key request/response schemas |
| `api/.env.example` | Environment variable template |
| `api/.gitignore` | Python/DB artifact exclusions |
| `api/DECISIONS.md` | Architecture decision log (9 decisions) |
| `api/docs/architecture.md` | 10 Mermaid architecture diagrams |
| `migrations/versions/003_add_span_output.py` | Adds `output` column to spans |

## Test plan
- [x] `make check` passes — 58 API tests + 63 SDK tests, zero ruff errors
- [ ] Manual: `GET /health` returns 200 without DB connection
- [ ] Manual: `GET /health/ready` returns 200 with DB, 503 without
- [ ] Manual: POST with >10MB body returns 413
- [ ] Manual: Re-revoke an API key returns 409
- [ ] Manual: Verify `X-Request-ID` header in responses
- [ ] Manual: Verify JSON log format in production mode (`LOG_LEVEL=INFO`)

---

**38 files changed**, **+2,175 / -182 lines**
