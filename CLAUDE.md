# CLAUDE.md — Trace

## Project Overview

Trace is a real-time causal debugger for LLM applications. It answers the production question: **"Why did the LLM say that?"** by providing decorator-based tracing and visual attribution maps.

**Tech Stack:**
- Backend: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy (async)
- Frontend: React 18, TypeScript, Tailwind CSS, D3.js (for attribution visualizations)
- Database: SQLite (local/dev), PostgreSQL (cloud/prod)
- Testing: pytest, pytest-asyncio
- Linting/Formatting: ruff
- Package Management: uv (preferred) or pip

---

## Directory Structure

Monorepo with three independently deployable packages:

```
trace/
├── CLAUDE.md
├── pyproject.toml            ← uv workspace root
├── Makefile                  ← Orchestrates all packages
├── sdk/                      ← Python SDK — published to PyPI as "usetrace"
│   ├── pyproject.toml        ← Minimal deps: pydantic, httpx
│   ├── src/usetrace/
│   │   ├── decorators/       ← @trace, @monitor, etc.
│   │   ├── capture/          ← Input/output capture logic
│   │   ├── transport/        ← Sending trace data to backend
│   │   └── models/           ← Pydantic models for trace payloads
│   └── tests/
├── api/                      ← FastAPI backend — deployed as Docker container
│   ├── pyproject.toml        ← Depends on usetrace + FastAPI, SQLAlchemy, etc.
│   ├── .env.example
│   ├── src/api/
│   │   ├── routes/           ← API endpoints (one file per resource)
│   │   ├── schemas/          ← Request/response Pydantic schemas
│   │   ├── services/         ← Business logic layer
│   │   ├── dal/              ← Data access layer (DB queries)
│   │   └── deps.py           ← FastAPI dependencies (auth, DB session)
│   └── tests/
├── frontend/                 ← React dashboard — deployed to Vercel or Nginx
│   ├── package.json
│   └── src/
│       ├── components/       ← Reusable UI components
│       ├── pages/            ← Route-level page components
│       ├── hooks/            ← Custom React hooks
│       ├── api/              ← API client functions
│       └── utils/            ← Helpers and formatters
└── docs/                     ← Specs and design documents
```

---

## Critical Rules (Read These First)

1. **Never modify `pyproject.toml`, `.env`, or config files without explicit permission.**
2. **Never install new dependencies without asking first.** Suggest the dependency and wait for approval.
3. **Never create new top-level directories.** Work within the existing structure.
4. **Always run `make check` (ruff + pytest) before considering any task complete.**
5. **When unsure between two approaches, stop and ask. Do not guess.**
6. **Never use `print()`.** Use the project logger: `from api.logger import logger`.

---

## Code Conventions

### Python (Backend + SDK)

- **Type hints on everything.** All function signatures, return types, and variables where non-obvious.
- **Pydantic v2 models** for all data structures. No raw dicts for structured data.
- **Async-first** in the API layer. Use `async def` for all route handlers and service methods.
- **Docstrings** on all public functions and classes (Google-style).
- **Snake_case** for functions, variables, files. **PascalCase** for classes.
- **No star imports.** Always import explicitly.
- **Keep functions short.** If a function exceeds ~40 lines, break it up.
- **Error handling:** Raise custom exceptions from `api/src/api/exceptions.py`. Never catch bare `Exception` unless re-raising.

```python
# Good
async def get_trace_by_id(trace_id: str) -> TraceRecord:
    """Fetch a single trace record by ID."""
    record = await dal.traces.get(trace_id)
    if not record:
        raise TraceNotFoundError(trace_id)
    return record

# Bad
def get_trace_by_id(trace_id):
    try:
        record = dal.traces.get(trace_id)
    except Exception:
        return None
```

### TypeScript (Frontend)

- **Functional components only.** No class components.
- **Named exports** for components. Default exports only for pages.
- **Tailwind for all styling.** No inline styles or CSS modules.
- **Type everything.** No `any` unless absolutely unavoidable (and add a `// TODO: type this` comment).
- **Custom hooks** for any reusable stateful logic. Keep components thin.

### Naming Patterns

| Thing               | Convention                        | Example                          |
|---------------------|-----------------------------------|----------------------------------|
| Python files        | snake_case                        | `trace_recorder.py`              |
| Python classes      | PascalCase                        | `TraceRecorder`                  |
| API routes          | `/api/v1/{resource}`              | `/api/v1/traces`                 |
| Route files         | `{resource}.py`                   | `routes/traces.py`               |
| Schema files        | `{resource}.py`                   | `schemas/traces.py`              |
| React components    | PascalCase file + export          | `TraceViewer.tsx`                |
| React hooks         | `use{Name}.ts`                    | `useTraceData.ts`                |
| Test files          | `test_{module}.py`                | `test_trace_recorder.py`         |

---

## Common Tasks — How To Do Them

### Add a new API endpoint

1. Create/edit route handler in `api/src/api/routes/{resource}.py`
2. Define request/response schemas in `api/src/api/schemas/{resource}.py`
3. Implement business logic in `api/src/api/services/{resource}.py`
4. Add DB queries in `api/src/api/dal/{resource}.py` if needed
5. Register the route in `api/src/api/routes/__init__.py`
6. Write tests in `api/tests/api/test_{resource}.py`

### Add a new SDK decorator

1. Follow the pattern in `sdk/src/usetrace/decorators/trace.py`
2. Each decorator must: capture inputs, capture outputs, record timing, and send a TraceEvent
3. Add tests in `sdk/tests/test_{decorator_name}.py`
4. Export the decorator from `sdk/src/usetrace/__init__.py`

### Add a new frontend page

1. Create the page component in `frontend/src/pages/`
2. Add the route in the router config
3. Create any needed API client functions in `frontend/src/api/`
4. Create custom hooks if the page has complex state

---

## Testing

- **Framework:** pytest + pytest-asyncio
- **Run all tests:** `make test`
- **Run API tests only:** `cd api && uv run pytest -x --tb=short`
- **Run SDK tests only:** `cd sdk && uv run pytest -x --tb=short`
- **Run specific tests:** `cd api && uv run pytest tests/api/test_health.py -v`
- **Every new module must have tests.** No exceptions.
- **Use fixtures from each package's `tests/conftest.py`** — check what's available before creating new ones.
- **Test naming:** `test_{what_it_does}` e.g., `test_trace_decorator_captures_llm_output`
- **Minimum:** test the happy path + one error case per public function.

---

## Environment Setup

```bash
# Clone and setup
cp api/.env.example api/.env
make install          # Creates venv, installs all workspace deps

# Run locally
make dev              # Starts API server on port 8000

# Check everything
make check            # Runs ruff + pytest across all packages
```

**Required env vars** (see `api/.env.example` for full list):
- `DATABASE_URL` — SQLite for local, Postgres connection string for prod
- `TRACE_API_KEY` — API key for authenticated endpoints
- `LOG_LEVEL` — DEBUG in dev, INFO in prod

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Attribution maps computed server-side | Keeps the SDK lightweight; users only install a thin client |
| SQLite for local mode | Zero-config developer experience; no DB setup needed to try Trace |
| Decorator-based API | Minimal code change for users — just add `@trace` to existing functions |
| Async throughout the API | LLM apps are I/O heavy; async prevents blocking on trace ingestion |
| Pydantic for SDK payloads too | Single source of truth for data shapes across SDK ↔ API boundary |

---

## Git Conventions

- **Conventional commits:** `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- **Branch naming:** `feat/short-description`, `fix/short-description`
- **Keep commits atomic.** One logical change per commit.
- **Write commit messages in imperative mood:** "Add trace export endpoint" not "Added trace export endpoint"

---

## What NOT to Do

- Do not generate boilerplate READMEs, CONTRIBUTING.md, or CI configs unless asked.
- Do not add comments that just restate what the code does. Comments should explain *why*.
- Do not refactor working code unless explicitly asked to.
- Do not over-engineer. Start with the simplest working solution, iterate from there.
- Do not add abstractions preemptively. Wait until there are 3+ concrete use cases.