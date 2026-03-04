# API Design Decisions — Impact Analysis

Every non-trivial decision made while building the API ingestion and read pipeline, with analysis of impact on reliability, availability, data loss, performance, scale, security, observability, and maintainability.

---

## 1. SHA-256 for API Key Authentication (not bcrypt)

**Decision**: Hash incoming API keys with SHA-256 and look up the hash in `api_keys` table. Don't use bcrypt/argon2.

**Why**: API keys are high-entropy random strings (not user-chosen passwords). Dictionary/rainbow table attacks aren't realistic. bcrypt adds 100-300ms per request by design.

| Dimension | Impact |
|-----------|--------|
| **Reliability** | Neutral — both approaches work correctly |
| **Availability** | Positive — SHA-256 is ~0.001ms vs bcrypt's ~100-300ms. Under load, bcrypt would become a bottleneck on the ingestion hot path |
| **Data loss** | Neutral — auth failure means rejection, not data loss |
| **Performance** | Positive — near-zero overhead per request. Critical for ingestion where every millisecond of latency backs up the SDK's flush thread |
| **Scale** | Positive — CPU cost is negligible even at thousands of requests/second. bcrypt would require horizontal scaling much sooner |
| **Security** | Acceptable — API keys are 32+ byte random strings with ~256 bits of entropy. SHA-256 is preimage-resistant; brute-forcing the key space is computationally infeasible. If the DB is compromised, the attacker gets hashes but can't reverse them to usable keys. **However**, if a key is leaked (e.g., committed to git), SHA-256 provides no rate-limiting protection — the attacker can use it immediately. Mitigation: key revocation (`revoked_at` column) and rotation support |
| **Observability** | Neutral — auth failures are visible as 401 responses in access logs |
| **Maintainability** | Positive — SHA-256 is in the stdlib (`hashlib`), no external dependency. Single line of code |

**Risk**: If API keys are ever low-entropy (short, predictable), SHA-256 would be vulnerable to brute force. Mitigated by generating keys with sufficient randomness (32+ bytes).

**Security hardening options**: Add rate limiting on failed auth attempts per IP. Log auth failures with the key prefix (first 8 chars) for incident response without exposing the full key.

---

## 2. ON CONFLICT DO UPDATE Upsert (dialect-aware)

**Decision**: `upsert_trace` uses `INSERT ... ON CONFLICT DO UPDATE` for atomic upserts.

**Why**: Eliminates race condition between concurrent batches writing to the same trace. Postgres path uses `func.least`, `func.greatest`, and `CASE` expressions via `stmt.excluded` to atomically widen time windows, accumulate tokens, and escalate status.

**Updated**: Originally used SELECT+UPDATE which had a lost-update race condition. Migrated to ON CONFLICT in the performance optimization pass.

---

## 3. Cursor-Based (Keyset) Pagination

**Decision**: `GET /traces` uses `cursor` + `limit` with keyset pagination on `(started_at DESC, id DESC)`.

**Why**: Eliminates deep pagination performance cliff. No OFFSET scanning, no COUNT query.

**Cursor format**: Base64url-encoded JSON `{"s": "<started_at_iso>", "i": "<id>"}`. Opaque to clients. Keyset condition: `WHERE (started_at < cursor_s) OR (started_at = cursor_s AND id < cursor_i)`. Fetches `limit + 1` rows to detect next page.

**API**: `limit` param (default 50, max 100), `cursor` param (optional, omit for first page). Response includes `next_cursor: str | None`.

**Updated**: Originally used offset-based pagination which degrades at deep page depths. Migrated to cursor-based in the performance optimization pass.

---

## 4. Savepoints Per Trace Group

**Decision**: Each `trace_id` group in a batch gets its own `begin_nested()` savepoint. One group failing doesn't abort the entire batch.

**Why**: Partial success is better than total failure for batch ingestion.

| Dimension | Impact |
|-----------|--------|
| **Reliability** | Positive — one bad trace group (e.g., constraint violation) doesn't kill the entire batch. Other trace groups in the same request are still persisted |
| **Availability** | Positive — the API returns 200 with `{accepted: N, failed: M}` instead of 500 |
| **Data loss** | Reduces data loss — without savepoints, one bad span would cause all spans in the batch to be rolled back |
| **Performance** | Slight negative — each `SAVEPOINT` + `RELEASE` is a round trip to the DB. For a batch with 10 trace groups, that's 10 extra round trips (~1ms each) |
| **Scale** | Neutral — savepoint overhead is constant per trace group, doesn't grow with data size |
| **Security** | Neutral — savepoints are a DB transaction mechanism, no auth implications. Each group is already scoped to the authenticated org_id |
| **Observability** | Positive — the `{accepted, failed}` response gives the caller (and our logs) per-batch success granularity. Failed groups are logged with full tracebacks |
| **Maintainability** | Slight negative — `begin_nested()` + savepoint semantics are an advanced SQLAlchemy feature. Requires understanding of nested transaction behavior. But well-documented in the codebase |

**Risk**: None significant. The failed groups are logged with full tracebacks (`exc_info=True`) for debugging.

---

## 5. Naive UTC Datetimes (strip timezone)

**Decision**: All datetime defaults use `datetime.now(UTC).replace(tzinfo=None)`. The `_to_naive_utc()` helper strips timezone from SDK-provided datetimes before storage.

**Why**: All DB columns are `TIMESTAMP WITHOUT TIME ZONE` (from the Alembic migration). Postgres rejects timezone-aware datetimes for these columns.

| Dimension | Impact |
|-----------|--------|
| **Reliability** | Positive — prevents `DataError` on Postgres |
| **Availability** | Positive — without this fix, every ingestion request to Postgres would fail |
| **Data loss** | Neutral — timezone info is discarded, but all times are UTC by convention. No ambiguity as long as all producers send UTC |
| **Performance** | Negligible — `replace(tzinfo=None)` is a Python object copy |
| **Scale** | Neutral |
| **Security** | Neutral — no auth or access control implications. Timezone stripping is purely a data formatting concern |
| **Observability** | Slight negative — if a client sends timestamps in a non-UTC timezone, there's no log or warning. The data silently becomes incorrect. Could add a warning log if `dt.tzinfo` is not None and not UTC |
| **Maintainability** | Slight negative — the convention "all datetimes are UTC, stored naive" is implicit. A new contributor might store a local datetime without converting. The `_to_naive_utc()` helper centralizes the logic but only covers SDK-provided datetimes, not all code paths |

**Risk**: If a client sends non-UTC timestamps, they'll be stored as-is with no conversion — the API assumes UTC. Could add explicit UTC conversion (`dt.astimezone(UTC).replace(tzinfo=None)`) for safety.

---

## 6. Drop FK on `parent_span_id`

**Decision**: Removed the self-referential foreign key `spans.parent_span_id -> spans.id`. The column is now a plain `String(36)`.

**Why**: The SDK batches spans by time/size, not by trace boundaries. A child span can arrive before its parent in a different batch. Postgres enforces the FK and rejects the INSERT.

| Dimension | Impact |
|-----------|--------|
| **Reliability** | Positive — ingestion no longer fails when spans arrive out of order |
| **Availability** | Positive — eliminates a class of silent ingestion failures that caused 100% data loss for affected traces |
| **Data loss** | Major positive — before this fix, any trace with spans split across batches would lose all spans in the child-only batch |
| **Performance** | Slight positive — Postgres no longer checks FK on every span INSERT |
| **Scale** | Positive — no ordering constraints on ingestion, enables future parallel/async ingestion pipelines |
| **Security** | Neutral — `parent_span_id` is an informational field for tree building, not an access control boundary. Org-level isolation is enforced by `org_id` on every query, not by span parent-child relationships. A malicious SDK can't reference another org's span because the dashboard always filters by `org_id` |
| **Observability** | Slight negative — orphaned `parent_span_id` references (pointing to spans that don't exist) are now possible and invisible. The dashboard handles this gracefully (shows orphans as root-level spans), but there's no metric tracking orphan rate |
| **Maintainability** | Positive — removes a constraint that was fundamentally incompatible with the SDK's async batching model. Less code (removed parent-first sorting logic). Matches industry standard (Zipkin, Jaeger, OpenTelemetry) |

**Risk**: `parent_span_id` can now reference a span that doesn't exist (orphaned reference). This is acceptable — the dashboard builds the span tree from whatever data exists. Industry standard (Zipkin, Jaeger, OpenTelemetry all do this).

---

## 7. Synchronous Write Before Response

**Decision**: `POST /ingest/batch` writes to DB and commits before returning 200. No async queue or fire-and-forget.

**Why**: Accurate response codes for observability. Natural backpressure on the SDK. Simpler architecture.

| Dimension | Impact |
|-----------|--------|
| **Reliability** | Positive — 200 means data is committed. No data sitting in an intermediate queue that could be lost on crash |
| **Availability** | Slight negative — if DB is slow or down, the API blocks and returns errors. An async approach would accept and queue |
| **Data loss** | Positive — no gap between "accepted" and "persisted". Data is committed or rejected, never in limbo |
| **Performance** | Slight negative — response latency = DB write latency. Typically 5-20ms for a batch. Acceptable since the SDK sends from a background thread |
| **Scale** | Bottleneck is DB write throughput. At high scale, would need to switch to queue-based async ingestion (Kafka/Redis → worker → Postgres) |
| **Security** | Positive — no intermediate queue that could be a target for data exfiltration or tampering. Data goes directly from the authenticated request to the DB within a single transaction. Simpler attack surface |
| **Observability** | Positive — response status code directly reflects write outcome. 200 = committed, 500 = failed. No ambiguous "accepted but not yet written" state. Latency metrics on this endpoint directly measure DB write performance |
| **Maintainability** | Positive — simplest possible architecture. No queue infrastructure to deploy, monitor, or debug. No worker processes. No retry/dead-letter queue logic. One code path |

**Risk**: DB outage causes ingestion failures. Mitigated by the SDK's one-retry logic and the fact that trace data is operational (not financial) — losing a few spans during an outage is acceptable.

---

## 8. Idempotent Span Ingestion (ON CONFLICT DO NOTHING)

**Decision**: `bulk_create_spans` uses `INSERT ... ON CONFLICT DO NOTHING` (single statement).

**Why**: The SDK can retry a failed batch. ON CONFLICT DO NOTHING is a single atomic query that handles duplicates without N+1 SELECTs.

**Updated**: Originally used per-span SELECT (N+1 anti-pattern). Migrated to ON CONFLICT DO NOTHING in the performance optimization pass.

---

## 9. `no_autoflush` + Deferred Flush

**Decision**: `bulk_create_spans` wraps the duplicate-check loop in `db.no_autoflush`, then calls `flush()` once at the end.

**Why**: Without `no_autoflush`, SQLAlchemy auto-flushes pending INSERTs before each `SELECT` query. This caused premature INSERTs that broke savepoint isolation.

| Dimension | Impact |
|-----------|--------|
| **Reliability** | Positive — ensures all span INSERTs happen as a single batch inside the savepoint. If any fail, the entire group rolls back cleanly |
| **Availability** | Neutral |
| **Data loss** | Neutral |
| **Performance** | Positive — one batch INSERT instead of N individual INSERTs. Postgres can optimize this into a single `executemany` |
| **Scale** | Positive — reduces DB round trips from 2N (N selects + N inserts) to N+1 (N selects + 1 batch insert) |
| **Security** | Neutral — purely an ORM optimization, no auth or data exposure implications |
| **Observability** | Neutral — the batch flush is transparent to logging. Errors during flush surface in the savepoint exception handler |
| **Maintainability** | Slight negative — `no_autoflush` is a SQLAlchemy-specific concept that requires understanding of the session's flush lifecycle. Well-documented in the codebase but a common source of confusion for developers unfamiliar with SQLAlchemy internals |

**Risk**: None. This is the correct pattern for SQLAlchemy when mixing reads and writes in a loop.

---

## 10. Correlated Subquery for `span_count`

**Decision**: `list_traces` uses `SELECT count(spans.id) WHERE spans.trace_id = traces.id` as a correlated subquery instead of loading spans and counting in Python.

**Why**: Avoids N+1 queries (one per trace to count its spans).

| Dimension | Impact |
|-----------|--------|
| **Reliability** | Neutral |
| **Availability** | Positive — prevents slow queries that could timeout under load |
| **Data loss** | N/A (read-only) |
| **Performance** | Positive — single query with subquery vs N+1 queries. For a page of 50 traces, this is 1 query instead of 51 |
| **Scale** | Good up to moderate scale. For very large span tables, the correlated subquery could slow down. Fix: materialized `span_count` column on the `traces` table, updated during ingestion |
| **Security** | Neutral — read-only query, already scoped to `org_id`. No data leakage risk |
| **Observability** | Positive — single query is easier to trace in DB query logs and `EXPLAIN ANALYZE` than 51 separate queries |
| **Maintainability** | Neutral — correlated subqueries are standard SQL, readable and well-understood. The SQLAlchemy expression is slightly verbose but clear |

**Risk**: Correlated subquery executes once per row in the outer query. At 50 rows per page this is fine. Would not scale to `page_size=10000`.

---

## 11. SDK Field Mapping in Service Layer

**Decision**: Field renaming (`span_id` → `id`, `start_time` → `started_at`, `inputs` → `input_locals`, `tags` → `span_metadata`) happens in `_map_span_to_orm()` in the service layer, not in Pydantic schemas.

**Why**: Keeps the schema matching the SDK's format exactly (for validation), and the ORM matching the DB exactly (for queries). The mapping is explicit and centralized.

| Dimension | Impact |
|-----------|--------|
| **Reliability** | Positive — explicit mapping makes mismatches between SDK and DB fields easy to spot and debug |
| **Availability** | Neutral |
| **Data loss** | Low risk — `output` and `module` fields from the SDK are silently dropped. If the DB schema adds these columns later, the mapping needs updating |
| **Performance** | Negligible — Python attribute assignments |
| **Scale** | Neutral |
| **Security** | Positive — the explicit mapping acts as a whitelist. Only mapped fields reach the DB. Unknown SDK fields are accepted by the schema (`extra="ignore"`) but never stored. This prevents an attacker from injecting unexpected fields into the database through the SDK payload |
| **Observability** | Slight negative — silently dropped fields (`output`, `module`) are invisible. No log when a field is ignored. Could add debug-level logging for dropped fields |
| **Maintainability** | Positive — single function to update when SDK or DB schema changes. Clear separation: schema validates, service maps, DAL persists. New fields require a conscious decision to add to the mapping |

**Risk**: New SDK fields won't be persisted until the mapping is updated. Mitigated by `extra="ignore"` on the Pydantic schema which accepts unknown fields without erroring.

---

## 12. Single `UsageEvent` Per Batch

**Decision**: One `UsageEvent(event_type="span_ingested", quantity=N)` is recorded per batch, not per span.

**Why**: Reduces write amplification. A batch of 100 spans creates 1 usage event row, not 100.

| Dimension | Impact |
|-----------|--------|
| **Reliability** | Slight risk — if the commit fails after spans are written but before the usage event, billing would under-count. Mitigated by being in the same transaction |
| **Availability** | Neutral |
| **Data loss** | Neutral for span data. Usage counts could drift if partial failures aren't accounted for (failed spans in one group still trigger a usage event for accepted spans in other groups) |
| **Performance** | Positive — 1 INSERT instead of N for billing |
| **Scale** | Positive — `usage_events` table stays small. Easy to aggregate with `SUM(quantity)` |
| **Security** | Slight risk — billing is based on the `accepted` count from the service layer, which accurately reflects inserted spans. However, the usage event is recorded outside the per-group savepoints. If a later commit fails, usage could be recorded for spans that weren't actually persisted. For billing integrity, the usage event should ideally be recorded after `db.commit()` succeeds (but before the response), not before |
| **Observability** | Positive — each batch creates exactly one usage event. Easy to correlate with ingestion logs. `SUM(quantity)` gives total span count per org per time window |
| **Maintainability** | Positive — simple pattern. One line to create the event, one line to add it to the session. Easy to extend with new event types |

**Risk**: Granularity is per-batch, not per-span. Acceptable for billing which aggregates to monthly totals anyway.

---

## 13. Exception Logging with `exc_info=True`

**Decision**: Ingestion failure warnings include the full exception traceback.

**Why**: Without it, the log just says "Failed to ingest trace group X (N spans)" with no root cause. With it, we get the exact error (FK violation, data type mismatch, etc.).

| Dimension | Impact |
|-----------|--------|
| **Reliability** | Positive — makes debugging production issues possible without reproducing locally |
| **Availability** | Neutral |
| **Data loss** | Indirectly positive — faster diagnosis means faster fixes means less sustained data loss |
| **Performance** | Negligible — traceback formatting only happens on failure path |
| **Scale** | Log volume concern if failures are frequent. Mitigated by the fact that failures should be rare after the FK/timezone fixes |
| **Security** | Slight risk — stack traces can reveal internal file paths, library versions, and DB schema details. Acceptable for server-side logs (not returned to the client). Ensure log aggregation systems (CloudWatch, Datadog, etc.) have appropriate access controls. Never include the traceback in the HTTP response body |
| **Observability** | Major positive — the primary purpose of this decision. Full tracebacks enable root-cause analysis without SSH access or local reproduction |
| **Maintainability** | Positive — no code to maintain. `exc_info=True` is a stdlib logging parameter. The alternative (manually formatting exceptions) would be more code and less information |

**Risk**: Stack traces in logs could expose internal details. Acceptable for server-side logs (not returned to the client).

---

## Summary Matrix

| Decision | Reliability | Availability | Data Loss | Performance | Scale | Security | Observability | Maintainability |
|----------|:-----------:|:------------:|:---------:|:-----------:|:-----:|:--------:|:-------------:|:---------------:|
| SHA-256 auth | = | ++ | = | ++ | ++ | + | = | + |
| ON CONFLICT upsert | ++ | = | ++ | ++ | ++ | = | = | + |
| Cursor pagination | = | + | = | ++ | ++ | + | = | = |
| Savepoints per group | ++ | ++ | ++ | - | = | = | ++ | - |
| Naive UTC datetimes | ++ | ++ | = | = | = | = | - | - |
| Drop parent_span FK | ++ | ++ | ++ | + | + | = | - | + |
| Sync write before response | ++ | - | ++ | - | - | + | ++ | ++ |
| ON CONFLICT span insert | ++ | = | ++ | ++ | ++ | + | = | + |
| no_autoflush + flush | ++ | = | = | + | + | = | = | - |
| Correlated subquery | = | + | = | ++ | + | = | + | = |
| Service-layer mapping | + | = | = | = | = | + | - | + |
| Single UsageEvent | = | = | = | + | + | - | + | + |
| exc_info logging | + | = | + | = | = | - | ++ | + |

`++` strong positive, `+` positive, `=` neutral, `-` negative, `--` strong negative

---

## Completed Optimizations

All three original scale concerns have been addressed:

1. ~~SELECT+UPDATE upsert~~ → **ON CONFLICT DO UPDATE** (Decision 2)
2. ~~Per-span SELECT~~ → **ON CONFLICT DO NOTHING** (Decision 8)
3. ~~Offset pagination~~ → **Cursor-based keyset** (Decision 3)

## Completed Security Hardening

1. **Rate limiting on auth failures** — in-memory sliding window per IP (10 failures/60s → 429)
2. **Page size clamping** — `limit` query param: `ge=1, le=100`
3. **Timestamp timezone conversion** — `_to_naive_utc` now converts via `astimezone(UTC)` before stripping
4. **Audit logging** — `logger.info("Auth success ...")` / `logger.warning("Auth failed ...")`
5. **Traceback scrubbing** — `exc_info=settings.is_debug` (only in DEBUG mode)
6. **HTTP body size limit** — 10 MB max via ASGI middleware
7. **XFF trust** — `trust_proxy_headers` setting (default False)
8. **CORS** — `Content-Type` + `Accept` added to `allow_headers`
9. **422 normalization** — custom `RequestValidationError` handler
