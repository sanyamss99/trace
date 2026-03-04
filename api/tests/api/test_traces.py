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
    assert data["next_cursor"] is None


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
    assert len(data["traces"]) == 1
    assert data["traces"][0]["function_name"] == "my_module.call_llm"
    assert data["traces"][0]["span_count"] == 1
    assert data["next_cursor"] is None


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
    assert len(data["traces"]) == 1
    assert data["traces"][0]["status"] == "error"


async def test_list_traces_cursor_pagination(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Cursor pagination should navigate through all traces."""
    raw_key, _ = create_api_key
    spans = [
        _make_span_payload(
            trace_id=f"t{i}",
            span_id=f"s{i}",
            start_time=f"2026-03-0{i + 1}T00:00:00+00:00",
            end_time=f"2026-03-0{i + 1}T00:00:01+00:00",
        )
        for i in range(3)
    ]
    await client.post("/ingest/batch", json=spans, headers={"X-Trace-Key": raw_key})

    # First page: limit=2
    response = await client.get("/traces", params={"limit": 2}, headers={"X-Trace-Key": raw_key})
    data = response.json()
    assert len(data["traces"]) == 2
    assert data["next_cursor"] is not None

    # Second page: use next_cursor
    response = await client.get(
        "/traces",
        params={"limit": 2, "cursor": data["next_cursor"]},
        headers={"X-Trace-Key": raw_key},
    )
    data = response.json()
    assert len(data["traces"]) == 1
    assert data["next_cursor"] is None


async def test_list_traces_invalid_cursor(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """A malformed cursor should return 400."""
    raw_key, _ = create_api_key
    response = await client.get(
        "/traces",
        params={"cursor": "not-a-valid-cursor"},
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 400


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


async def test_list_traces_limit_over_max(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """limit > 100 should return 422."""
    raw_key, _ = create_api_key
    response = await client.get("/traces", params={"limit": 200}, headers={"X-Trace-Key": raw_key})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Auth rejection tests (M5)
# ---------------------------------------------------------------------------


async def test_list_traces_unauthenticated(client: AsyncClient) -> None:
    """GET /traces without API key should return 401."""
    response = await client.get("/traces")
    assert response.status_code == 401


async def test_get_trace_unauthenticated(client: AsyncClient) -> None:
    """GET /traces/{id} without API key should return 401."""
    response = await client.get("/traces/some_id")
    assert response.status_code == 401


async def test_get_span_unauthenticated(client: AsyncClient) -> None:
    """GET /traces/spans/{id} without API key should return 401."""
    response = await client.get("/traces/spans/some_id")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Cross-org isolation tests (M6)
# ---------------------------------------------------------------------------


async def test_cross_org_trace_isolation(
    client: AsyncClient,
    create_api_key: tuple[str, str],
    create_second_api_key: tuple[str, str],
) -> None:
    """Org A's traces should not be visible to Org B."""
    key_a, _ = create_api_key
    key_b, _ = create_second_api_key

    # Ingest a trace under Org A
    await client.post(
        "/ingest/batch",
        json=[_make_span_payload(trace_id="org_a_trace", span_id="org_a_span")],
        headers={"X-Trace-Key": key_a},
    )

    # Org A should see it
    response = await client.get("/traces", headers={"X-Trace-Key": key_a})
    assert len(response.json()["traces"]) == 1

    # Org B should NOT see it
    response = await client.get("/traces", headers={"X-Trace-Key": key_b})
    assert len(response.json()["traces"]) == 0

    # Org B should not access Org A's trace detail
    response = await client.get("/traces/org_a_trace", headers={"X-Trace-Key": key_b})
    assert response.status_code == 404
