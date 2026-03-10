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

## Quick Start

### Install

### Instrument your code

### View your traces

## Examples

### OpenAI

### Anthropic

### RAG Pipeline

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
- [x] Multi-vendor LLM support (OpenAI, Anthropic)
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
