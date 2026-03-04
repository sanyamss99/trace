"""Tests for POST /ingest/batch endpoint."""

from datetime import UTC, datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Span, Trace, UsageEvent
from api.services.ingest import _to_naive_utc


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


async def test_ingest_happy_path(
    client: AsyncClient,
    create_api_key: tuple[str, str],
    db_session: AsyncSession,
) -> None:
    """A valid batch should persist traces, spans, and a usage event."""
    raw_key, org_id = create_api_key
    payload = [_make_span_payload()]

    response = await client.post(
        "/ingest/batch",
        json=payload,
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["accepted"] == 1
    assert data["failed"] == 0

    # Verify trace was created
    traces = (await db_session.execute(select(Trace))).scalars().all()
    assert len(traces) == 1
    assert traces[0].org_id == org_id
    assert traces[0].function_name == "my_module.call_llm"

    # Verify span was created
    spans = (await db_session.execute(select(Span))).scalars().all()
    assert len(spans) == 1
    assert spans[0].trace_id == traces[0].id

    # Verify usage event
    events = (await db_session.execute(select(UsageEvent))).scalars().all()
    assert len(events) == 1
    assert events[0].quantity == 1


async def test_ingest_missing_api_key(client: AsyncClient) -> None:
    """Request without X-Trace-Key should return 401."""
    response = await client.post("/ingest/batch", json=[_make_span_payload()])
    assert response.status_code == 401


async def test_ingest_invalid_api_key(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Request with wrong API key should return 401."""
    response = await client.post(
        "/ingest/batch",
        json=[_make_span_payload()],
        headers={"X-Trace-Key": "tr_wrong_key"},
    )
    assert response.status_code == 401


async def test_ingest_validation_error(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Invalid span payload should return 422."""
    raw_key, _ = create_api_key
    response = await client.post(
        "/ingest/batch",
        json=[{"span_id": "abc"}],
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 422


async def test_ingest_duplicate_span_is_idempotent(
    client: AsyncClient,
    create_api_key: tuple[str, str],
    db_session: AsyncSession,
) -> None:
    """Sending the same span twice should not create duplicates."""
    raw_key, _ = create_api_key
    payload = [_make_span_payload()]

    await client.post("/ingest/batch", json=payload, headers={"X-Trace-Key": raw_key})
    await client.post("/ingest/batch", json=payload, headers={"X-Trace-Key": raw_key})

    spans = (await db_session.execute(select(Span))).scalars().all()
    assert len(spans) == 1


async def test_ingest_multi_trace_batch(
    client: AsyncClient,
    create_api_key: tuple[str, str],
    db_session: AsyncSession,
) -> None:
    """A batch with spans from different trace_ids should create multiple traces."""
    raw_key, _ = create_api_key
    payload = [
        _make_span_payload(trace_id="trace_aaa", span_id="span_1"),
        _make_span_payload(trace_id="trace_bbb", span_id="span_2"),
    ]

    response = await client.post("/ingest/batch", json=payload, headers={"X-Trace-Key": raw_key})
    assert response.json()["accepted"] == 2

    traces = (await db_session.execute(select(Trace))).scalars().all()
    assert len(traces) == 2


async def test_ingest_updates_trace_on_second_batch(
    client: AsyncClient,
    create_api_key: tuple[str, str],
    db_session: AsyncSession,
) -> None:
    """Spans arriving in a second batch for the same trace should update it."""
    raw_key, _ = create_api_key
    trace_id = "shared_trace_id"

    batch_1 = [
        _make_span_payload(
            trace_id=trace_id,
            span_id="span_1",
            start_time="2026-03-01T00:00:00+00:00",
            end_time="2026-03-01T00:00:01+00:00",
            prompt_tokens=10,
            completion_tokens=5,
        )
    ]
    batch_2 = [
        _make_span_payload(
            trace_id=trace_id,
            span_id="span_2",
            parent_span_id="span_1",
            start_time="2026-03-01T00:00:01+00:00",
            end_time="2026-03-01T00:00:03+00:00",
            prompt_tokens=20,
            completion_tokens=10,
        )
    ]

    await client.post("/ingest/batch", json=batch_1, headers={"X-Trace-Key": raw_key})
    await client.post("/ingest/batch", json=batch_2, headers={"X-Trace-Key": raw_key})

    traces = (await db_session.execute(select(Trace))).scalars().all()
    assert len(traces) == 1
    trace = traces[0]
    # Tokens should be accumulated: (10+5) + (20+10) = 45
    assert trace.total_tokens == 45


# ---------------------------------------------------------------------------
# Timezone conversion tests
# ---------------------------------------------------------------------------


def test_to_naive_utc_aware_utc() -> None:
    """Aware UTC datetime should strip tzinfo."""
    dt = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    result = _to_naive_utc(dt)
    assert result == datetime(2026, 3, 1, 12, 0, 0)
    assert result.tzinfo is None


def test_to_naive_utc_aware_non_utc() -> None:
    """Aware non-UTC datetime should convert to UTC then strip."""
    ist = timezone(timedelta(hours=5, minutes=30))
    dt = datetime(2026, 3, 1, 12, 0, 0, tzinfo=ist)
    result = _to_naive_utc(dt)
    # 12:00 IST = 06:30 UTC
    assert result == datetime(2026, 3, 1, 6, 30, 0)
    assert result.tzinfo is None


def test_to_naive_utc_naive() -> None:
    """Naive datetime should be returned as-is (assumed UTC)."""
    dt = datetime(2026, 3, 1, 12, 0, 0)
    result = _to_naive_utc(dt)
    assert result == datetime(2026, 3, 1, 12, 0, 0)
    assert result.tzinfo is None


# ---------------------------------------------------------------------------
# Edge case and hardening tests
# ---------------------------------------------------------------------------


async def test_ingest_all_null_tokens(
    client: AsyncClient,
    create_api_key: tuple[str, str],
    db_session: AsyncSession,
) -> None:
    """Spans with no token counts should produce a trace with total_tokens=None."""
    raw_key, _ = create_api_key
    payload = [
        _make_span_payload(
            span_id="no_tokens",
            prompt_tokens=None,
            completion_tokens=None,
        )
    ]
    response = await client.post("/ingest/batch", json=payload, headers={"X-Trace-Key": raw_key})
    assert response.json()["accepted"] == 1

    traces = (await db_session.execute(select(Trace))).scalars().all()
    assert traces[0].total_tokens is None


async def test_ingest_batch_too_large(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """A batch exceeding MAX_BATCH_SIZE should return 413."""
    raw_key, _ = create_api_key
    payload = [_make_span_payload(span_id=f"s{i}", trace_id=f"t{i}") for i in range(1001)]
    response = await client.post("/ingest/batch", json=payload, headers={"X-Trace-Key": raw_key})
    assert response.status_code == 413


async def test_ingest_revoked_key_rejected(
    client: AsyncClient,
    create_api_key: tuple[str, str],
    db_session: AsyncSession,
) -> None:
    """A revoked API key should return 401."""
    raw_key, _ = create_api_key

    # Revoke the key directly in the DB
    from api.models import ApiKey

    keys = (await db_session.execute(select(ApiKey))).scalars().all()
    keys[0].revoked_at = datetime(2026, 1, 1)
    await db_session.commit()

    response = await client.post(
        "/ingest/batch",
        json=[_make_span_payload()],
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 401


async def test_ingest_status_escalation_to_error(
    client: AsyncClient,
    create_api_key: tuple[str, str],
    db_session: AsyncSession,
) -> None:
    """If any span has status=error, the trace status should be 'error'."""
    raw_key, _ = create_api_key
    trace_id = "status_test"

    # First batch: ok
    batch_1 = [_make_span_payload(trace_id=trace_id, span_id="ok_span", status="ok")]
    await client.post("/ingest/batch", json=batch_1, headers={"X-Trace-Key": raw_key})

    # Second batch: error
    batch_2 = [
        _make_span_payload(
            trace_id=trace_id,
            span_id="err_span",
            status="error",
            error_message="boom",
        )
    ]
    await client.post("/ingest/batch", json=batch_2, headers={"X-Trace-Key": raw_key})

    traces = (await db_session.execute(select(Trace))).scalars().all()
    assert traces[0].status == "error"
