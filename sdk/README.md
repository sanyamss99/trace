# usetrace

Lightweight tracing SDK for LLM applications. Add `@tracer.observe()` to your functions and get visual attribution maps that answer **"Why did the LLM say that?"**

## Install

```bash
pip install usetrace
```

## Quick Start

```python
import openai
from usetrace import Trace

tracer = Trace(api_key="tr-...", base_url="https://api.use-trace.com")
client = openai.OpenAI()


@tracer.observe(span_type="retrieval", tags={"source": "pinecone"})
def retrieve_context(query: str) -> str:
    """Fetch relevant documents for the query."""
    results = pinecone_index.query(vector=embed(query), top_k=5)
    return "\n".join(match.metadata["text"] for match in results.matches)


@tracer.observe(span_type="llm", model="gpt-4o")
def generate_answer(question: str, context: str) -> str:
    """Call the LLM with retrieved context."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"Answer using this context:\n{context}"},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


@tracer.observe(span_type="chain", tags={"pattern": "rag"})
def rag_pipeline(question: str) -> str:
    """Full RAG pipeline — retrieve then generate."""
    context = retrieve_context(question)
    return generate_answer(question, context)


answer = rag_pipeline("How does attention work in Transformers?")
```

Every traced call is captured — inputs, outputs, latency, token usage — and sent to the Trace dashboard where you can inspect the full execution tree and per-token attribution maps. The example above produces a three-level trace: `rag_pipeline` → `retrieve_context` + `generate_answer`.

## Configuration

Create a `Trace` instance once at application startup. All parameters are optional.

```python
tracer = Trace(
    api_key="tr-...",
    base_url="https://api.use-trace.com",
    environment="production",
    flush_interval=2.0,
    batch_size=100,
)
```

| Param | Type | Default | Description |
|---|---|---|---|
| `api_key` | `str` | `""` | API key for authenticating with the Trace backend. Get yours from the dashboard. |
| `base_url` | `str` | `"http://localhost:8000"` | URL of the Trace API. Use `https://api.use-trace.com` for hosted, or your own URL for self-hosted. |
| `environment` | `str` | `"development"` | Tags every span with the environment name. Use to filter traces by dev/staging/prod in the dashboard. |
| `enabled` | `bool` | `True` | Master switch. Set `False` to completely disable tracing — zero overhead, no background threads, decorated functions run as-is. |
| `flush_interval` | `float` | `5.0` | How often (seconds) the background worker sends buffered spans to the API. Lower = fresher data, higher = fewer HTTP calls. |
| `batch_size` | `int` | `50` | Max spans sent per HTTP request. Balances payload size vs request count. |
| `max_buffer_bytes` | `int` | `10485760` (10 MB) | Memory cap for the span buffer. When full, oldest spans are dropped. Prevents runaway memory in high-throughput apps. |
| `max_string_length` | `int \| None` | `None` (auto) | Truncation limit for captured input/output strings. Auto-scales between 500–50,000 chars based on buffer size. Set explicitly for predictable behavior. |
| `flush_threshold` | `int \| None` | `None` (same as `batch_size`) | Number of buffered spans that triggers an early flush before the interval timer fires. Useful for bursty workloads. |

## Decorator

Use `@tracer.observe()` on any function — sync or async — to record it as a span.

```python
@tracer.observe(span_type="llm", model="gpt-4o")
def call_llm(prompt: str) -> str:
    ...
```

| Param | Type | Default | Description |
|---|---|---|---|
| `span_type` | `str` | `"generic"` | Categorizes the span. Use `"llm"` for model calls (enables auto-extraction of tokens, logprobs, prompt text), `"retrieval"` for search/RAG, `"tool"` for tool calls, or any custom string. |
| `model` | `str \| None` | `None` | Model name (e.g. `"gpt-4o"`, `"claude-sonnet-4-20250514"`). For `span_type="llm"`, auto-detected from the response if not set. |
| `capture_input` | `bool` | `True` | Capture function arguments. Set `False` for functions with sensitive inputs (PII, credentials). |
| `capture_output` | `bool` | `True` | Capture return value. Set `False` for large responses or sensitive data. |
| `tags` | `dict[str, str] \| None` | `None` | Custom key-value metadata attached to the span. Use for filtering in the dashboard (e.g. `{"customer": "acme", "version": "v2"}`). |

## Methods

### `tracer.flush()`

Forces immediate send of buffered spans. Essential for serverless environments (Lambda, Cloud Functions) where the process may exit before the background flush timer fires.

```python
tracer.flush()
```

### `tracer.shutdown()`

Stops the background worker thread and drains remaining spans. Called automatically via `atexit`, but call explicitly if you need to guarantee delivery before process exit.

```python
tracer.shutdown()
```

### `tracer.stats`

Returns a `TraceStats` object with two fields:

- `pending_bytes` — current buffer usage in bytes
- `dropped_spans` — count of spans dropped due to buffer overflow

Useful for monitoring SDK health in long-running services.

```python
stats = tracer.stats
print(f"Buffer: {stats.pending_bytes} bytes, dropped: {stats.dropped_spans}")
```

## Examples

### Async functions

The decorator auto-detects async functions — no extra configuration needed.

```python
@tracer.observe(span_type="llm", model="gpt-4o")
async def call_llm(prompt: str) -> str:
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
```

### Disabling input capture for sensitive data

```python
@tracer.observe(span_type="tool", capture_input=False)
def lookup_user(ssn: str) -> dict:
    """SSN is never sent to the Trace backend."""
    return db.query(ssn)
```

### Custom tags

```python
@tracer.observe(
    span_type="llm",
    model="gpt-4o",
    tags={"customer": "acme", "experiment": "v2-prompt"},
)
def generate_summary(text: str) -> str:
    ...
```

### Serverless / Lambda flush pattern

```python
from usetrace import Trace

tracer = Trace(api_key="tr-...", base_url="https://api.use-trace.com")

@tracer.observe(span_type="llm", model="gpt-4o")
def call_llm(prompt: str) -> str:
    ...

def handler(event, context):
    result = call_llm(event["prompt"])
    tracer.flush()  # send spans before the process freezes
    return {"body": result}
```

## Dashboard

Sign up and explore your traces at [use-trace.com](https://use-trace.com).

## License

Apache-2.0
