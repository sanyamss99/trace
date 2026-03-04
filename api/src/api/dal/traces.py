"""Data access layer for trace records."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Row, and_, case, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from api.constants import STATUS_ERROR
from api.models import Span, Trace

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


async def upsert_trace(
    db: AsyncSession,
    *,
    trace_id: str,
    org_id: str,
    function_name: str,
    environment: str,
    started_at: datetime,
    ended_at: datetime,
    total_tokens: int | None,
    status: str,
    tags: dict | None,
) -> None:
    """Insert a new trace or update an existing one via ON CONFLICT DO UPDATE.

    On conflict: widen time window, accumulate tokens, escalate status
    to 'error' if any span errored, and update function_name/environment/tags.
    """
    table = Trace.__table__

    stmt = pg_insert(table).values(
        id=trace_id,
        org_id=org_id,
        function_name=function_name,
        environment=environment,
        started_at=started_at,
        ended_at=ended_at,
        total_tokens=total_tokens,
        status=status,
        tags=tags,
    )

    excluded = stmt.excluded

    update_dict = {
        "started_at": func.least(table.c.started_at, excluded.started_at),
        "ended_at": func.greatest(table.c.ended_at, excluded.ended_at),
        "total_tokens": case(
            (excluded.total_tokens.is_(None), table.c.total_tokens),
            else_=func.coalesce(table.c.total_tokens, 0) + excluded.total_tokens,
        ),
        "status": case(
            (table.c.status == STATUS_ERROR, STATUS_ERROR),
            (excluded.status == STATUS_ERROR, STATUS_ERROR),
            else_=excluded.status,
        ),
        "function_name": excluded.function_name,
        "environment": excluded.environment,
        "tags": excluded.tags,
    }

    stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_dict)
    await db.execute(stmt)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


async def get_trace_by_id(
    db: AsyncSession,
    trace_id: str,
    org_id: str,
) -> Trace | None:
    """Fetch a single trace by ID, scoped to org."""
    result = await db.execute(select(Trace).where(Trace.id == trace_id, Trace.org_id == org_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Cursor helpers
# ---------------------------------------------------------------------------


def _encode_cursor(started_at: datetime, trace_id: str) -> str:
    """Encode a pagination cursor as a URL-safe base64 string."""
    payload = json.dumps({"s": started_at.isoformat(), "i": trace_id})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    """Decode a pagination cursor into (started_at, trace_id).

    Raises ValueError on malformed input.
    """
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return datetime.fromisoformat(payload["s"]), payload["i"]
    except (json.JSONDecodeError, KeyError, ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid cursor: {cursor}") from exc


# ---------------------------------------------------------------------------
# List (cursor-based keyset pagination)
# ---------------------------------------------------------------------------


async def list_traces(
    db: AsyncSession,
    org_id: str,
    *,
    limit: int = 50,
    cursor: str | None = None,
    function_name: str | None = None,
    environment: str | None = None,
    status: str | None = None,
) -> tuple[list[Row], str | None]:
    """List traces with cursor-based (keyset) pagination.

    Returns (rows_with_span_count, next_cursor_or_none).
    Each row has a Trace object and a span_count integer.
    """
    span_count_subq = (
        select(func.count(Span.id))
        .where(Span.trace_id == Trace.id)
        .correlate(Trace)
        .scalar_subquery()
        .label("span_count")
    )

    query = select(Trace, span_count_subq).where(Trace.org_id == org_id)

    if function_name:
        query = query.where(Trace.function_name == function_name)
    if environment:
        query = query.where(Trace.environment == environment)
    if status:
        query = query.where(Trace.status == status)

    # Apply keyset cursor condition
    if cursor:
        cursor_started_at, cursor_id = _decode_cursor(cursor)
        query = query.where(
            or_(
                Trace.started_at < cursor_started_at,
                and_(
                    Trace.started_at == cursor_started_at,
                    Trace.id < cursor_id,
                ),
            )
        )

    query = query.order_by(Trace.started_at.desc(), Trace.id.desc())
    query = query.limit(limit + 1)

    result = await db.execute(query)
    rows = list(result.all())

    if len(rows) > limit:
        rows = rows[:limit]
        last_trace = rows[-1][0]
        next_cursor = _encode_cursor(last_trace.started_at, last_trace.id)
    else:
        next_cursor = None

    return rows, next_cursor
