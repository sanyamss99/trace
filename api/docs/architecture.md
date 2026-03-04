# API Architecture Diagrams

## 1. High-Level Architecture

```mermaid
graph TB
    SDK["Python SDK<br/>(usetrace)"] -->|POST /ingest/batch| API
    Dashboard["React Dashboard"] -->|GET /traces, /spans| API
    Dashboard -->|POST/GET/DELETE /api-keys| API

    subgraph API["FastAPI Application"]
        MW["Middleware Stack"]
        Routes["Route Handlers"]
        Services["Service Layer"]
        DAL["Data Access Layer"]
    end

    DAL -->|asyncpg| DB[(PostgreSQL)]
```

## 2. Middleware & Request Pipeline

```mermaid
graph LR
    Request([Incoming Request]) --> RID["RequestIdMiddleware<br/>Assign/echo X-Request-ID"]
    RID --> Body["MaxBodySizeMiddleware<br/>Reject >10MB"]
    Body --> CORS["CORSMiddleware<br/>Allow origins, headers"]
    CORS --> Router["FastAPI Router"]
    Router --> Auth{"Requires Auth?"}
    Auth -->|No| Health["Health Endpoints"]
    Auth -->|Yes| Deps["deps.py<br/>_authenticate()"]
    Deps --> AuthRL{"Auth Rate Limit<br/>10 failures/60s per IP"}
    AuthRL -->|Blocked| R429([429 Too Many Requests])
    AuthRL -->|OK| KeyCheck["SHA-256 key lookup"]
    KeyCheck -->|Invalid/Revoked| R401([401 Unauthorized])
    KeyCheck -->|Valid| OrgRL{"Org Rate Limit<br/>10K req/60s per org"}
    OrgRL -->|Blocked| R429
    OrgRL -->|OK| Handler["Route Handler"]
    Handler --> Response([Response + X-Request-ID])
```

## 3. Exception Handling

```mermaid
graph TD
    Exc{Exception Raised} --> TA{"TraceAppError?"}
    TA -->|Yes| Map["Map to status code"]
    Map --> E401["AuthenticationError → 401"]
    Map --> E404["NotFoundError → 404"]
    Map --> E409["ConflictError → 409"]
    Map --> E429["RateLimitError → 429"]
    Map --> E400["InvalidCursorError → 400"]

    TA -->|No| RVE{"RequestValidationError?"}
    RVE -->|Yes| E422["422 + {error, details}"]
    RVE -->|No| Global["Global Handler"]
    Global --> E500["500 + {error: 'Internal server error'}<br/>Log with exc_info in debug"]
```

## 4. Data Model (ERD)

```mermaid
erDiagram
    organizations ||--o{ org_members : "has"
    organizations ||--o{ api_keys : "owns"
    organizations ||--o{ traces : "owns"
    organizations ||--o{ usage_events : "generates"
    users ||--o{ org_members : "belongs to"
    users ||--o{ api_keys : "creates"
    traces ||--o{ spans : "contains"
    spans ||--o{ span_segments : "has"

    organizations {
        string id PK
        string name
        string plan
        datetime created_at
    }

    users {
        string id PK
        string email UK
        datetime created_at
    }

    org_members {
        string org_id PK,FK
        string user_id PK,FK
        string role
        datetime joined_at
    }

    api_keys {
        string id PK
        string org_id FK
        string created_by FK
        string key_hash UK
        string name
        datetime created_at
        datetime last_used_at
        datetime revoked_at
    }

    traces {
        string id PK
        string org_id FK
        string function_name
        string environment
        datetime started_at
        datetime ended_at
        int total_tokens
        float total_cost_usd
        string status
        json tags
    }

    spans {
        string id PK
        string trace_id FK
        string parent_span_id
        string org_id FK
        string function_name
        string span_type
        string model
        datetime started_at
        datetime ended_at
        text prompt_text
        int prompt_tokens
        text completion_text
        int completion_tokens
        json completion_logprobs
        float cost_usd
        json model_params
        json input_locals
        json output
        text error
        json metadata
    }

    span_segments {
        string id PK
        string span_id FK
        string segment_name
        string segment_type
        text segment_text
        int position_start
        int position_end
        int retrieval_rank
        float influence_score
        float utilization_score
        string attribution_method
    }

    usage_events {
        string id PK
        string org_id FK
        string event_type
        datetime occurred_at
        int quantity
    }
```

## 5. Ingestion Flow

```mermaid
sequenceDiagram
    participant SDK as Python SDK
    participant API as POST /ingest/batch
    participant Auth as _authenticate()
    participant Svc as process_batch()
    participant DAL as DAL Layer
    participant DB as PostgreSQL

    SDK->>API: POST /ingest/batch<br/>[SpanIngestPayload × N]
    API->>Auth: X-Trace-Key header
    Auth->>DB: SELECT api_keys WHERE key_hash = ?
    Auth-->>API: AuthContext(org_id, user_id)

    API->>Svc: process_batch(payloads, org_id)

    loop Each trace_id group
        Svc->>Svc: _compute_trace_aggregates()
        Svc->>DB: SAVEPOINT

        Svc->>DAL: upsert_trace()
        DAL->>DB: INSERT ... ON CONFLICT DO UPDATE<br/>widen time window, accumulate tokens,<br/>escalate status

        Svc->>Svc: _map_span_to_orm() × N
        Svc->>DAL: bulk_create_spans()
        DAL->>DB: INSERT ... ON CONFLICT DO NOTHING

        alt Success
            Svc->>DB: RELEASE SAVEPOINT
        else IntegrityError / DBAPIError
            Svc->>DB: ROLLBACK TO SAVEPOINT
            Note over Svc: Log warning with org_id, continue
        end
    end

    Svc->>DB: INSERT usage_event(quantity=accepted)
    Svc-->>API: IngestResult(accepted, failed)
    API->>DB: COMMIT (via get_db lifecycle)
    API-->>SDK: 200 {status, accepted, failed}
```

## 6. Read Flow (List Traces)

```mermaid
sequenceDiagram
    participant Client as Dashboard
    participant API as GET /traces
    participant Auth as _authenticate()
    participant DAL as list_traces()
    participant DB as PostgreSQL

    Client->>API: GET /traces?limit=50&cursor=abc
    API->>Auth: X-Trace-Key header
    Auth-->>API: org_id

    API->>DAL: list_traces(org_id, limit=50, cursor="abc")
    DAL->>DAL: _decode_cursor("abc")<br/>→ (started_at, trace_id)
    DAL->>DB: SELECT traces.*, COUNT(spans.id)<br/>WHERE org_id = ? AND (started_at, id) < cursor<br/>ORDER BY started_at DESC, id DESC<br/>LIMIT 51

    DB-->>DAL: rows (≤51)

    alt len(rows) > 50
        DAL->>DAL: _encode_cursor(row[50])
        DAL-->>API: rows[:50], next_cursor
    else
        DAL-->>API: rows, None
    end

    API-->>Client: {traces: [...], next_cursor, limit}
```

## 7. Module Dependency Graph

```mermaid
graph TD
    main["main.py"] --> config["config.py"]
    main --> logger["logger.py"]
    main --> request_id["request_id.py"]
    main --> exceptions["exceptions.py"]
    main --> routes_init["routes/__init__.py"]
    main --> database["database.py"]

    logger --> config
    logger --> request_id
    database --> config

    routes_init --> health["routes/health.py"]
    routes_init --> ingest["routes/ingest.py"]
    routes_init --> traces_r["routes/traces.py"]
    routes_init --> apikeys_r["routes/api_keys.py"]

    health --> deps["deps.py"]
    ingest --> deps
    ingest --> svc_ingest["services/ingest.py"]
    traces_r --> deps
    traces_r --> dal_traces["dal/traces.py"]
    traces_r --> dal_spans["dal/spans.py"]
    apikeys_r --> deps
    apikeys_r --> dal_apikeys["dal/api_keys.py"]

    deps --> config
    deps --> database
    deps --> exceptions
    deps --> logger
    deps --> rate_limit["rate_limit.py"]
    deps --> models["models.py"]

    svc_ingest --> dal_traces
    svc_ingest --> dal_spans
    svc_ingest --> models
    svc_ingest --> constants["constants.py"]
    svc_ingest --> logger
    svc_ingest --> config

    dal_traces --> models
    dal_traces --> constants
    dal_spans --> models
    dal_apikeys --> models

    models --> constants

    schemas_ingest["schemas/ingest.py"] --> constants
    schemas_traces["schemas/traces.py"]
    schemas_apikeys["schemas/api_keys.py"]
```

## 8. API Endpoints

```mermaid
graph LR
    subgraph Public["No Auth Required"]
        H1["GET /health<br/>Liveness probe"]
        H2["GET /health/ready<br/>Readiness probe (DB check)"]
    end

    subgraph AuthOrgId["Auth: X-Trace-Key → org_id"]
        I1["POST /ingest/batch<br/>Ingest spans (≤1000)"]
        T1["GET /traces<br/>List traces (paginated)"]
        T2["GET /traces/{trace_id}<br/>Trace detail + spans"]
        T3["GET /spans/{span_id}<br/>Single span detail"]
    end

    subgraph AuthFull["Auth: X-Trace-Key → AuthContext"]
        K1["POST /api-keys<br/>Create API key (201)"]
        K2["GET /api-keys<br/>List org keys"]
        K3["DELETE /api-keys/{key_id}<br/>Revoke key (soft delete)"]
    end
```

## 9. Rate Limiting

```mermaid
graph TD
    Req([Request]) --> IPCheck{"Auth failure<br/>rate limiter"}

    IPCheck -->|"≥10 failures in 60s<br/>for this IP"| Block429([429])
    IPCheck -->|OK| AuthAttempt{"Key valid?"}

    AuthAttempt -->|No| RecordFail["Record failure<br/>for IP"]
    RecordFail --> R401([401])

    AuthAttempt -->|Yes| OrgCheck{"Org request<br/>rate limiter"}
    OrgCheck -->|"≥10K requests in 60s<br/>for this org"| Block429
    OrgCheck -->|OK| Handler["Route Handler"]
```

## 10. Logging Architecture

```mermaid
graph LR
    subgraph Request["Per-Request Context"]
        RID["RequestIdMiddleware<br/>Sets ContextVar"]
    end

    subgraph Logging["Logger Pipeline"]
        Filter["RequestIdFilter<br/>Injects request_id<br/>into LogRecord"]
        Filter --> Debug{"is_debug?"}
        Debug -->|Yes| Plain["Plain Text Formatter<br/>timestamp level name [request_id] message"]
        Debug -->|No| JSON["JsonFormatter<br/>{timestamp, level, logger,<br/>request_id, message, exception}"]
    end

    RID -.->|ContextVar| Filter
    Plain --> Stderr([stderr])
    JSON --> Stderr
```
