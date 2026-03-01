# Trace — Product Spec & Technical Design
### Real-time Causal Debugger for LLM Applications
**Version 1.0 | February 2026**

---

## Table of Contents

1. Problem Statement
2. Product Vision
3. User Personas
4. Feature Specification
5. Technical Architecture
6. Database Schema
7. API Specification
8. SDK Design
9. Attribution Algorithm
10. Dashboard UI Spec
11. Infrastructure & Deployment
12. Security & Privacy
13. Pricing & Monetization
14. Launch Plan
15. Success Metrics

---

## 1. Problem Statement

LLM applications are moving from demos to production. The number one problem teams encounter is answering a deceptively simple question: **"Why did it say that?"**

Current tools fall short in specific ways. LangSmith is tied to LangChain and treats tracing as logging rather than causal analysis. Helicone captures cost and latency but offers no insight into prompt causality. Arize has attribution for classical ML but hasn't solved the LLM-specific problem cleanly. Custom logging with print statements gives you data but no structure or insight.

The gap is not observability — it's **causality**. Developers don't just need to see what happened. They need to understand which part of their system caused it, primarily alongside other metrics such as cost, latency and reliability.

### The Core Pain, Precisely

Given a RAG pipeline that returns a wrong answer, a developer currently must:

1. Add print statements and re-run
2. Manually inspect each retrieved chunk
3. Guess which chunk influenced the answer
4. Modify the prompt and run again
5. Repeat until the answer changes

This process takes 30–90 minutes per debugging session. At scale, wrong answers in production go unresolved for days because the debugging cost is too high.

Trace reduces this to 30 seconds.

---

## 2. Product Vision

**One decorator. Full causal trace. Latency, Reliability and cost included**

Trace is an observability layer for LLM applications that answers not just *what* happened but *why*. It instruments your LLM calls, captures the full execution context, and produces a visual attribution map showing which parts of your input most influenced the output alongside  Latency, Reliability and Cost.

### What Makes Trace Different

**Causal attribution, not just logging.** Every trace includes a heatmap showing which prompt segments — system prompt, retrieved chunks, user query, few-shot examples — drove the model's response. This is the feature no competitor has shipped cleanly.

**Code-aware, not just prompt-aware.** The decorator sees the Python call context — the variables, the function, the call stack. Trace can tell you whether a wrong answer came from the retrieval logic or the user's phrasing. No external tool can do this.

**Retrieval utilization scoring.** For RAG pipelines, Trace measures which retrieved chunks actually influenced the answer versus which were retrieved but ignored. This single metric exposes the most common RAG failure mode: retrieving relevant content that the model doesn't actually use. This is important.

**Framework-agnostic.** Works with OpenAI, Anthropic, Cohere, LiteLLM, LangChain, LlamaIndex, and any custom LLM wrapper. One decorator, any framework.

---

## 3. User Personas

### Primary: The Production AI Engineer

**Who:** A software engineer (2–6 years experience) at a startup or mid-size company who has shipped an LLM-powered feature and is now debugging why it behaves inconsistently in production.

**Pain:** Getting a wrong answer report from a user, having no idea which part of the pipeline caused it, and spending an hour adding logs to find out.

**Job to be done:** "When something goes wrong, I need to understand why in under 5 minutes, not 60."

**Decision criteria:** Works with their existing stack without refactoring. Setup takes under 10 minutes. The output is immediately interpretable.

### Secondary: The AI Team Lead

**Who:** A senior engineer or tech lead managing a team building LLM features. Responsible for reliability, cost, latency and model upgrade decisions. 

**Pain:** Can't systematically evaluate whether a prompt change improved or degraded behavior across production traffic. Relies on vibes and spot-checks.

**Job to be done:** "I need to know if this prompt change made things better or worse before I ship it to everyone."

**Decision criteria:** Team-level sharing, anomaly alerting, trend dashboards. Willing to pay.

### Tertiary: The Indie AI Developer

**Who:** Solo developer building AI-powered products. Budget-sensitive. Ships fast.

**Pain:** No visibility into why their product behaves inconsistently. Can't justify paid tools.

**Job to be done:** "I need the same debugging power as big teams but for free."

**Decision criteria:** Free tier that's genuinely useful. Simple setup. No unnecessary complexity.

---

## 4. Feature Specification

### 4.1 Core SDK

**@trace decorator**

The primary interface. Wraps any function that calls an LLM.

```python
from usetrace import trace

@trace
def answer_question(query: str, context: list[str]) -> str:
    prompt = build_prompt(query, context)
    return llm.call(prompt)
```

Behavior:
- Intercepts the function call
- Captures all arguments at call time (Python locals snapshot)
- Instruments any LLM call made within the function body
- Captures: prompt string, model parameters, raw completion, latency, token counts, cost estimate, logprobs (if available)
- Flushes span data asynchronously — zero blocking on the hot path
- Links nested decorated calls as parent-child spans automatically
- Tags retrieval steps detected via heuristics (list of strings as context argument)

**auto_instrument() mode**

For codebases where adding decorators everywhere isn't practical.

```python
import usetrace
usetrace.auto_instrument()
# Now patches openai.ChatCompletion.create, anthropic.messages.create globally
```

**Context manager mode**

```python
with usetrace.span("retrieval_step") as span:
    chunks = retrieve(query)
    span.set_metadata({"chunk_count": len(chunks), "query": query})
```

**Framework callbacks**

```python
# LangChain
from usetrace.callbacks import TraceCallback
llm = ChatOpenAI(callbacks=[TraceCallback()])

# LlamaIndex
from usetrace.callbacks import TraceLlamaCallback
Settings.callback_manager = TraceLlamaCallback()
```

---

### 4.2 Ingestion Pipeline

Receives spans from SDK clients, validates, enriches, and fans out to storage and processing queues.

Responsibilities:
- API key authentication
- Schema validation
- Cost enrichment (token count × model pricing table)
- Async fan-out: write to Postgres + push to Redis queue for attribution worker
- PII scrubbing before storage (emails, phone numbers, credit card patterns)
- Rate limiting per API key

---

### 4.3 Attribution Engine

The core novel feature. Computes influence scores for each prompt segment.

**Segment detection** — automatically chunks the prompt into logical units:
- System prompt (text before the first human turn)
- Retrieved chunks (detected by structural patterns: numbered lists, separator lines, XML-tagged chunks)
- User query (the final human message)
- Few-shot examples (detected by alternating human/assistant pattern before the final query)
- Custom segments (developer-defined via `span.add_segment(name, text)`)

**Fast attribution (default, free tier):**

For each segment sᵢ in prompt P producing completion C:

```
influence(sᵢ) = |log P(C | P) - log P(C | P \ sᵢ)|
```

Implementation: n+1 API calls where n = number of segments. Uses logprobs endpoint. Cached aggressively — same prompt seen twice pays zero extra cost.

**Approximation attribution (zero extra API calls, used when logprobs unavailable):**

Uses token-level logprobs from the original completion (available in most APIs). Measures overlap between high-uncertainty completion tokens and prompt segment vocabulary. Produces ~70% correlation with full method. Default for free tier on models without logprob access.

**Deep attribution (Pro tier, open-weight models):**

Attention rollout across transformer layers for models hosted locally or via compatible APIs. Produces per-token attribution maps, not just segment-level scores. Computationally expensive — run on sampled traces only.

**Retrieval utilization score:**

Specific to RAG pipelines. For each retrieved chunk cᵢ:

```
utilization(cᵢ) = overlap(tokens(cᵢ), high_influence_completion_tokens)
```

Surfaces chunks that were retrieved but had zero influence on the answer — the primary RAG failure signal.

---

### 4.4 Dashboard

#### Trace Explorer

The home view. A table of recent traces with columns:

- Timestamp
- Function name
- Model
- Latency (ms)
- Token count
- Cost ($)
- Attribution quality (high / medium / low confidence)
- Status (success / error / anomaly)

Sortable by any column. Filterable by function name, model, date range, status. Searchable by prompt content.

#### Span Waterfall

For a selected trace. Hierarchical tree of spans showing:
- Parent-child relationships (nested function calls)
- Timeline bar showing when each span started and ended relative to total trace duration
- Expandable panel per span showing full prompt, completion, metadata

#### Attribution Heatmap

The primary differentiating view. For a selected span:

Prompt is rendered with color overlay. Each detected segment has a background color on a red-to-blue gradient where red = high influence, blue = low/no influence.

For RAG pipelines specifically: each retrieved chunk is shown as a card with its utilization score. Chunks are ranked by influence, not by retrieval rank. The delta between retrieval rank and influence rank is surfaced explicitly — "Chunk #3 was your top retrieval but had 4% influence. Chunk #7 was ranked last but drove 67% of the answer."

#### Session Replay

Multi-turn conversation timeline. Scrub through turns. Context window fill visualized as a bar showing how much of the token budget is consumed at each turn. Context loss events flagged when semantically relevant content from earlier turns is no longer in the window.

#### Anomaly Feed

Auto-detected events:
- Latency spike (>2σ above function baseline)
- Cost spike (>2σ above function baseline)
- Low-confidence completion (high entropy in completion logprobs)
- Prompt injection pattern detected (instruction-like text in user-controlled fields)
- Attribution shift (influence distribution changes significantly from baseline)

Configurable Slack/webhook alerts per anomaly type.

---

### 4.5 Regression Testing Mode

```python
@trace(baseline=True)
def answer_question(query, context):
    ...
```

When `baseline=True`, the current behavior is crystallized as the reference distribution. Future runs of the same function are compared against this baseline. Divergence is measured via:
- Output length distribution
- Semantic similarity (embedding cosine distance on completions)
- Attribution pattern similarity (did the same segments drive the answer?)

Reported as a drift score. Dashboard shows a timeline of drift scores. Useful for detecting model update impacts without writing explicit evals.

---

## 5. Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│                                                                 │
│   Python SDK          Node.js SDK         Auto-instrument       │
│   @trace decorator    TraceClient         usetrace.auto()       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ HTTPS POST /ingest/batch
                 │ (async, fire-and-forget, 2s flush interval)
                 │
┌────────────────▼────────────────────────────────────────────────┐
│                     INGESTION API                               │
│                     FastAPI + Uvicorn                           │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────┐  │
│  │   Auth   │  │   Validate   │  │  Enrich  │  │  Fan-out  │  │
│  │ API Keys │  │ Pydantic     │  │  Cost    │  │  PII      │  │
│  │   JWT    │  │ Schema       │  │  Model   │  │  Scrub    │  │
│  └──────────┘  └──────────────┘  └──────────┘  └─────┬─────┘  │
└───────────────────────────────────────────────────────┼─────────┘
                                                         │
                          ┌──────────────────────────────┤
                          │                              │
               ┌──────────▼──────┐             ┌────────▼────────┐
               │    Postgres     │             │      Redis      │
               │                 │             │                 │
               │  traces         │             │  span_queue     │
               │  spans          │             │  (attribution   │
               │  segments       │             │   jobs)         │
               │  users          │             │                 │
               │  api_keys       │             │  live_stream    │
               │  baselines      │             │  (dashboard     │
               └─────────────────┘             │   websocket)    │
                                               └────────┬────────┘
                                                        │
                                             ┌──────────▼──────────┐
                                             │  Attribution Worker  │
                                             │  (Python, async)     │
                                             │                      │
                                             │  - Pull from queue   │
                                             │  - Detect segments   │
                                             │  - Score influence   │
                                             │  - Compute RAG util  │
                                             │  - Write scores back │
                                             └──────────┬───────────┘
                                                        │
                                             ┌──────────▼──────────┐
                                             │   Dashboard API      │
                                             │   FastAPI            │
                                             │                      │
                                             │  REST endpoints      │
                                             │  WebSocket (live)    │
                                             └──────────┬───────────┘
                                                        │
                                             ┌──────────▼──────────┐
                                             │   Next.js Dashboard  │
                                             │   (Vercel or VPS)    │
                                             │                      │
                                             │  Trace Explorer      │
                                             │  Span Waterfall      │
                                             │  Attribution Map     │
                                             │  Session Replay      │
                                             └─────────────────────┘
```

### Service Boundaries

**Ingestion API** — write-only, high throughput, no business logic beyond validation and enrichment. Scales horizontally. Stateless.

**Attribution Worker** — async consumer. Pulls from Redis queue. Calls LLM APIs for logprob computation. Writes scores back to Postgres. Single instance for MVP, scales horizontally later.

**Dashboard API** — read-heavy. Serves the Next.js frontend. Handles auth, querying, filtering, aggregation. WebSocket endpoint for live trace streaming.

**Dashboard UI** — Next.js frontend. Deployed to Vercel (cloud tier) or served by Nginx on the VPS (self-hosted).

---

## 6. Database Schema

```sql
-- Organizations (every user belongs to one; hobby users get a personal org on signup)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    plan TEXT DEFAULT 'hobby', -- hobby | team | enterprise
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Org membership
CREATE TABLE org_members (
    org_id UUID REFERENCES organizations(id) NOT NULL,
    user_id UUID REFERENCES users(id) NOT NULL,
    role TEXT NOT NULL DEFAULT 'member', -- owner | admin | member
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (org_id, user_id)
);

-- API keys (scoped to org, not user — survives employee churn)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    created_by UUID REFERENCES users(id) NOT NULL, -- audit trail
    key_hash TEXT UNIQUE NOT NULL, -- bcrypt hash, never store plaintext
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

-- Core trace data
CREATE TABLE traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    function_name TEXT NOT NULL,
    environment TEXT NOT NULL DEFAULT 'default', -- production | staging | development | default
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NOT NULL,
    duration_ms INTEGER GENERATED ALWAYS AS
        (EXTRACT(EPOCH FROM ended_at - started_at) * 1000)::INTEGER STORED,
    total_tokens INTEGER,
    total_cost_usd NUMERIC(10, 6),
    status TEXT DEFAULT 'success', -- success | error | anomaly
    tags JSONB DEFAULT '{}'
);

CREATE TABLE spans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID REFERENCES traces(id) NOT NULL,
    parent_span_id UUID REFERENCES spans(id), -- null for root span
    org_id UUID REFERENCES organizations(id) NOT NULL,
    function_name TEXT NOT NULL,
    span_type TEXT DEFAULT 'llm', -- llm | retrieval | custom
    model TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NOT NULL,
    duration_ms INTEGER GENERATED ALWAYS AS
        (EXTRACT(EPOCH FROM ended_at - started_at) * 1000)::INTEGER STORED,
    -- Prompt and completion stored separately for PII scrubbing
    prompt_text TEXT,
    prompt_tokens INTEGER,
    completion_text TEXT,
    completion_tokens INTEGER,
    completion_logprobs JSONB, -- token-level logprobs if captured
    cost_usd NUMERIC(10, 6),
    model_params JSONB, -- temperature, max_tokens, etc.
    input_locals JSONB, -- Python locals snapshot at call time
    error TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Attribution results
CREATE TABLE span_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    span_id UUID REFERENCES spans(id) NOT NULL,
    segment_name TEXT NOT NULL, -- 'system_prompt' | 'chunk_1' | 'user_query' | etc.
    segment_type TEXT NOT NULL, -- 'system' | 'retrieval' | 'query' | 'few_shot' | 'custom'
    segment_text TEXT NOT NULL,
    position_start INTEGER, -- character offset in full prompt
    position_end INTEGER,
    retrieval_rank INTEGER, -- for RAG chunks: original retrieval rank
    influence_score NUMERIC(5, 4), -- 0.0000 to 1.0000
    utilization_score NUMERIC(5, 4), -- for retrieval chunks only
    attribution_method TEXT -- 'logprob_delta' | 'approximation' | 'attention_rollout'
);

-- Baseline snapshots for regression testing
CREATE TABLE baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    function_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sample_count INTEGER,
    avg_output_length NUMERIC,
    output_embedding_centroid VECTOR(1536), -- pgvector
    attribution_pattern JSONB -- avg influence by segment type
);

-- Usage metering (metered against org for billing)
CREATE TABLE usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    event_type TEXT NOT NULL, -- 'span_ingested' | 'attribution_computed'
    occurred_at TIMESTAMPTZ DEFAULT NOW(),
    quantity INTEGER DEFAULT 1
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Org members: look up which orgs a user belongs to
CREATE INDEX idx_org_members_user ON org_members(user_id);

-- API keys
CREATE INDEX idx_api_keys_org ON api_keys(org_id);

-- Traces: primary dashboard queries filter by org
CREATE INDEX idx_traces_org_started ON traces(org_id, started_at DESC);
CREATE INDEX idx_traces_org_env ON traces(org_id, environment);
CREATE INDEX idx_traces_org_function ON traces(org_id, function_name);
CREATE INDEX idx_traces_org_status ON traces(org_id, status);

-- Spans
CREATE INDEX idx_spans_trace_id ON spans(trace_id);
CREATE INDEX idx_spans_org_started ON spans(org_id, started_at DESC);

-- Span segments (unique constraint prevents duplicate attributions on retry)
CREATE UNIQUE INDEX idx_span_segments_span_segment ON span_segments(span_id, segment_name);
CREATE INDEX idx_span_segments_span_id ON span_segments(span_id);

-- Usage (billing aggregation by org per month)
CREATE INDEX idx_usage_org_month ON usage_events(org_id, date_trunc('month', occurred_at));
```

## 7. API Specification

### Ingestion API

**POST /ingest/batch**

Receives a batch of spans from the SDK. Authentication via `X-Trace-Key` header.

Request:
```json
{
  "spans": [
    {
      "id": "uuid",
      "trace_id": "uuid",
      "parent_span_id": "uuid | null",
      "function_name": "answer_question",
      "span_type": "llm",
      "model": "gpt-4o",
      "started_at": "2026-02-28T10:00:00.000Z",
      "ended_at": "2026-02-28T10:00:02.341Z",
      "prompt_text": "...",
      "prompt_tokens": 847,
      "completion_text": "...",
      "completion_tokens": 124,
      "completion_logprobs": { ... },
      "model_params": { "temperature": 0.7 },
      "input_locals": { "query": "...", "context": ["chunk1", "chunk2"] },
      "metadata": {}
    }
  ]
}
```

Response: `202 Accepted` — ingestion is async, no result in response.

**GET /health** — liveness check, returns `{ "status": "ok" }`.

---

### Dashboard API

**GET /traces**

Query params: `page`, `limit`, `function_name`, `model`, `status`, `from`, `to`, `min_cost`, `max_latency`

Response:
```json
{
  "traces": [{ "id": "...", "function_name": "...", "started_at": "...", "duration_ms": 2341, "total_cost_usd": "0.003400", "status": "success" }],
  "total": 1482,
  "page": 1
}
```

**GET /traces/:id** — full trace with all spans

**GET /spans/:id** — single span with segments and attribution scores

**GET /spans/:id/attribution** — attribution results, triggers computation if not yet available

**GET /functions** — list of decorated functions seen, with aggregate stats

**GET /functions/:name/stats** — aggregated metrics for a function over time

**GET /anomalies** — recent anomaly events

**WebSocket /live** — real-time span stream. Client subscribes, receives new spans as they arrive.

---

### Auth API

**POST /auth/signup** — email + password, returns JWT

**POST /auth/login** — returns JWT

**POST /auth/keys** — create new API key, returns plaintext key once

**DELETE /auth/keys/:id** — revoke key

---

## 8. SDK Design

### Python SDK

"""
Trace SDK — lightweight, zero-impact instrumentation for LLM applications.

Usage:
    from trace_sdk import Trace

    trace = Trace(api_key="tr_xxx", environment="production")

    @trace.observe(span_type="llm")
    def answer_question(query: str, context: list[str]) -> str:
        return openai_client.chat.completions.create(...)

Design principles:
    1. Never block, slow down, or crash the host application.
    2. Telemetry is best-effort — data loss is acceptable, host impact is not.
    3. Memory usage is bounded by a hard byte ceiling, not span count.
    4. Lock-free ingestion path — decorated functions pay near-zero overhead.
    5. No retries — if the server is down, spans are silently dropped.
"""
```
from __future__ import annotations

import atexit
import functools
import inspect
import json
import logging
import queue
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import requests

logger = logging.getLogger("trace_sdk")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_FLUSH_INTERVAL_S = 5.0
_DEFAULT_BATCH_SIZE = 50
_DEFAULT_MAX_PENDING_BYTES = 10 * 1024 * 1024  # 10 MB hard ceiling
_DEFAULT_REQUEST_TIMEOUT_S = 5
_SHUTDOWN_DRAIN_TIMEOUT_S = 3.0


# ---------------------------------------------------------------------------
# Span buffer — lock-free ingestion, bounded by estimated byte usage
# ---------------------------------------------------------------------------

class _SpanBuffer:
    """Thread-safe, memory-bounded span buffer.

    Uses queue.SimpleQueue for lock-free put() on the hot path.
    Tracks estimated memory usage and silently drops spans when the
    byte ceiling is exceeded — host app health always wins.
    """

    def __init__(self, max_pending_bytes: int = _DEFAULT_MAX_PENDING_BYTES):
        self._queue: queue.SimpleQueue[dict] = queue.SimpleQueue()
        self._max_pending_bytes = max_pending_bytes
        # Approximate tracking — not atomic, but accuracy isn't critical.
        # Slight over/under-count is fine; the goal is order-of-magnitude safety.
        self._pending_bytes = 0
        self._dropped_count = 0

    def put(self, span: dict) -> bool:
        """Enqueue a span. Returns False (and drops) if memory ceiling hit."""
        est = self._estimate_bytes(span)
        if self._pending_bytes + est > self._max_pending_bytes:
            self._dropped_count += 1
            return False
        self._queue.put(span)
        self._pending_bytes += est
        return True

    def drain(self, max_items: int) -> list[dict]:
        """Non-blocking drain of up to max_items spans."""
        batch: list[dict] = []
        drained_bytes = 0
        while len(batch) < max_items:
            try:
                span = self._queue.get_nowait()
            except queue.Empty:
                break
            drained_bytes += self._estimate_bytes(span)
            batch.append(span)
        self._pending_bytes = max(0, self._pending_bytes - drained_bytes)
        return batch

    def drain_all(self) -> list[dict]:
        """Drain everything remaining — used during shutdown."""
        return self.drain(max_items=100_000)

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    @property
    def pending_bytes(self) -> int:
        return self._pending_bytes

    @staticmethod
    def _estimate_bytes(span: dict) -> int:
        """Cheap byte estimate without serialization.

        Focuses on the two heaviest fields (prompt_text, completion_text)
        plus a flat overhead for the rest of the dict.
        """
        prompt = span.get("prompt_text") or ""
        completion = span.get("completion_text") or ""
        logprobs = span.get("completion_logprobs")
        # Each character ≈ 1 byte for ASCII/English, close enough for budgeting
        size = len(prompt) + len(completion)
        if logprobs:
            # Rough estimate: number of keys * avg value size
            size += len(logprobs) * 20 if isinstance(logprobs, dict) else 200
        size += 512  # flat overhead for other fields, dict structure, etc.
        return size


# ---------------------------------------------------------------------------
# Flush worker — background thread that ships spans to the server
# ---------------------------------------------------------------------------

class _FlushWorker:
    """Daemon thread that periodically drains the buffer and ships batches.

    Design choices:
    - No retry queue: failed batches are dropped immediately.
    - Hard HTTP timeout: a slow/hanging server never stalls the flush loop.
    - Serialization happens off the caller's thread entirely.
    """

    def __init__(
        self,
        buffer: _SpanBuffer,
        base_url: str,
        api_key: str,
        flush_interval: float,
        batch_size: int,
        request_timeout: float,
    ):
        self._buffer = buffer
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._flush_interval = flush_interval
        self._batch_size = batch_size
        self._request_timeout = request_timeout
        self._shutdown_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="trace-flush")

    def start(self):
        self._thread.start()

    def shutdown(self):
        """Signal the flush loop to exit and do a final drain."""
        self._shutdown_event.set()
        self._thread.join(timeout=_SHUTDOWN_DRAIN_TIMEOUT_S)

    def _run(self):
        while not self._shutdown_event.is_set():
            self._shutdown_event.wait(timeout=self._flush_interval)
            self._flush_all_batches()

        # Final flush on shutdown — best effort
        self._flush_all_batches()

    def _flush_all_batches(self):
        """Drain and send batches until the buffer is empty."""
        while True:
            batch = self._buffer.drain(self._batch_size)
            if not batch:
                break
            self._send(batch)

    def _send(self, batch: list[dict]):
        """POST a batch to the ingestion endpoint. Fire-and-forget."""
        url = f"{self._base_url}/ingest/batch"
        headers = {
            "X-Trace-Key": self._api_key,
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(
                url,
                data=json.dumps({"spans": batch}, default=str),
                headers=headers,
                timeout=self._request_timeout,
            )
            if resp.status_code >= 400:
                logger.debug(
                    "Trace ingestion failed: status=%d, dropped %d spans",
                    resp.status_code,
                    len(batch),
                )
        except requests.exceptions.Timeout:
            logger.debug("Trace ingestion timed out, dropped %d spans", len(batch))
        except Exception:
            # Network error, DNS failure, connection refused, etc.
            # Never raise — host app must not be affected.
            logger.debug("Trace ingestion error, dropped %d spans", len(batch), exc_info=True)


# ---------------------------------------------------------------------------
# Trace context — tracks the active trace and span hierarchy per-thread
# ---------------------------------------------------------------------------

class _TraceContext:
    """Per-thread context for correlating spans into traces.

    Uses threading.local so concurrent requests in web frameworks
    each get their own trace/span stack without interference.
    """

    def __init__(self):
        self._local = threading.local()

    @property
    def _stack(self) -> list[str]:
        if not hasattr(self._local, "span_stack"):
            self._local.span_stack = []
        return self._local.span_stack

    @property
    def trace_id(self) -> Optional[str]:
        return getattr(self._local, "trace_id", None)

    @trace_id.setter
    def trace_id(self, value: str):
        self._local.trace_id = value

    def push_span(self, span_id: str):
        self._stack.append(span_id)

    def pop_span(self):
        if self._stack:
            self._stack.pop()

    @property
    def current_parent_span_id(self) -> Optional[str]:
        return self._stack[-1] if self._stack else None

    def is_root(self) -> bool:
        return len(self._stack) == 0

    def reset(self):
        self._local.trace_id = None
        self._local.span_stack = []


# ---------------------------------------------------------------------------
# Local variable capture — snapshot function arguments for attribution
# ---------------------------------------------------------------------------

def _capture_locals(func: Callable, args: tuple, kwargs: dict) -> dict:
    """Snapshot function arguments as a JSON-serializable dict.

    Truncates large values to avoid blowing up memory. This runs in the
    caller's thread, so it must be fast.
    """
    sig = inspect.signature(func)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()

    MAX_STR_LEN = 2000
    captured = {}
    for name, value in bound.arguments.items():
        try:
            if isinstance(value, str):
                captured[name] = value[:MAX_STR_LEN]
            elif isinstance(value, (int, float, bool, type(None))):
                captured[name] = value
            elif isinstance(value, (list, tuple)):
                # Capture first few items, truncate strings within
                items = []
                for item in value[:10]:
                    if isinstance(item, str):
                        items.append(item[:MAX_STR_LEN])
                    else:
                        items.append(repr(item)[:MAX_STR_LEN])
                captured[name] = items
            elif isinstance(value, dict):
                # Shallow capture of dict keys/values
                captured[name] = {
                    str(k)[:200]: (str(v)[:MAX_STR_LEN] if isinstance(v, str) else repr(v)[:MAX_STR_LEN])
                    for k, v in list(value.items())[:20]
                }
            else:
                captured[name] = repr(value)[:MAX_STR_LEN]
        except Exception:
            captured[name] = "<capture_error>"
    return captured


# ---------------------------------------------------------------------------
# LLM response extraction — pull token counts and text from common formats
# ---------------------------------------------------------------------------

def _extract_llm_response(result: Any) -> dict:
    """Best-effort extraction of completion data from LLM client responses.

    Supports OpenAI-style response objects. Returns empty dict if
    the format isn't recognized — never raises.
    """
    extracted: dict[str, Any] = {}
    try:
        # OpenAI ChatCompletion style
        if hasattr(result, "choices") and result.choices:
            choice = result.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                extracted["completion_text"] = choice.message.content

        if hasattr(result, "usage"):
            usage = result.usage
            if hasattr(usage, "prompt_tokens"):
                extracted["prompt_tokens"] = usage.prompt_tokens
            if hasattr(usage, "completion_tokens"):
                extracted["completion_tokens"] = usage.completion_tokens

        # Logprobs (OpenAI style)
        if hasattr(result, "choices") and result.choices:
            choice = result.choices[0]
            if hasattr(choice, "logprobs") and choice.logprobs is not None:
                if hasattr(choice.logprobs, "content") and choice.logprobs.content:
                    extracted["completion_logprobs"] = [
                        {"token": lp.token, "logprob": lp.logprob}
                        for lp in choice.logprobs.content
                    ]
    except Exception:
        pass  # never fail extraction — it's optional enrichment
    return extracted


# ---------------------------------------------------------------------------
# Public API — the Trace client
# ---------------------------------------------------------------------------

class Trace:
    """Trace SDK client.

    Initialize once at app startup. Use @trace.observe() to instrument functions.

    Args:
        api_key: Your Trace API key (starts with tr_).
        base_url: Ingestion server URL.
        environment: Deployment environment tag.
        flush_interval: Seconds between background flushes.
        batch_size: Max spans per HTTP request.
        max_pending_bytes: Memory ceiling for buffered spans (bytes).
            When exceeded, new spans are silently dropped.
        request_timeout: HTTP timeout for ingestion requests (seconds).
        enabled: Set False to disable all instrumentation (zero overhead).
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.usetrace.dev",
        environment: str = "default",
        flush_interval: float = _DEFAULT_FLUSH_INTERVAL_S,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        max_pending_bytes: int = _DEFAULT_MAX_PENDING_BYTES,
        request_timeout: float = _DEFAULT_REQUEST_TIMEOUT_S,
        enabled: bool = True,
    ):
        self._enabled = enabled
        self._environment = environment
        self._context = _TraceContext()

        if not enabled:
            self._buffer = None
            self._worker = None
            return

        self._buffer = _SpanBuffer(max_pending_bytes=max_pending_bytes)
        self._worker = _FlushWorker(
            buffer=self._buffer,
            base_url=base_url,
            api_key=api_key,
            flush_interval=flush_interval,
            batch_size=batch_size,
            request_timeout=request_timeout,
        )
        self._worker.start()
        atexit.register(self.shutdown)

    # ------------------------------------------------------------------
    # Decorator — the primary instrumentation API
    # ------------------------------------------------------------------

    def observe(
        self,
        span_type: str = "custom",
        model: Optional[str] = None,
        capture_input: bool = True,
        capture_output: bool = True,
        tags: Optional[dict] = None,
    ) -> Callable:
        """Decorator to instrument a function as a Trace span.

        Args:
            span_type: One of 'llm', 'retrieval', 'custom'.
            model: LLM model name (e.g., 'gpt-4o'). Auto-detected if possible.
            capture_input: Snapshot function arguments as input_locals.
            capture_output: Extract completion text/tokens from return value.
            tags: Static key-value tags attached to the span.

        Example:
            @trace.observe(span_type="llm", model="gpt-4o")
            def generate_answer(query: str) -> str:
                ...
        """

        def decorator(func: Callable) -> Callable:
            if not self._enabled:
                return func

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._execute_span(
                    func, args, kwargs, span_type, model, capture_input, capture_output, tags
                )

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._execute_span_async(
                    func, args, kwargs, span_type, model, capture_input, capture_output, tags
                )

            if inspect.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    # ------------------------------------------------------------------
    # Span execution — sync and async paths
    # ------------------------------------------------------------------

    def _execute_span(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        span_type: str,
        model: Optional[str],
        capture_input: bool,
        capture_output: bool,
        tags: Optional[dict],
    ) -> Any:
        span_id = str(uuid.uuid4())
        is_root = self._context.is_root()

        if is_root:
            self._context.trace_id = str(uuid.uuid4())

        parent_span_id = self._context.current_parent_span_id
        trace_id = self._context.trace_id
        self._context.push_span(span_id)

        input_locals = _capture_locals(func, args, kwargs) if capture_input else None
        started_at = datetime.now(timezone.utc)

        error_text = None
        result = None
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            ended_at = datetime.now(timezone.utc)
            self._emit_span(
                span_id=span_id,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                function_name=func.__qualname__,
                span_type=span_type,
                model=model,
                started_at=started_at,
                ended_at=ended_at,
                input_locals=input_locals,
                result=result if capture_output else None,
                error=error_text,
                tags=tags,
            )
            self._context.pop_span()
            if is_root:
                self._context.reset()

    async def _execute_span_async(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        span_type: str,
        model: Optional[str],
        capture_input: bool,
        capture_output: bool,
        tags: Optional[dict],
    ) -> Any:
        span_id = str(uuid.uuid4())
        is_root = self._context.is_root()

        if is_root:
            self._context.trace_id = str(uuid.uuid4())

        parent_span_id = self._context.current_parent_span_id
        trace_id = self._context.trace_id
        self._context.push_span(span_id)

        input_locals = _capture_locals(func, args, kwargs) if capture_input else None
        started_at = datetime.now(timezone.utc)

        error_text = None
        result = None
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            ended_at = datetime.now(timezone.utc)
            self._emit_span(
                span_id=span_id,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                function_name=func.__qualname__,
                span_type=span_type,
                model=model,
                started_at=started_at,
                ended_at=ended_at,
                input_locals=input_locals,
                result=result if capture_output else None,
                error=error_text,
                tags=tags,
            )
            self._context.pop_span()
            if is_root:
                self._context.reset()

    # ------------------------------------------------------------------
    # Span emission — build the span dict and enqueue it
    # ------------------------------------------------------------------

    def _emit_span(
        self,
        span_id: str,
        trace_id: str,
        parent_span_id: Optional[str],
        function_name: str,
        span_type: str,
        model: Optional[str],
        started_at: datetime,
        ended_at: datetime,
        input_locals: Optional[dict],
        result: Any,
        error: Optional[str],
        tags: Optional[dict],
    ):
        span: dict[str, Any] = {
            "id": span_id,
            "trace_id": trace_id,
            "parent_span_id": parent_span_id,
            "function_name": function_name,
            "span_type": span_type,
            "model": model,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "environment": self._environment,
            "metadata": tags or {},
        }

        if input_locals is not None:
            span["input_locals"] = input_locals

        if error is not None:
            span["error"] = error

        # Extract LLM response data if available
        if result is not None and span_type == "llm":
            llm_data = _extract_llm_response(result)
            span.update(llm_data)

        self._buffer.put(span)

    # ------------------------------------------------------------------
    # Manual flush and lifecycle
    # ------------------------------------------------------------------

    def flush(self):
        """Force an immediate flush of buffered spans.

        Useful in serverless environments (AWS Lambda) where you need
        to flush before the runtime freezes.
        """
        if self._enabled and self._worker:
            self._worker._flush_all_batches()

    def shutdown(self):
        """Graceful shutdown — flushes remaining spans and stops the worker.

        Called automatically via atexit. Safe to call multiple times.
        """
        if self._enabled and self._worker:
            self._worker.shutdown()

    @property
    def stats(self) -> dict:
        """Diagnostic stats for monitoring SDK health.

        Returns:
            dict with pending_bytes, dropped_count — useful for logging
            in your app's health endpoint.
        """
        if not self._enabled or not self._buffer:
            return {"enabled": False}
        return {
            "enabled": True,
            "pending_bytes": self._buffer.pending_bytes,
            "dropped_spans": self._buffer.dropped_count,
        }
```

---

## 9. Attribution Algorithm

### Segment Detection

The prompt is chunked into logical segments before scoring. Detection heuristics, in order of priority:

**System prompt:** text occurring before the first `\nHuman:` or `\nUser:` marker in the assembled prompt, or the `system` role content in chat format.

**Retrieved chunks:** detected by:
- Numbered list pattern: `\n1. ...\n2. ...`
- XML tag pattern: `<doc>...</doc>` or `<context>...</context>`
- Separator pattern: `---` or `===` between paragraphs
- Explicit SDK tagging: `span.add_segment("chunk_1", text)`

**User query:** the final human-turn content.

**Few-shot examples:** alternating human/assistant pairs appearing before the final query.

---

### Provider Compatibility

Not all LLM providers expose token-level logprobs. This determines which attribution methods are available per span.

| Provider | Logprobs Support | Utilization Score | Influence Score (Ablation) |
|---|---|---|---|
| OpenAI / Azure OpenAI | ✅ `logprobs=True` | ✅ Auto (free) | ✅ On-demand |
| Google Gemini | ✅ `response_logprobs` | ✅ Auto (free) | ✅ On-demand |
| Open-source (vLLM, TGI, Ollama) | ✅ Native | ✅ Auto (free) | ✅ On-demand |
| Cohere | ✅ Token likelihoods | ✅ Auto (free) | ✅ On-demand |
| Anthropic Claude | ❌ Not exposed | ❌ Unavailable | ✅ On-demand |

For providers without logprob support, the dashboard displays: *"Utilization score unavailable for this provider. Use Explain to run influence analysis."*

The SDK auto-detects the provider from the API call being wrapped and injects the appropriate logprob parameter where supported.

---

### Retrieval Utilization Score (Default — Zero Cost)

This is the **default attribution method**, computed automatically on every span where logprobs are available. It costs zero additional API calls — it piggybacks on logprob data already returned with the original completion.

```python
def compute_utilization(chunk_text: str, completion_text: str,
                         completion_logprobs: list[TokenLogprob]) -> float:
    # Find high-uncertainty completion tokens (logprob < -1.0)
    uncertain_tokens = [
        t.token for t in completion_logprobs if t.logprob < -1.0
    ]

    # Measure vocabulary overlap between chunk and uncertain tokens
    chunk_tokens = set(tokenize(chunk_text))
    overlap = len(chunk_tokens & set(uncertain_tokens))

    return overlap / len(uncertain_tokens) if uncertain_tokens else 0.0
```

**How it works:** Tokens with logprob < -1.0 (below ~37% confidence) are where the model was uncertain and leaned on context. If a chunk's vocabulary overlaps heavily with these uncertain tokens, that chunk was actively utilized.

**Limitations:** Lexical overlap only. Paraphrased usage (chunk says "one month", completion says "30 days") scores zero. Acceptable for a fast heuristic; influence scoring covers these cases.

---

### Influence Scoring via Ablation (On-Demand — Host-Paid)

Influence scoring uses **leave-one-out ablation** to measure causal impact of each segment. It is **not computed automatically**. It runs only when a user clicks "Explain" on a specific span in the dashboard.

**Critical: all LLM calls for ablation are made using the host's own API keys, against the host's provider. Trace never makes LLM calls on behalf of the user.** The cost of attribution lies entirely with the host.

```python
async def score_segments_on_demand(span: Span, host_api_key: str) -> list[SegmentScore]:
    """
    Triggered by user action ("Explain this span").
    All API calls use the host's credentials — Trace bears no LLM cost.
    """
    segments = detect_segments(span.prompt_text)

    # --- Cache-aware computation (see Caching Strategy below) ---

    # Check span-level cache first
    span_key = make_span_cache_key(span)
    cached_result = await cache.get(span_key)
    if cached_result:
        return cached_result  # Full hit — instant return

    # Check baseline cache
    baseline_key = make_baseline_cache_key(span)
    baseline_logprob = await cache.get(baseline_key)
    if not baseline_logprob:
        baseline_logprob = await get_completion_logprob(
            prompt=span.prompt_text,
            completion=span.completion_text,
            model=span.model,
            api_key=host_api_key
        )
        await cache.set(baseline_key, baseline_logprob)

    # Check segment ablation cache — only compute misses
    tasks = []
    cache_statuses = []

    for segment in segments:
        ablated_prompt = span.prompt_text.replace(segment.text, "")
        seg_key = make_segment_cache_key(ablated_prompt, span.completion_text, span.model)
        cached_logprob = await cache.get(seg_key)

        if cached_logprob is not None:
            cache_statuses.append(("hit", cached_logprob))
        else:
            cache_statuses.append(("miss", seg_key))
            tasks.append(get_completion_logprob(
                prompt=ablated_prompt,
                completion=span.completion_text,
                model=span.model,
                api_key=host_api_key
            ))

    # Fire only the uncached ablation calls in parallel
    computed_logprobs = await asyncio.gather(*tasks)

    # Merge cached + computed results
    computed_idx = 0
    ablated_logprobs = []
    for status, value in cache_statuses:
        if status == "hit":
            ablated_logprobs.append(value)
        else:
            logprob = computed_logprobs[computed_idx]
            await cache.set(value, logprob)  # value is the cache key
            ablated_logprobs.append(logprob)
            computed_idx += 1

    # Score and normalize
    scores = []
    for segment, ablated_logprob in zip(segments, ablated_logprobs):
        influence = abs(baseline_logprob - ablated_logprob)
        scores.append(SegmentScore(segment=segment, raw_influence=influence))

    total = sum(s.raw_influence for s in scores)
    for s in scores:
        s.influence_score = s.raw_influence / total if total > 0 else 0

    # Cache the full result at span level
    await cache.set(span_key, scores)

    return scores
```

**Cost:** n+1 API calls per span *maximum* (1 baseline + n segments), billed to the host's account. Calls run in parallel — wall-clock latency ≈ 1 round-trip. Segment-level caching reduces actual API calls over time (see below).

**When to use:**
- Debugging a specific hallucination or unexpected output
- Verifying that the right retrieval chunks drove a response
- Auditing prompt design (which few-shot examples actually matter?)

---

### Attribution Caching Strategy

Attribution caching operates at **three levels** — span-level, segment-level, and baseline-level — to maximize cache hit rates across similar prompts while keeping infrastructure costs proportional to actual usage.

#### Cache Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Cache Lookup Flow                     │
│                                                         │
│  1. Span-level cache (exact match)                      │
│     Key: sha256(full_prompt + completion + model)        │
│     Hit? → Return full attribution instantly             │
│     Miss? ↓                                             │
│                                                         │
│  2. Baseline cache                                      │
│     Key: sha256(full_prompt + completion + model)        │
│     Hit? → Skip baseline API call (save 1 call)         │
│     Miss? → Compute baseline, cache result              │
│                                                         │
│  3. Segment ablation cache (partial reuse)              │
│     Key: sha256(ablated_prompt + completion + model)     │
│     Per-segment lookup — some may hit, others miss      │
│     Hit? → Skip that segment's API call                 │
│     Miss? → Compute, cache result                       │
│                                                         │
│  Result: Only novel ablations trigger API calls.         │
│  Repeated segments across spans get progressively free.  │
└─────────────────────────────────────────────────────────┘
```

#### Level 1: Span-Level Cache (Exact Match)

The fast path. If the exact same prompt + completion + model has been attributed before, return the full result.

```python
span_cache_key = sha256(prompt_text + completion_text + model)
```

**When this hits:** Re-runs of the same request (retries, duplicate webhook deliveries), or a user clicking "Explain" a second time on the same span.

**Storage:** Redis. These are the most frequently accessed and should be fast.

#### Level 2: Baseline Logprob Cache

The baseline call (full prompt + completion logprob) is identical for every attribution request on the same span. But it's also reusable if the same prompt-completion pair appears across different attribution runs.

```python
baseline_cache_key = sha256(prompt_text + completion_text + model)
```

This is technically the same key as Level 1, but stored separately because a baseline might exist without the full attribution being complete (e.g., ablation was interrupted or partially computed).

**Savings:** 1 API call per cache hit. Always checked before starting ablation.

#### Level 3: Segment Ablation Cache (Partial Reuse)

This is where the major savings come from. Each ablation result is cached independently:

```python
segment_cache_key = sha256(ablated_prompt + completion_text + model)
```

Where `ablated_prompt` = full prompt with that specific segment removed.

**Why this matters:** Consider a production RAG app where:
- The system prompt is identical across 100% of spans
- Few-shot examples are identical across 100% of spans
- Retrieved chunks vary per query
- User queries are unique

When a user clicks "Explain" on span #500, the ablation for "prompt minus system prompt" and "prompt minus few-shot" might already be cached from a *different* span that shared those segments AND had the same remaining prompt + completion. This is a narrower hit condition than pure segment reuse, but it compounds over time for apps with high prompt structure similarity.

**Partial failure recovery:** Within the same span, if a user triggers "Explain" and the job partially fails (network error after 4 of 8 ablation calls), the completed ablations are already cached. Retry only computes the missing ones.

#### TTL Strategy

Fixed TTL is wasteful for stable segments and too generous for volatile ones. TTL scales with **segment stability** — how often the segment appears unchanged across spans.

| Cache Level | TTL | Rationale |
|---|---|---|
| Span-level (full attribution) | 7 days | Exact results don't change. Evict to reclaim memory, not for freshness. |
| Baseline logprob | 7 days | Same reasoning — deterministic given inputs. |
| Segment ablation (high-frequency segment) | 7 days | System prompts, few-shot examples — rarely change, high reuse value. |
| Segment ablation (low-frequency segment) | 48 hours | Unique chunks, user queries — low reuse probability, don't waste memory. |

**Frequency classification:** When caching a segment ablation, tag it with the segment type from detection (system_prompt, few_shot, retrieved_chunk, user_query). Apply TTL based on type:

```python
TTL_BY_SEGMENT_TYPE = {
    "system_prompt": 7 * 86400,    # 7 days — almost never changes
    "few_shot":      7 * 86400,    # 7 days — rarely changes
    "retrieved_chunk": 2 * 86400,  # 48 hours — moderate reuse
    "user_query":    2 * 86400,    # 48 hours — low reuse
}
```

**Eviction under memory pressure:** LRU eviction within each TTL tier. Span-level results are evicted first (cheapest to recompute from segment cache), segment ablations last (most expensive to recompute).

#### Storage Backend

**Redis** for all cache levels. Segment ablation values are small (a single float per entry), so memory footprint stays low even at scale.

Estimated memory per span attribution:
- Span-level result: ~2 KB (serialized score list)
- Baseline logprob: ~64 bytes
- Segment ablation: ~64 bytes × n segments

For 100K cached span attributions with avg 6 segments: ~200 MB baseline + ~38 MB segment cache ≈ **~250 MB total Redis footprint**. Well within a single Redis instance.

If scale demands it, segment ablation cache can be migrated to a cheaper store (DynamoDB, Postgres) with minimal latency impact since it's only accessed during on-demand computation, not dashboard rendering.

#### Cache Hit Rate Projections

For a typical production RAG app:

| Scenario | Expected Hit Rate | API Calls Saved |
|---|---|---|
| User clicks "Explain" twice on same span | 100% (span-level) | All n+1 calls |
| Two spans share system prompt + few-shot, differ in chunks + query | ~25-35% (2-3 of 8 segments) | 2-3 calls per span |
| High-traffic app, 1000 spans/day, 5% explained | Increasing over time | Compounds as segment cache fills |
| Same user debugging similar queries in a session | 40-60% | Significant within a session |

The cache becomes more valuable over time as segment ablations accumulate, particularly for the stable parts of the prompt (system prompt, few-shot) that repeat across every span.

---

### Cost Model Summary

| Action | Who pays | Cost |
|---|---|---|
| Span ingestion + utilization score | Trace | Zero LLM cost (logprobs from original call) |
| Influence scoring (on-demand) | Host | n+1 API calls max at host's provider rate (reduced by cache hits) |
| Cached influence retrieval | Trace | Zero (Redis lookup) |

Trace's infrastructure cost is limited to ingestion, storage, and serving the dashboard. All LLM compute for attribution is borne by the host.

## 10. Dashboard UI Spec


**MVP (10-Day Sprint) + Month 1 Roadmap**

Version 1.0 · March 2026

---

## 10.1. Overview

Trace is a real-time causal debugger that answers the production question: *"why did the LLM say that?"* The dashboard is the primary interface where developers investigate traces, explore attribution heatmaps, and identify anomalies in their LLM pipelines.

This spec defines two phases: the **MVP (10-day sprint)** focused on a single jaw-dropping demo flow, and **Month 1** enhancements that expand toward a production-ready product.

---

## 10.2. Tech Stack

| Layer | Choice |
|---|---|
| **Framework** | Next.js 14 (App Router) |
| **UI Components** | shadcn/ui (consistent, no custom CSS needed) |
| **Data Fetching** | TanStack Query (caching, background refresh) |
| **Charts** | Recharts (trace waterfall, cost timelines) |
| **Heatmap** | Custom canvas rendering (performance, pixel-precise gradients) |
| **Real-time (MVP)** | SSE or polling every 2–3s (simpler than WebSocket) |
| **Real-time (Month 1)** | Native WebSocket via `useWebSocket` hook |
| **Auth** | NextAuth.js (email/password) |

> **Note:** WebSocket is deferred to Month 1. For MVP, SSE or short-polling achieves the same perceived real-time feel with significantly less infrastructure — no reconnection logic, no backpressure handling, no auth handshake.

---

## 10.3. Page Structure

### 10.3.1 MVP Pages (3 Routes)

The MVP ships exactly three pages. Every engineering hour goes toward making these three screens polished and demo-ready.

| Route | Phase | Description |
|---|---|---|
| `/login` | 🟢 MVP | Email/password login via NextAuth.js. Clean, minimal form. |
| `/traces` | 🟢 MVP | Trace Explorer with filtering by function name, status, and time range. The primary navigation entry point. |
| `/traces/[id]` | 🟢 MVP | Trace Detail with waterfall view, span list, and inline attribution heatmap. **The hero screen.** |

### 10.3.2 Month 1 Additions

| Route | Phase | Description |
|---|---|---|
| `/signup` | 🟡 Month 1 | Self-serve account creation with email verification. |
| `/spans/[id]` | 🟡 Month 1 | Dedicated Span Detail page with full-screen heatmap and RAG chunk view. |
| `/functions` | 🟡 Month 1 | Function Analytics: aggregated latency (p50/p99), error rates, cost trends per function. |
| `/anomalies` | 🟡 Month 1 | Anomaly Feed: auto-detected outliers in latency, cost, or attribution drift. |
| `/settings` | 🟡 Month 1 | API keys management, billing, team member invitations. |

---

## 10.4. Trace Explorer (`/traces`)

The Trace Explorer is the developer's entry point. It must answer the question: *"show me the trace for the function call I want to debug."*

### 10.4.1 MVP Requirements

- **Function name filter** — Dropdown or search bar to filter traces by the decorated function name. This is the primary navigation path — developers think in functions, not trace IDs.
- **Status filter** — Quick toggles for `error` / `slow` / `ok` status.
- **Time range** — Last 1h / 6h / 24h / 7d selector.
- **Trace list table** — Columns: function name, status badge, latency, token count, timestamp. Clickable rows navigate to `/traces/[id]`.
- **Sort** — Default sort by timestamp (newest first). Click column headers to sort by latency or status.
- **Pagination** — Load up to 50 traces per page with cursor-based pagination.

### 10.4.2 Month 1 Enhancements

- **Full-text search** — Search across prompt content, function names, and metadata.
- **Saved filters** — Let developers save common filter combinations (e.g., "my generate_summary errors this week").
- **Bulk actions** — Select multiple traces to compare, export, or delete.
- **Live indicator** — Pulsing dot when new traces arrive via WebSocket, with auto-prepend to the list.

---

## 10.5. Trace Detail (`/traces/[id]`)

This is the **hero screen** — the page that makes Trace visually distinctive and demo-worthy. It combines the execution waterfall with the attribution heatmap in a single, cohesive view.

### 10.5.1 Layout (MVP)

- **Top bar** — Trace ID, function name, total latency, total tokens, timestamp, status badge.
- **Left panel — Waterfall** — Vertical timeline showing each span (LLM call, retrieval, tool use) with duration bars. Click a span to load its attribution data in the right panel.
- **Right panel — Attribution Heatmap** — Canvas-rendered prompt text with color-coded influence scores. This is the "why did it say that?" answer, visualized.
- **Interaction** — Click a span in the waterfall → heatmap highlights the relevant prompt segments with a smooth transition animation. *This click-to-reveal moment is the core demo experience.*

### 10.5.2 Month 1 Enhancements

- **Side-by-side prompt → output view** — Hover over a word in the output, and the prompt segments that influenced it glow. Linked highlighting between input and output.
- **Span comparison** — Select two spans to diff their attribution maps.
- **Cost breakdown** — Per-span cost displayed in the waterfall, with total cost in the top bar.
- **Export** — Download trace as JSON or shareable link for team debugging.

---

## 10.6. Attribution Heatmap

The heatmap is the visual core of Trace — the feature that differentiates it from every other LLM observability tool. It must be fast, beautiful, and immediately intuitive.

### 10.6.1 Rendering (Canvas)

The heatmap is rendered on a canvas element, not SVG or DOM. This is a deliberate choice for performance with large prompts, pixel-precise color gradients, and zero layout thrashing.

**Rendering algorithm:**

1. Receive prompt text and segment scores from API.
2. Split prompt into characters, map each character to its segment.
3. Map segment influence score to color using a diverging colormap.
4. Render text character-by-character with colored background.
5. On hover: show tooltip with segment name, influence score, and utilization score.

### 10.6.2 Color Scale (Updated)

**Original spec:** `hsl(score * 240, 70%, 60%)` — this produces a blue→green→cyan progression that is perceptually non-linear and confusing.

**Updated for MVP:** Use a sequential **white → yellow → red** colormap. Low influence = white/transparent, high influence = deep red. This is immediately intuitive — "red means important" requires zero learning curve. The squint test: if you can still tell high from low influence when squinting, the scale works.

### 6.3 RAG View (Month 1)

For RAG-augmented traces, render retrieved chunks as cards sorted by influence score (not retrieval rank). Display the delta between retrieval rank and influence rank prominently — this reveals when the retriever is pulling irrelevant context.

---

## 10.7. Demo Mode (MVP Critical)

> **This is the single most important feature for launch success.**

A visitor lands on the site, clicks "Try Demo," and instantly sees a real LLM trace with the attribution heatmap lit up. No SDK installation, no account creation, no waiting.

### 10.7.1 Requirements

- **Pre-loaded sample trace** — A realistic, visually impressive trace baked into the app. Choose a trace that shows clear attribution patterns (e.g., a RAG pipeline where one retrieved chunk dominates the output).
- **Guided walkthrough** — Subtle tooltip sequence (3–4 steps) that walks the visitor through: click a span → see the heatmap → hover for details → "Install SDK to see your own traces."
- **No auth required** — Demo mode bypasses login entirely. The visitor can explore the sample trace without creating an account.
- **CTA placement** — "Get Started" button always visible, linking to signup + SDK installation docs.

**Why this matters:** The demo mode is what you screen-record for Twitter and Hacker News. It's the screenshot that goes viral. Invest heavily in making the sample trace visually stunning.

---

## 10.8. Function → Trace Navigation

Developers think in functions, not trace IDs. The dashboard must support the workflow: *"my `generate_summary` function is acting weird → show me recent traces for that function → pick one → see the heatmap."*

### 10.8.1 MVP Approach

For MVP, this is solved entirely through the Trace Explorer's filter bar. No separate Function Analytics page is needed.

- **Function name as filterable dimension** — The trace list includes a function name column. Clicking a function name filters the list to show only traces for that function.
- **Autocomplete in filter bar** — As the developer types a function name, autocomplete suggests matching functions from recent traces.

### 10.8.2 Data Model: Immutable Function Names

Traces store the function name as a **string field at ingestion time**, not as a foreign key to a mutable function registry. This means if a developer renames a function, old traces retain the old name and new traces use the new name. This is correct behavior — traces are immutable records of what actually happened at execution time.

> *Post-MVP consideration: If function renaming becomes a pain point, add a function alias/grouping feature where a developer can link old and new names. This is explicitly out of scope for MVP.*

### 10.8.3 Month 1: Function Analytics Page

The dedicated `/functions` page provides aggregated views that help developers who are *monitoring* (not just debugging):

- **Per-function dashboard** — Median and p99 latency trends, error rates, token usage, and cost over time.
- **Function comparison** — Select 2–3 functions to overlay their latency or cost trends.
- **Drill-down** — Click any data point on a function chart to see the underlying traces.
- **Alerting hooks** — Set thresholds (e.g., "alert if p99 latency exceeds 5s") with webhook notifications.

---

## 10.9. Real-Time Updates

### 10.9.1 MVP: SSE / Polling

For MVP, use Server-Sent Events (SSE) or short-polling every 2–3 seconds. This gives the visual effect of "live updating" traces appearing in the explorer, which is sufficient for the demo and early users.

- SSE endpoint: `GET /api/traces/stream` returns new trace summaries as they're ingested.
- Trace Explorer auto-prepends new traces to the list with a subtle slide-in animation.
- Trace Detail page refreshes span data when new spans arrive for the current trace.

### 10.9.2 Month 1: WebSocket

Upgrade to native WebSocket for true bidirectional communication:

- **`useWebSocket` hook** — Handles connection, reconnection (exponential backoff), auth token refresh, and message parsing.
- **Channels** — Subscribe to specific traces or functions for targeted updates.
- **Backpressure** — Client-side buffering when the UI can't render fast enough (e.g., during bulk ingestion).

---

## 10.10. Performance Targets

### 10.10.1 MVP Targets

These targets are pragmatic for the 10-day sprint. The priority is visual polish, not benchmarking.

| Metric | Target |
|---|---|
| Trace list load | Under 1s for up to 200 traces (realistic MVP scale) |
| Trace detail load | Under 500ms including waterfall render |
| Heatmap render | Under 200ms for prompts up to 4k tokens (typical early usage) |
| SSE/poll latency | Under 3s from span ingestion to dashboard display |

### 10.10.2 Month 1 Targets

| Metric | Target |
|---|---|
| Trace list load | Under 500ms for up to 1,000 traces with virtual scrolling |
| Span detail load | Under 200ms (attribution loads async) |
| Heatmap render | Under 100ms for prompts up to 10k tokens |
| WebSocket latency | Under 500ms from span ingestion to dashboard display |

---

## 10.11. Empty States & Onboarding (MVP)

The first experience must not be a blank page. Every empty state should guide the developer toward the next action.

- **Empty Trace Explorer** — Full-screen card with: "No traces yet. Install the SDK to send your first trace." Includes a code snippet showing the decorator syntax and a link to docs. Below: "Or try the demo" button.
- **Empty Trace Detail** — Should never happen in normal flow (developer navigates from a list), but if accessed via direct URL, show: "Trace not found. View all traces."
- **Loading states** — Skeleton loaders for the trace list and heatmap. Never show a blank white panel.
- **Error states** — Friendly error messages with retry buttons. Never show raw stack traces to the user.

---

## 10.12. Phase Summary

### 10.12.1 MVP Scope (Days 1–10)

The MVP is ruthlessly scoped to three pages and one stunning demo flow. Every hour spent on anything else is an hour stolen from the heatmap.

| Feature | Phase | Description |
|---|---|---|
| Login page | 🟢 MVP | Email/password auth via NextAuth.js |
| Trace Explorer | 🟢 MVP | Filterable trace list (function name, status, time range) |
| Trace Detail | 🟢 MVP | Waterfall + inline attribution heatmap with click-to-reveal animation |
| Demo Mode | 🟢 MVP | Pre-loaded sample trace, no auth required, guided walkthrough |
| Attribution Heatmap | 🟢 MVP | Canvas-rendered, white→yellow→red colormap, hover tooltips |
| SSE/Polling | 🟢 MVP | 2–3s refresh for live trace updates |
| Empty States | 🟢 MVP | Onboarding guidance, skeleton loaders, error handling |

### 10.12.2 Month 1 Additions

| Feature | Phase | Description |
|---|---|---|
| Signup + verification | 🟡 Month 1 | Self-serve account creation |
| Span Detail page | 🟡 Month 1 | Full-screen heatmap with RAG chunk visualization |
| Function Analytics | 🟡 Month 1 | Aggregated latency, error rates, cost per function |
| Anomaly Feed | 🟡 Month 1 | Auto-detected outliers and attribution drift |
| Settings | 🟡 Month 1 | API keys, billing, team management |
| Side-by-side view | 🟡 Month 1 | Linked prompt → output highlighting |
| WebSocket | 🟡 Month 1 | True real-time with reconnection and backpressure |
| Function aliasing | 🟡 Month 1 | Group renamed functions under a single identity |

---

## 10.13. Design Principles

These principles guide every UI decision across both phases:

- **The heatmap is the product.** Every design choice should make the attribution visualization more impressive, more intuitive, and more shareable. If a feature doesn't enhance the heatmap experience, it can wait.

- **Demo-first development.** Build for the screen recording. If it doesn't look amazing in a 30-second GIF, rethink the interaction.

- **Developers are the audience.** Use monospace fonts for code, dark-mode support (Month 1), and information density over whitespace. Developers want data, not marketing.

- **Traces are immutable.** Never retroactively modify trace data. What was recorded is what happened. This applies to function names, timestamps, and attribution scores.

- **Progressive disclosure.** Show the trace list first, then the waterfall, then the heatmap. Each click reveals more detail. Don't overwhelm on the first screen.
---

### 11. Infrastructure & Deployment

> Complete infrastructure requirements for launching and operating Trace as a production SaaS.
> Estimated setup time: 2–3 days for must-haves, 1 week for full setup.

---

## 1. Hosting & Compute

### Primary: Hetzner Cloud

| Resource | Spec | Cost |
|----------|------|------|
| VPS | CX31 — 4 vCPU, 8 GB RAM, 80 GB disk | €11/mo |
| Region | Ashburn, Virginia (US-East) | — |
| Object Storage | For backups, €0.023/GB | ~€1–2/mo |
| VPS Snapshots | Pre-deploy rollback, €0.012/GB/mo | ~€1/mo |

**Why Hetzner:** Best price-to-performance for early-stage SaaS. 4–6x cheaper than equivalent AWS/GCP instances. Docker Compose friendly with no vendor lock-in.

**Architecture on single VPS:**

```
Hetzner CX31 (Ashburn)
├── Docker Compose
│   ├── ingestion-api (FastAPI, 2 workers)
│   ├── dashboard-api (FastAPI, 2 workers)
│   ├── attribution-worker (Python, 1 instance)
│   ├── postgres:16 (persistent volume)
│   ├── redis:7 (persistent volume)
│   └── nginx (reverse proxy)
├── Certbot (if not using Cloudflare SSL)
└── GitHub Actions → deploy on push to main
```

**Setup references:**
- Hetzner Cloud Console: https://console.hetzner.cloud
- Hetzner CLI (`hcloud`): https://github.com/hetznercloud/cli
- Docker on Ubuntu 24: https://docs.docker.com/engine/install/ubuntu/

---

## 2. Domains & DNS

### Domain Registration

Register `usetrace.dev` via **Cloudflare Registrar** (at-cost pricing, no markup).

| Subdomain | Points To | Purpose |
|-----------|-----------|---------|
| `app.usetrace.dev` | Vercel (cloud) / Hetzner IP (self-hosted) | Next.js dashboard |
| `api.usetrace.dev` | Hetzner VPS IP | Ingestion + Dashboard API |
| `docs.usetrace.dev` | Mintlify / Docusaurus host | Documentation |
| `status.usetrace.dev` | Betterstack status page | Uptime/incident status |

### DNS Provider: Cloudflare (Free Tier)

Use Cloudflare as the DNS provider regardless of where you registered the domain. Free tier includes DNS management, CDN, DDoS protection, and SSL proxy.

**Setup references:**
- Cloudflare Registrar: https://www.cloudflare.com/products/registrar/
- Namecheap (alternative): https://www.namecheap.com
- Cloudflare DNS setup: https://developers.cloudflare.com/dns/zone-setups/full-setup/

---

## 3. SSL/TLS

### Option A: Cloudflare SSL (Recommended)

If Cloudflare is proxying your traffic (orange cloud icon on DNS records), SSL is automatic. No Certbot needed.

**Critical:** Set SSL mode to **"Full (Strict)"** in Cloudflare dashboard. "Flexible" mode causes infinite redirect loops with FastAPI.

For origin certificates (Cloudflare → your server), generate a Cloudflare Origin CA certificate:
- Cloudflare Dashboard → SSL/TLS → Origin Server → Create Certificate
- Install on Nginx inside your Docker Compose

### Option B: Certbot + Let's Encrypt

If not using Cloudflare proxy, use Certbot in your Docker Compose for automatic certificate provisioning and renewal.

```yaml
# docker-compose.yml snippet
certbot:
  image: certbot/certbot
  volumes:
    - ./certbot/conf:/etc/letsencrypt
    - ./certbot/www:/var/www/certbot
  entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
```

**Setup references:**
- Cloudflare SSL modes: https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/
- Cloudflare Origin CA: https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/
- Certbot with Docker + Nginx: https://mindsers.blog/en/post/https-len-encrypt-len-docker-len-len-len/

---

## 4. Email

### Transactional Email: Resend

For signup verification, password resets, alert notifications, billing receipts.

| Provider | Free Tier | Why |
|----------|-----------|-----|
| **Resend** | 3,000 emails/mo | Developer-friendly API, great deliverability |
| Postmark (alt) | 100 emails/mo | Best deliverability, small free tier |

```python
# Example: sending with Resend
import resend
resend.api_key = "re_xxxxx"

resend.Emails.send({
    "from": "Trace <notifications@usetrace.dev>",
    "to": ["user@example.com"],
    "subject": "Verify your Trace account",
    "html": "<p>Your verification code is: 123456</p>"
})
```

**DNS records required:** Add Resend's SPF, DKIM, and DMARC records to your Cloudflare DNS to ensure deliverability.

### Business Email

Use **Cloudflare Email Routing** (free) to forward `sanyam@usetrace.dev` → your personal Gmail. To send *from* that address, configure Gmail "Send mail as" with an SMTP relay (Resend SMTP or Gmail app password).

**Setup references:**
- Resend quickstart: https://resend.com/docs/introduction
- Cloudflare Email Routing: https://developers.cloudflare.com/email-routing/
- Gmail "Send as" setup: https://support.google.com/mail/answer/22370

---

## 5. Authentication

### Cloud Tier: Clerk (Recommended)

| Provider | Free Tier | Strengths |
|----------|-----------|-----------|
| **Clerk** | 10,000 MAUs | Best DX, prebuilt components, OAuth + magic links |
| Auth.js | Unlimited (self-hosted) | Free, pairs with Next.js, more setup work |
| Supabase Auth | 50,000 MAUs | Good if you ever move Postgres to Supabase |

Clerk provides prebuilt React components for sign-in/sign-up, handles JWT issuance, and integrates directly with Next.js middleware.

```typescript
// Next.js middleware with Clerk
import { clerkMiddleware } from "@clerk/nextjs/server";
export default clerkMiddleware();
```

### Self-Hosted Tier: API Key Auth

Keep it simple — no OAuth, no third-party auth provider dependency.

```python
# FastAPI dependency for API key auth
async def verify_api_key(x_api_key: str = Header(...)):
    key = await db.fetch_one("SELECT * FROM api_keys WHERE key = $1", x_api_key)
    if not key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key
```

**Setup references:**
- Clerk Next.js quickstart: https://clerk.com/docs/quickstarts/nextjs
- Auth.js (NextAuth): https://authjs.dev/getting-started
- Supabase Auth: https://supabase.com/docs/guides/auth

---

## 6. Billing & Payments

### Launch: Lemon Squeezy (Merchant of Record)

Lemon Squeezy handles tax, VAT, GST globally — no need for a registered business entity to start.

| Provider | Fees | Business Entity Needed? | Tax Handling |
|----------|------|------------------------|--------------|
| **Lemon Squeezy** | 5% + $0.50 | No (individuals OK) | Full MoR — they handle everything |
| Paddle | 5% + $0.50 | No | Full MoR |
| Stripe | 2.9% + $0.30 | Yes (LLP/Pvt Ltd in India) | You handle tax yourself |

**Webhook integration** — handle subscription events in your dashboard API:

```python
@app.post("/webhooks/lemonsqueezy")
async def handle_billing_webhook(request: Request):
    payload = await request.json()
    event = payload["meta"]["event_name"]

    if event == "subscription_created":
        await activate_user_plan(payload["data"])
    elif event == "subscription_expired":
        await downgrade_user_plan(payload["data"])
```

**Migration path:** Move to Stripe once you register a business entity (LLP or Pvt Ltd) and want lower fees. Stripe Atlas can help register a US entity if needed.

**Setup references:**
- Lemon Squeezy docs: https://docs.lemonsqueezy.com
- Paddle: https://developer.paddle.com/getting-started
- Stripe Atlas (for later): https://stripe.com/atlas

---

## 7. Documentation

### Mintlify (Recommended)

Free for open-source projects. Beautiful out-of-the-box design, MDX-based, auto-generates API reference from OpenAPI spec.

Host at `docs.usetrace.dev`.

**Minimum pages for launch:**

```
docs/
├── quickstart.mdx          # Install SDK, send first trace, view attribution
├── sdk-reference/
│   ├── python.mdx           # @trace decorator, configuration options
│   └── configuration.mdx    # Environment variables, PII modes
├── self-hosting/
│   ├── docker-compose.mdx   # One-command setup guide
│   └── configuration.mdx    # .env options, scaling tips
├── api-reference/
│   ├── ingestion.mdx        # POST /v1/traces endpoint
│   └── dashboard.mdx        # GET endpoints for traces, attribution
└── concepts/
    └── attribution.mdx      # How attribution scoring works
```

**Alternatives:**
- Docusaurus (free, self-hosted, React): https://docusaurus.io
- GitBook (free for OSS): https://www.gitbook.com

**Setup references:**
- Mintlify quickstart: https://mintlify.com/docs/quickstart
- Mintlify OpenAPI integration: https://mintlify.com/docs/api-playground/openapi

---

## 8. Monitoring & Uptime

### Uptime Monitoring: Betterstack (Free Tier)

- Monitor `api.usetrace.dev/health` and `app.usetrace.dev` every 3 minutes
- Auto-creates a status page at `status.usetrace.dev`
- Alerts via email/Slack/Discord on downtime

### Error Tracking: Sentry (Free Tier)

- 5,000 events/month on free tier
- Add to both FastAPI services and Next.js dashboard

```python
# FastAPI + Sentry
import sentry_sdk
sentry_sdk.init(dsn="https://xxx@sentry.io/xxx", traces_sample_rate=0.1)
```

### Health Check Endpoints

Add to both FastAPI services:

```python
@app.get("/health")
async def health():
    checks = {}
    try:
        await db.execute("SELECT 1")
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

**Setup references:**
- Betterstack: https://betterstack.com/uptime
- Sentry Python: https://docs.sentry.io/platforms/python/integrations/fastapi/
- Sentry Next.js: https://docs.sentry.io/platforms/javascript/guides/nextjs/

---

## 9. Logging

### Phase 1 (Launch): Docker Native Logging

Keep it simple — Docker's `json-file` driver with log rotation.

```yaml
# docker-compose.yml — add to each service
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "5"
```

**Access logs:**

```bash
# Follow all service logs
docker compose logs -f

# Filter by service
docker compose logs -f ingestion-api

# Search for errors
docker compose logs ingestion-api 2>&1 | grep "ERROR"
```

### Phase 2 (Post-Launch): Structured Logging

When `grep` isn't enough, add **Vector** (free, by Datadog) to ship logs to a local **Loki** instance, queryable via Grafana.

**Setup references:**
- Docker logging drivers: https://docs.docker.com/engine/logging/configure/
- Vector: https://vector.dev/docs/
- Loki + Grafana: https://grafana.com/docs/loki/latest/

---

## 10. Backups & Disaster Recovery

### Postgres: Daily pg_dump to Object Storage

```bash
#!/bin/bash
# backup-postgres.sh — run via cron daily at 3 AM UTC

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="trace_pg_backup_${TIMESTAMP}.sql.gz"

docker exec trace-postgres pg_dump -U trace trace_db | gzip > /tmp/${BACKUP_FILE}

# Upload to Hetzner Object Storage (S3-compatible)
aws s3 cp /tmp/${BACKUP_FILE} s3://trace-backups/postgres/${BACKUP_FILE} \
  --endpoint-url https://fsn1.your-objectstorage.com

# Retain last 30 days
aws s3 ls s3://trace-backups/postgres/ --endpoint-url https://fsn1.your-objectstorage.com \
  | awk '{print $4}' | head -n -30 | while read file; do
    aws s3 rm "s3://trace-backups/postgres/$file" --endpoint-url https://fsn1.your-objectstorage.com
  done

rm /tmp/${BACKUP_FILE}
```

```bash
# Crontab entry
0 3 * * * /opt/trace/backup-postgres.sh >> /var/log/trace-backup.log 2>&1
```

### Redis: RDB Snapshots

```yaml
# redis.conf
save 900 1       # snapshot if 1 key changed in 15 min
save 300 10      # snapshot if 10 keys changed in 5 min
save 60 10000    # snapshot if 10k keys changed in 1 min
```

Redis data is ephemeral — loss means pending attribution jobs are re-queued from Postgres, not data loss.

### Restore Testing

**Schedule a monthly restore drill.** Untested backups are not backups.

```bash
# Test restore process
gunzip -c trace_pg_backup_YYYYMMDD.sql.gz | docker exec -i trace-postgres psql -U trace trace_db
```

### Config Backups

Store `.env`, `nginx.conf`, `docker-compose.yml`, and all config files in a **private GitHub repo**. This is your infrastructure-as-code — if the VPS dies, you should be able to rebuild from scratch in under an hour.

**Setup references:**
- Hetzner Object Storage: https://docs.hetzner.com/storage/object-storage
- pg_dump documentation: https://www.postgresql.org/docs/current/app-pgdump.html
- Redis persistence: https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/

---

## 11. Rate Limiting & Abuse Prevention

### Layer 1: Cloudflare (Edge)

Cloudflare free tier includes basic rate limiting via WAF rules. Create a rule for `api.usetrace.dev/v1/traces` — limit to 200 requests/minute per IP.

### Layer 2: Application (FastAPI)

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_api_key_from_header)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/v1/traces")
@limiter.limit("100/minute")    # per API key
async def ingest_trace(...):
    ...

@app.post("/v1/auth/login")
@limiter.limit("5/minute")      # brute force protection
async def login(...):
    ...
```

### Layer 3: Nginx

```nginx
# nginx.conf
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

server {
    location /v1/traces {
        limit_req zone=api burst=50 nodelay;
        proxy_pass http://ingestion-api:8000;
    }
}
```

**Setup references:**
- SlowAPI (FastAPI rate limiting): https://github.com/laurentS/slowapi
- Nginx rate limiting: https://www.nginx.com/blog/rate-limiting-nginx/
- Cloudflare WAF rules: https://developers.cloudflare.com/waf/rate-limiting-rules/

---

## 12. PII Redaction

### Implementation: Microsoft Presidio

```bash
pip install presidio-analyzer presidio-anonymizer
```

### Phase 1 (Launch): Regex-Based Detection Only

High accuracy, low false positives on technical text. Skip NLP-based name detection initially.

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# Only high-confidence regex-based entities
SAFE_ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "US_SSN",
    "IBAN_CODE",
]

def redact_text(text: str) -> str:
    results = analyzer.analyze(
        text=text,
        language="en",
        entities=SAFE_ENTITIES,
        score_threshold=0.7
    )
    return anonymizer.anonymize(text=text, analyzer_results=results).text

def redact_trace(trace: dict) -> dict:
    redacted = {}
    for key, value in trace.items():
        if isinstance(value, str):
            redacted[key] = redact_text(value)
        elif isinstance(value, dict):
            redacted[key] = redact_trace(value)
        elif isinstance(value, list):
            redacted[key] = [
                redact_trace(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value
    return redacted
```

### Pipeline Integration

```
Raw trace → Attribution engine (full data, in memory)
         → Redact trace (Presidio)
         → Store redacted trace + attribution scores to Postgres
         → PII never hits disk unencrypted
```

### Configuration

```bash
# .env
TRACE_PII_MODE=redact_after_scoring    # default — full accuracy, store redacted
# TRACE_PII_MODE=redact_before_scoring # stricter, ~5-10% accuracy loss
# TRACE_PII_MODE=none                  # self-hosted users who don't need redaction
```

**Setup references:**
- Presidio quickstart: https://microsoft.github.io/presidio/getting_started/
- Presidio supported entities: https://microsoft.github.io/presidio/supported_entities/
- Presidio customization: https://microsoft.github.io/presidio/analyzer/adding_recognizers/

---

## 13. CI/CD Pipeline

### GitHub Actions: Deploy on Push to Main

```yaml
# .github/workflows/deploy.yml
name: Deploy to Hetzner

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Hetzner
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.HETZNER_HOST }}
          username: root
          key: ${{ secrets.HETZNER_SSH_KEY }}
          script: |
            cd /opt/trace
            git pull origin main
            docker compose build --no-cache
            docker compose up -d
            docker system prune -f
```

### Pre-Deploy Checks

Add to CI pipeline:
- `pytest` — unit + integration tests
- `ruff check` — Python linting
- `ruff format --check` — code formatting
- Health check after deploy (curl `/health` endpoint, fail pipeline if unhealthy)

**Setup references:**
- GitHub Actions: https://docs.github.com/en/actions/quickstart
- appleboy/ssh-action: https://github.com/appleboy/ssh-action
- Docker Compose in CI: https://docs.docker.com/compose/how-tos/use-compose-in-production/

---

## 14. Legal Pages

### Must-Have Before First User

| Page | Purpose | How to Create |
|------|---------|---------------|
| **Privacy Policy** | What data you collect, PII handling, GDPR rights | Iubenda ($27/yr) or adapt OSS template |
| **Terms of Service** | Liability, acceptable use, data ownership | Adapt from OSS template |
| **Cookie Policy** | If using analytics or tracking | Bundled with Iubenda |

**Key clauses for Trace specifically:**
- Users own their trace data — Trace is a processor, not owner
- PII handling disclosure — explain redaction pipeline
- Data deletion — users can request full data deletion
- Self-hosted data — make clear Trace has zero access to self-hosted instances

### Post-Launch (When Enterprise Customers Ask)

| Document | When Needed |
|----------|-------------|
| Data Processing Agreement (DPA) | First EU enterprise customer |
| SOC 2 Type I | Enterprise sales conversations |
| Security whitepaper | When asked "how do you handle security?" |

**Setup references:**
- Iubenda (privacy policy generator): https://www.iubenda.com
- OSS ToS templates: https://github.com/nickmessing/legal-templates
- GDPR compliance checklist: https://gdpr.eu/checklist/

---

## 15. Security Hardening

### Server Level

```bash
# On Hetzner VPS initial setup

# Disable root SSH login
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Create deploy user
adduser deploy
usermod -aG docker deploy

# SSH key only (disable password auth)
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# UFW firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (redirect to HTTPS)
ufw allow 443/tcp   # HTTPS
ufw enable

# Automatic security updates
apt install unattended-upgrades -y
dpkg-reconfigure -plow unattended-upgrades

systemctl restart sshd
```

### Application Level

- All API keys stored as bcrypt hashes in Postgres, never plaintext
- Environment variables via `.env` file, never committed to git
- Docker containers run as non-root users
- Postgres not exposed to the internet — only accessible within Docker network
- Redis bound to Docker internal network, no external port mapping

### Secrets Management

For launch, `.env` files on the server are fine. Add to `.gitignore` and back up encrypted.

Post-launch, consider:
- **Doppler** (free tier: 5 team members): centralized secrets manager
- **GitHub Actions secrets**: for CI/CD environment variables
- **SOPS** (free): encrypt secrets in git with age/GPG keys

**Setup references:**
- Hetzner server hardening: https://community.hetzner.com/tutorials/basic-cloud-config
- Docker security best practices: https://docs.docker.com/engine/security/
- UFW guide: https://www.digitalocean.com/community/tutorials/how-to-set-up-a-firewall-with-ufw-on-ubuntu

---

## 16. Scaling Path

### Current Ceiling: ~500 Paying Users on Single VPS

Estimated based on CX31 specs handling ingestion + attribution + dashboard + database on one machine.

### When to Scale (Watch These Metrics)

| Metric | Warning Threshold | Action |
|--------|-------------------|--------|
| CPU sustained | > 70% for 10+ min | Add workers or upgrade VPS |
| RAM usage | > 6 GB (of 8 GB) | Upgrade VPS or separate Postgres |
| Postgres connections | > 80 | Connection pooling (PgBouncer) |
| Disk usage | > 70% | Expand storage or archive old traces |
| Ingestion API p95 latency | > 500ms | Add API instances |
| Attribution queue depth | > 1000 pending | Add worker instances |

### Scaling Steps (In Order)

```
Step 1: Vertical scale
├── Upgrade to CX41 (8 vCPU, 16 GB, €17/mo)
└── Buys time with minimal effort

Step 2: Extract Postgres
├── Move to Neon (free tier: 0.5 GB) or Supabase (free tier: 500 MB)
├── Or managed Postgres on separate Hetzner VPS
└── Frees RAM/CPU on primary VPS for API + worker

Step 3: Extract attribution worker
├── Dedicated VPS (CX21, €4.50/mo)
├── Can scale horizontally — add more workers
└── Connect to shared Postgres + Redis

Step 4: Horizontal API scaling
├── Multiple ingestion API instances behind Hetzner Load Balancer (€5.39/mo)
├── Add read replicas for dashboard API
└── At this point, consider Kubernetes (but resist as long as possible)
```

---

## 17. Cost Summary

### Launch Month

| Item | Monthly Cost |
|------|-------------|
| Hetzner CX31 | €11.00 |
| Hetzner Object Storage | ~€1.00 |
| Cloudflare (free tier) | €0 |
| Resend (free tier) | €0 |
| Clerk (free tier) | €0 |
| Betterstack (free tier) | €0 |
| Sentry (free tier) | €0 |
| Lemon Squeezy (no monthly fee) | €0 |
| Domain (.dev) | ~€1.00 (amortized) |
| **Total** | **~€13/mo** |

### At 500 Users

| Item | Monthly Cost |
|------|-------------|
| Hetzner CX41 + CX21 (worker) | €21.50 |
| Hetzner Load Balancer | €5.39 |
| Hetzner Object Storage | ~€3.00 |
| Cloudflare Pro (WAF) | €20.00 |
| Resend (paid tier) | ~€20.00 |
| Clerk (paid tier, if >10k MAU) | ~€25.00 |
| Sentry (paid, if >5k events) | ~€26.00 |
| **Total** | **~€120/mo** |

---

## 18. Pre-Launch Checklist

### Must Have (Before First User) — ~2 Days

- [ ] Hetzner VPS provisioned and hardened (SSH keys, UFW, non-root user)
- [ ] Docker + Docker Compose installed
- [ ] Domain registered, DNS on Cloudflare
- [ ] SSL configured (Cloudflare proxy or Certbot)
- [ ] All services running via `docker-compose.yml`
- [ ] Health check endpoints on both APIs (`/health`)
- [ ] Transactional email (Resend) configured with DNS records
- [ ] Authentication (Clerk or Auth.js) integrated
- [ ] Rate limiting on ingestion API (SlowAPI + Nginx)
- [ ] PII redaction (Presidio, regex-only mode) in attribution worker
- [ ] Privacy Policy + Terms of Service pages live
- [ ] Basic documentation (quickstart + SDK reference) on Mintlify
- [ ] GitHub Actions CI/CD deploying on push to main
- [ ] Postgres backup cron job running
- [ ] Uptime monitoring (Betterstack) on `/health` endpoints
- [ ] `.env` and configs backed up to private repo

### Should Have (First Week) — ~1 Day

- [ ] Billing integration (Lemon Squeezy checkout + webhooks)
- [ ] Error tracking (Sentry) on all services
- [ ] Status page live at `status.usetrace.dev`
- [ ] Business email (`sanyam@usetrace.dev`) forwarding
- [ ] Docker log rotation configured
- [ ] Backup restore tested successfully
- [ ] Hetzner VPS snapshot taken as baseline

### Can Wait (Post-Launch)

- [ ] NLP-based PII name detection (Presidio + spaCy)
- [ ] Structured logging (Vector + Loki + Grafana)
- [ ] DPA template for enterprise customers
- [ ] SOC 2 preparation
- [ ] Business entity registration (LLP/Pvt Ltd)
- [ ] Stripe migration from Lemon Squeezy
- [ ] Multi-region deployment
- [ ] Read replicas for dashboard API
---

## 12. Security & Privacy

### API Key Security

- API keys are generated as `trace_live_` + 32 random bytes (base58 encoded)
- Only the bcrypt hash is stored in the database
- Keys shown to user exactly once at creation
- Automatic rotation reminders every 90 days

### Data Transmission

- All API communication over TLS 1.3
- SDK verifies SSL certificates (no skip-verify option in production)
- Spans transmitted in batches to reduce connection overhead

### PII Scrubbing

Applied client-side before transmission AND server-side as defense in depth.

Patterns scrubbed:
- Email addresses: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`
- Phone numbers: `\b[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}\b`
- Credit cards: `\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b`
- SSNs: `\b(?!219-09-9999|078-05-1120)(?!666|000|9\d{2})\d{3}-(?!00)\d{2}-(?!0{4})\d{4}\b`
- API keys: common patterns (`sk-`, `AKIA`, `Bearer `, etc.)

Scrubbed values replaced with `[REDACTED:type]`.

### Data Isolation

Each user's data is isolated at the database level via `user_id` foreign key on every table. All queries include `WHERE user_id = :current_user_id`. No cross-user data access is possible via the API.

### Retention and Deletion

Hobby tier: 7 days automatic deletion via Postgres partitioning by `started_at`.
Team tier: 30 days.
Enterprise tier: configurable, up to 90 days.

User account deletion: all spans, traces, segments, and baselines hard-deleted within 24 hours. API keys revoked immediately.

---

## 13. Pricing & Monetization

### Tier Structure

| | Hobby | Team | Enterprise |
|---|---|---|---|
| **Price** | Free | $49/mo | $299/mo |
| **Spans/month** | 10,000 | 500,000 | Unlimited |
| **Retention** | 7 days | 30 days | 90 days |
| **Users** | 1 | 10 | Unlimited |
| **Attribution** | Approximation | Full (logprob delta) | Full + Deep |
| **Alerts** | — | Slack | Slack + PagerDuty + custom webhook |
| **SSO** | — | — | SAML via WorkOS |
| **Self-hosted** | ✓ | ✓ | ✓ + SLA |
| **Support** | Community | Email (48h SLA) | Dedicated Slack |

### Stripe Integration

- Stripe Checkout for upgrade flow (no custom payment UI in v1)
- Stripe Webhooks for subscription lifecycle events
- Usage metering via Stripe Meters for span count
- Upgrade nudge appears in dashboard at 80% of plan limit

### Unit Economics (Target: Month 3)

```
100 paying teams × $49/mo  = $4,900 MRR
  5 enterprise       × $299/mo = $1,495 MRR
                               = $6,395 MRR

Infrastructure costs:
  Hetzner VPS (2×)          = $40
  LLM API costs (attribution)= $200 (estimated)
  Vercel (dashboard hosting) = $20
  Other (domains, email)     = $20
                               = $280/mo

Gross margin: ~96%
```

---

## 14. Launch Plan

### Pre-launch (Days 1–8)

3 beta users recruited from personal network. Goal: verify the 5-minute setup claim holds for someone who isn't you.

Feedback collection: 30-minute screen-share session. Watch them set up Trace on their own project. Note every moment of confusion.

### Launch Day (Day 9)

**Show HN post title:** "Show HN: Trace – I kept asking 'why did it say that?' so I built a causal debugger for LLM apps"

**Post body structure:**
- The problem in two sentences
- One code snippet (the decorator)
- The RAG hallucination demo video embedded
- What makes it different from LangSmith (one paragraph, honest)
- Self-hosted option available
- Looking for feedback, not just users

**Timing:** Tuesday or Wednesday, 9am ET.

**Twitter thread:** same day, targeting AI engineering community. Tag Latent Space, AI Engineer accounts.

### Post-launch (Weeks 2–4)

- Respond to every comment on HN within 2 hours
- DM every GitHub star who has a bio mentioning AI engineering
- Write the technical attribution blog post: "How we compute which prompt segment caused a hallucination"
- Submit to: Hacker Newsletter, TLDR AI, The Batch

---

## 15. Success Metrics

### Week 1 (Post-launch)

- GitHub stars: 300+
- HN upvotes: 100+
- Signups: 75+
- Setup success rate (user completes first trace): >60%

### Month 1

- Active weekly users: 100+
- Paying customers: 5+
- MRR: $245+
- Mean time to first trace (new user): <8 minutes
- Churn: <20%

### Month 3

- Paying teams: 50+
- MRR: $2,500+
- GitHub stars: 1,500+
- Integration count (LangChain, LlamaIndex, etc.): 5+
- P50 setup time: <5 minutes

### The Single Most Important Metric

**Time from signup to first "oh" moment** — the moment a user sees the attribution heatmap on their own trace for the first time. Target: under 8 minutes. If this takes longer than 15 minutes, something is wrong with onboarding and everything else suffers.

---

*Trace — because "why did it say that?" shouldn't take an hour to answer.*