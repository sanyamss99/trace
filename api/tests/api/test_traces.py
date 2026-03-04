"""Tests for GET /traces and GET /traces/:id endpoints."""

import pytest
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


# ---------------------------------------------------------------------------
# Date range filtering tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_traces_started_after(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """started_after filters out older traces."""
    raw_key, _ = create_api_key
    spans = [
        _make_span_payload(
            trace_id="old_t",
            span_id="old_s",
            start_time="2026-01-01T00:00:00+00:00",
            end_time="2026-01-01T00:00:01+00:00",
        ),
        _make_span_payload(
            trace_id="new_t",
            span_id="new_s",
            start_time="2026-03-01T00:00:00+00:00",
            end_time="2026-03-01T00:00:01+00:00",
        ),
    ]
    await client.post("/ingest/batch", json=spans, headers={"X-Trace-Key": raw_key})

    response = await client.get(
        "/traces",
        params={"started_after": "2026-02-01T00:00:00"},
        headers={"X-Trace-Key": raw_key},
    )
    data = response.json()
    assert len(data["traces"]) == 1
    assert data["traces"][0]["id"] == "new_t"


@pytest.mark.asyncio
async def test_list_traces_started_before(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """started_before filters out newer traces."""
    raw_key, _ = create_api_key
    spans = [
        _make_span_payload(
            trace_id="early_t",
            span_id="early_s",
            start_time="2026-01-15T00:00:00+00:00",
            end_time="2026-01-15T00:00:01+00:00",
        ),
        _make_span_payload(
            trace_id="late_t",
            span_id="late_s",
            start_time="2026-03-15T00:00:00+00:00",
            end_time="2026-03-15T00:00:01+00:00",
        ),
    ]
    await client.post("/ingest/batch", json=spans, headers={"X-Trace-Key": raw_key})

    response = await client.get(
        "/traces",
        params={"started_before": "2026-02-01T00:00:00"},
        headers={"X-Trace-Key": raw_key},
    )
    data = response.json()
    assert len(data["traces"]) == 1
    assert data["traces"][0]["id"] == "early_t"


@pytest.mark.asyncio
async def test_list_traces_date_range(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Combining started_after and started_before gives a time window."""
    raw_key, _ = create_api_key
    spans = [
        _make_span_payload(
            trace_id="jan_t",
            span_id="jan_s",
            start_time="2026-01-10T00:00:00+00:00",
            end_time="2026-01-10T00:00:01+00:00",
        ),
        _make_span_payload(
            trace_id="feb_t",
            span_id="feb_s",
            start_time="2026-02-15T00:00:00+00:00",
            end_time="2026-02-15T00:00:01+00:00",
        ),
        _make_span_payload(
            trace_id="mar_t",
            span_id="mar_s",
            start_time="2026-03-20T00:00:00+00:00",
            end_time="2026-03-20T00:00:01+00:00",
        ),
    ]
    await client.post("/ingest/batch", json=spans, headers={"X-Trace-Key": raw_key})

    response = await client.get(
        "/traces",
        params={
            "started_after": "2026-02-01T00:00:00",
            "started_before": "2026-03-01T00:00:00",
        },
        headers={"X-Trace-Key": raw_key},
    )
    data = response.json()
    assert len(data["traces"]) == 1
    assert data["traces"][0]["id"] == "feb_t"


# ---------------------------------------------------------------------------
# Cost computation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_span_has_cost_after_ingest(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Ingesting an LLM span with known model populates cost_usd."""
    raw_key, _ = create_api_key
    await client.post(
        "/ingest/batch",
        json=[
            _make_span_payload(
                trace_id="cost_trace",
                span_id="cost_span",
                model="gpt-4o-mini",
                prompt_tokens=1000,
                completion_tokens=500,
            )
        ],
        headers={"X-Trace-Key": raw_key},
    )

    response = await client.get("/traces/spans/cost_span", headers={"X-Trace-Key": raw_key})
    assert response.status_code == 200
    data = response.json()
    assert data["cost_usd"] is not None
    assert data["cost_usd"] > 0


@pytest.mark.asyncio
async def test_trace_has_total_cost(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Trace aggregates cost from child spans."""
    raw_key, _ = create_api_key
    await client.post(
        "/ingest/batch",
        json=[
            _make_span_payload(
                trace_id="tc_trace",
                span_id="tc_s1",
                model="gpt-4o-mini",
                prompt_tokens=1000,
                completion_tokens=500,
            ),
            _make_span_payload(
                trace_id="tc_trace",
                span_id="tc_s2",
                parent_span_id="tc_s1",
                model="gpt-4o-mini",
                prompt_tokens=2000,
                completion_tokens=1000,
            ),
        ],
        headers={"X-Trace-Key": raw_key},
    )

    response = await client.get("/traces", headers={"X-Trace-Key": raw_key})
    data = response.json()
    trace = next(t for t in data["traces"] if t["id"] == "tc_trace")
    assert trace["total_cost_usd"] is not None
    assert trace["total_cost_usd"] > 0


# ---------------------------------------------------------------------------
# Cost-by-function analytics tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_by_function(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """GET /traces/analytics/cost-by-function returns per-function aggregates."""
    raw_key, _ = create_api_key
    await client.post(
        "/ingest/batch",
        json=[
            _make_span_payload(
                trace_id="cbf_t1",
                span_id="cbf_s1",
                function_name="mod.func_a",
                model="gpt-4o-mini",
                prompt_tokens=1000,
                completion_tokens=500,
            ),
            _make_span_payload(
                trace_id="cbf_t2",
                span_id="cbf_s2",
                function_name="mod.func_a",
                model="gpt-4o-mini",
                prompt_tokens=2000,
                completion_tokens=1000,
            ),
            _make_span_payload(
                trace_id="cbf_t3",
                span_id="cbf_s3",
                function_name="mod.func_b",
                model="gpt-4o-mini",
                prompt_tokens=500,
                completion_tokens=200,
            ),
        ],
        headers={"X-Trace-Key": raw_key},
    )

    response = await client.get(
        "/traces/analytics/cost-by-function",
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Ordered by total_cost_usd desc — func_a has more calls
    assert data[0]["function_name"] == "mod.func_a"
    assert data[0]["call_count"] == 2
    assert data[0]["total_cost_usd"] > 0
    assert data[0]["avg_cost_usd"] > 0
    assert data[0]["avg_duration_ms"] is not None
    assert data[0]["error_count"] == 0
    assert data[1]["function_name"] == "mod.func_b"
    assert data[1]["call_count"] == 1


@pytest.mark.asyncio
async def test_cost_by_function_empty(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Empty org returns empty list."""
    raw_key, _ = create_api_key
    response = await client.get(
        "/traces/analytics/cost-by-function",
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_cost_by_function_unauthenticated(client: AsyncClient) -> None:
    """GET /traces/analytics/cost-by-function without API key returns 401."""
    response = await client.get("/traces/analytics/cost-by-function")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Overview stats tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overview_stats_empty(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Empty org returns zero counts."""
    raw_key, _ = create_api_key
    response = await client.get(
        "/traces/analytics/overview",
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trace_count"] == 0
    assert data["error_count"] == 0
    assert data["error_rate"] == 0.0


@pytest.mark.asyncio
async def test_overview_stats_with_data(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Overview stats reflect ingested traces."""
    raw_key, _ = create_api_key
    await client.post(
        "/ingest/batch",
        json=[
            _make_span_payload(
                trace_id="ov_t1",
                span_id="ov_s1",
                model="gpt-4o-mini",
                prompt_tokens=1000,
                completion_tokens=500,
            ),
            _make_span_payload(
                trace_id="ov_t2",
                span_id="ov_s2",
                status="error",
                error_message="boom",
            ),
        ],
        headers={"X-Trace-Key": raw_key},
    )

    response = await client.get(
        "/traces/analytics/overview",
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trace_count"] == 2
    assert data["error_count"] == 1
    assert data["error_rate"] == 0.5
    assert data["avg_duration_ms"] is not None


@pytest.mark.asyncio
async def test_overview_stats_unauthenticated(client: AsyncClient) -> None:
    """GET /traces/analytics/overview without API key returns 401."""
    response = await client.get("/traces/analytics/overview")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Time-series tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeseries_empty(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Empty org returns empty list."""
    raw_key, _ = create_api_key
    response = await client.get(
        "/traces/analytics/timeseries",
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_timeseries_groups_by_day(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Traces on different days produce separate data points."""
    raw_key, _ = create_api_key
    await client.post(
        "/ingest/batch",
        json=[
            _make_span_payload(
                trace_id="ts_t1",
                span_id="ts_s1",
                start_time="2026-03-01T10:00:00+00:00",
                end_time="2026-03-01T10:00:01+00:00",
            ),
            _make_span_payload(
                trace_id="ts_t2",
                span_id="ts_s2",
                start_time="2026-03-01T14:00:00+00:00",
                end_time="2026-03-01T14:00:01+00:00",
            ),
            _make_span_payload(
                trace_id="ts_t3",
                span_id="ts_s3",
                start_time="2026-03-02T10:00:00+00:00",
                end_time="2026-03-02T10:00:01+00:00",
                status="error",
                error_message="fail",
            ),
        ],
        headers={"X-Trace-Key": raw_key},
    )

    response = await client.get(
        "/traces/analytics/timeseries",
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # First day: 2 traces, 0 errors
    assert data[0]["trace_count"] == 2
    assert data[0]["error_count"] == 0
    # Second day: 1 trace, 1 error
    assert data[1]["trace_count"] == 1
    assert data[1]["error_count"] == 1


@pytest.mark.asyncio
async def test_timeseries_unauthenticated(client: AsyncClient) -> None:
    """GET /traces/analytics/timeseries without API key returns 401."""
    response = await client.get("/traces/analytics/timeseries")
    assert response.status_code == 401
