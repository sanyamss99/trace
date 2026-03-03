# usetrace

Lightweight tracing SDK for LLM applications. Add `@tracer.observe()` to your functions and get full visibility into execution traces, token usage, and latency — with zero impact on your application.

## Install

```bash
pip install usetrace
# or
uv add usetrace
```

## Quick start

```python
from usetrace import Trace

tracer = Trace(api_key="your-key", base_url="https://your-trace-server.com")

@tracer.observe(span_type="llm", model="gpt-4o")
def ask(prompt: str) -> str:
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return response

@tracer.observe(span_type="chain")
def pipeline(question: str) -> dict:
    answer = ask(question)          # captured as child span
    summary = ask(f"Summarize: {answer}")  # captured as child span
    return {"answer": answer, "summary": summary}
```

Nested `@observe()` calls automatically build parent-child span trees. LLM responses are parsed to extract token counts, completion text, and logprobs across OpenAI, Anthropic, Gemini, and other providers.

## Features

- Sync and async function support (auto-detected)
- Parent-child span linking via `contextvars` (async-safe)
- Multi-vendor LLM response extraction (OpenAI, Anthropic, Gemini, Ollama, Together, xAI)
- Memory-bounded buffer with configurable ceiling
- Background flush with hybrid strategy (span count OR timer)
- Fire-and-forget delivery — never blocks your application

## Configuration

```python
tracer = Trace(
    api_key="your-key",
    base_url="https://your-trace-server.com",
    environment="production",
    flush_interval=5.0,         # seconds between flushes
    batch_size=50,              # max spans per batch
    max_buffer_bytes=10*1024*1024,  # 10 MB buffer ceiling
)
```

## License

Apache 2.0
