# Trace

[![PyPI](https://img.shields.io/pypi/v/usetrace)](https://pypi.org/project/usetrace/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![CI](https://github.com/sanyamsharma/trace/actions/workflows/ci.yml/badge.svg)](https://github.com/sanyamsharma/trace/actions)
[![Python](https://img.shields.io/pypi/pyversions/usetrace)](https://pypi.org/project/usetrace/)

> "One decorator to trace your LLM apps — understand why the model said that, with cost, latency, and attribution built
  in."

![assets/trace.png](assets/trace.png)

## Why Trace?

Your LLM app hallucinated in production. A user screenshots the wrong answer, posts it on Twitter, and your Slack lights up.

You open your logs. You see the prompt. You see the completion. You see the latency.

But you can't answer the one question everyone is asking: **"Why did it say that?"**

Was it the retrieval? Did the model ignore the right documents? Was the system prompt ambiguous? Did you stuff too much context and drown out the actual query?

You don't know. You're guessing.

**Trace answers that question.** One decorator on your functions, and you get full execution traces with per-token attribution — which parts of your prompt actually influenced the output, and which parts the model ignored.

## Demo

## How It Works

![How Trace Works](assets/trace-works.png)

## Quick Start

### Install

```bash
pip install usetrace
```

### Instrument your code

Add `@tracer.observe()` to any function you want to trace — sync or async, any LLM provider.

```python
import openai
from usetrace import Trace

tracer = Trace(api_key="tr-...", base_url="https://api.use-trace.com")
client = openai.OpenAI()


@tracer.observe(span_type="retrieval", tags={"source": "pinecone"})
def retrieve_context(query: str) -> str:
    results = pinecone_index.query(vector=embed(query), top_k=5)
    return "\n".join(match.metadata["text"] for match in results.matches)


@tracer.observe(span_type="llm", model="gpt-4o")
def generate_answer(question: str, context: str) -> str:
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
    context = retrieve_context(question)
    return generate_answer(question, context)


answer = rag_pipeline("How does attention work in Transformers?")
```

That's it. Every call is captured — inputs, outputs, latency, token usage — and sent to the Trace backend as a nested execution tree: `rag_pipeline` → `retrieve_context` + `generate_answer`.

### View your traces

Open the [Trace dashboard](https://use-trace.com) to see your execution trees and per-token attribution maps.

## Examples

### OpenAI

```python
from usetrace import Trace
import openai

tracer = Trace(api_key="tr-...", base_url="https://api.use-trace.com")
client = openai.OpenAI()


@tracer.observe(span_type="llm", model="gpt-4o")
def summarize(text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Summarize:\n{text}"}],
    )
    return response.choices[0].message.content
```

### Anthropic

```python
from usetrace import Trace
import anthropic

tracer = Trace(api_key="tr-...", base_url="https://api.use-trace.com")
client = anthropic.Anthropic()


@tracer.observe(span_type="llm", model="claude-sonnet-4-20250514")
def analyze(text: str) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"Analyze this text:\n{text}"}],
    )
    return message.content[0].text
```

### Gemini

```python
from usetrace import Trace
import google.generativeai as genai

tracer = Trace(api_key="tr-...", base_url="https://api.use-trace.com")
model = genai.GenerativeModel("gemini-2.0-flash")


@tracer.observe(span_type="llm", model="gemini-2.0-flash")
def summarize(text: str) -> str:
    response = model.generate_content(f"Summarize:\n{text}")
    return response.text
```

### RAG Pipeline

```python
from usetrace import Trace
import openai

tracer = Trace(api_key="tr-...", base_url="https://api.use-trace.com")
client = openai.OpenAI()


@tracer.observe(span_type="retrieval", tags={"source": "pg_vector"})
def search_docs(query: str) -> list[str]:
    rows = db.execute("SELECT content FROM docs ORDER BY embedding <=> %s LIMIT 5", [embed(query)])
    return [row.content for row in rows]


@tracer.observe(span_type="llm", model="gpt-4o")
def ask_with_context(question: str, docs: list[str]) -> str:
    context = "\n---\n".join(docs)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"Answer using only this context:\n{context}"},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


@tracer.observe(span_type="chain", tags={"pattern": "rag"})
def rag(question: str) -> str:
    docs = search_docs(question)
    return ask_with_context(question, docs)
```

## Provider Support

| Capability | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| Input/output capture | ✅ | ✅ | ✅ |
| Latency tracking | ✅ | ✅ | ✅ |
| Token usage | ✅ | ✅ | ✅ |
| Model auto-detection | ✅ | ✅ | ✅ |
| Logprobs | ✅ | ❌ | ✅ |
| Per-token attribution maps | ✅ | ❌ | ✅ |

**Why no attribution maps for Anthropic?** Attribution maps are built from **logprobs** (log-probabilities) — the model's confidence score for each token it generates. Trace uses these scores to compute which parts of your prompt actually influenced each output token. OpenAI exposes logprobs via `logprobs=True`, and Gemini via `response_logprobs=True`. Anthropic's Messages API does not return logprobs, so Trace cannot compute per-token attribution for Anthropic calls. Tracing still works — you get the full execution tree, inputs, outputs, latency, and token counts — but the attribution visualization is unavailable.

## Features

## Performance

## Dashboard

## Comparison

| Feature | Trace | Langfuse | LangSmith |
|---------|-------|----------|-----------|
| Open source | | | |
| Self-hostable | | | |
| Attribution maps | | | |
| SDK weight (deps) | | | |
| Decorator-based | | | |
| Async-safe | | | |

## Design Principles

## Architecture

| Component | Description |
|-----------|-------------|
| `sdk/` | |
| `api/` | |
| `frontend/` | |

## Self-Hosting

### Prerequisites

### One-Click Deploy

### Manual Setup

### Environment Variables

## SDK Reference

## Roadmap

- [x] Decorator-based tracing
- [x] Multi-vendor LLM support (OpenAI, Anthropic, Gemini)
- [x] Visual attribution maps
- [x] Async-safe span nesting
- [x] Google OAuth + API key auth
- [ ] Streaming support
- [ ] LangChain / LlamaIndex integrations
- [ ] Cost tracking per trace
- [ ] Alerting on attribution anomalies
- [ ] OpenTelemetry export

## Contributing

## Star History

## License

Apache-2.0
