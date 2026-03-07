# usetrace

Lightweight tracing SDK for LLM applications. Add `@tracer.observe()` to your functions and get visual attribution maps that answer **"Why did the LLM say that?"**

## Install

```bash
pip install usetrace
```

## Quick Start

```python
from usetrace import Trace

tracer = Trace(api_key="your-key", base_url="https://api.use-trace.com")

@tracer.observe(span_type="llm", model="gpt-4o")
def my_llm_function(prompt: str) -> str:
    return openai.chat.completions.create(...)
```

Every traced call is captured — inputs, outputs, latency, token usage — and sent to the Trace dashboard where you can inspect full execution trees and per-token attribution maps.

## Dashboard

Sign up and explore your traces at [use-trace.com](https://use-trace.com).

## License

Apache-2.0
