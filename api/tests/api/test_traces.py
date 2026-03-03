"""Tests for GET /traces and GET /traces/:id endpoints."""

from httpx import AsyncClient


def _make_span_payload(**overrides: object) -> dict:
    """Build a minimal valid span payload dict."""
    base: dict = {
        "trace_id": "aaaa1111bbbb2222cccc3333dddd4444",
        "span_id": "1111aaaa2222bbbb3333cccc4444dddd",
        "parent_span_id": None,
        "span_type": "llm",
        "function_name": "my_module.call_llm",
        "module": "my_module",
        "start_time": "2026-03-01T00:00:00+00:00",
        "end_time": "2026-03-01T00:00:01+00:00",
        "duration_ms": 1000.0,
        "status": "ok",
        "model": "gpt-4o",
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "environment": "test",
    }
    base.update(overrides)
    return base


async def test_list_traces_empty(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Empty org should return empty list."""
    raw_key, _ = create_api_key
    response = await client.get("/traces", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 200
    data = response.json()
    assert data["traces"] == []
    assert data["total"] == 0


async def test_list_traces_after_ingest(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """After ingesting spans, the trace should appear in the list."""
    raw_key, _ = create_api_key
    await client.post(
        "/ingest/batch",
        json=[_make_span_payload()],
        headers={"X-Trace-Key": raw_key},
    )

    response = await client.get("/traces", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["traces"][0]["function_name"] == "my_module.call_llm"
    assert data["traces"][0]["span_count"] == 1


async def test_list_traces_filter_by_status(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Filter by status should return matching traces only."""
    raw_key, _ = create_api_key
    await client.post(
        "/ingest/batch",
        json=[
            _make_span_payload(trace_id="t1", span_id="s1", status="ok"),
            _make_span_payload(trace_id="t2", span_id="s2", status="error", error_message="boom"),
        ],
        headers={"X-Trace-Key": raw_key},
    )

    response = await client.get(
        "/traces", params={"status": "error"}, headers={"X-Trace-Key": raw_key}
    )
    data = response.json()
    assert data["total"] == 1
    assert data["traces"][0]["status"] == "error"


async def test_list_traces_pagination(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Pagination params should be respected."""
    raw_key, _ = create_api_key
    spans = [_make_span_payload(trace_id=f"t{i}", span_id=f"s{i}") for i in range(3)]
    await client.post("/ingest/batch", json=spans, headers={"X-Trace-Key": raw_key})

    response = await client.get(
        "/traces",
        params={"page": 1, "page_size": 2},
        headers={"X-Trace-Key": raw_key},
    )
    data = response.json()
    assert len(data["traces"]) == 2
    assert data["total"] == 3
    assert data["has_more"] is True


async def test_get_trace_detail(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """GET /traces/:id should return trace with spans."""
    raw_key, _ = create_api_key
    trace_id = "detail_trace"
    await client.post(
        "/ingest/batch",
        json=[
            _make_span_payload(trace_id=trace_id, span_id="root", parent_span_id=None),
            _make_span_payload(trace_id=trace_id, span_id="child", parent_span_id="root"),
        ],
        headers={"X-Trace-Key": raw_key},
    )

    response = await client.get(f"/traces/{trace_id}", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == trace_id
    assert len(data["spans"]) == 2


async def test_get_trace_not_found(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """GET /traces/:id for missing trace should return 404."""
    raw_key, _ = create_api_key
    response = await client.get("/traces/nonexistent", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 404


async def test_get_span_by_id(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """GET /traces/spans/:span_id should return the span."""
    raw_key, _ = create_api_key
    await client.post(
        "/ingest/batch",
        json=[_make_span_payload(span_id="target_span")],
        headers={"X-Trace-Key": raw_key},
    )

    response = await client.get("/traces/spans/target_span", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 200
    assert response.json()["id"] == "target_span"


async def test_get_span_not_found(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """GET /traces/spans/:span_id for missing span should return 404."""
    raw_key, _ = create_api_key
    response = await client.get("/traces/spans/nope", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 404
