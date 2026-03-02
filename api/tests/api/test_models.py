"""Tests for SQLAlchemy ORM models — full insert chain."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    ApiKey,
    Organization,
    OrgMember,
    Span,
    SpanSegment,
    Trace,
    UsageEvent,
    User,
)


async def test_create_organization(db_session: AsyncSession) -> None:
    org = Organization(name="Acme Corp")
    db_session.add(org)
    await db_session.commit()

    result = await db_session.execute(select(Organization))
    fetched = result.scalar_one()
    assert fetched.name == "Acme Corp"
    assert fetched.plan == "hobby"
    assert fetched.id is not None


async def test_create_user(db_session: AsyncSession) -> None:
    user = User(email="alice@example.com")
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User))
    fetched = result.scalar_one()
    assert fetched.email == "alice@example.com"


async def test_full_insert_chain(db_session: AsyncSession) -> None:
    """Insert org → user → org_member → api_key → trace → span → segment → usage_event."""
    # Organization
    org = Organization(name="TestOrg")
    db_session.add(org)
    await db_session.flush()

    # User
    user = User(email="bob@example.com")
    db_session.add(user)
    await db_session.flush()

    # OrgMember
    member = OrgMember(org_id=org.id, user_id=user.id, role="owner")
    db_session.add(member)
    await db_session.flush()

    # ApiKey
    api_key = ApiKey(
        org_id=org.id,
        created_by=user.id,
        key_hash="$2b$12$fakehash",
        name="dev-key",
    )
    db_session.add(api_key)
    await db_session.flush()

    # Trace
    now = datetime.now(UTC)
    trace = Trace(
        org_id=org.id,
        function_name="answer_question",
        started_at=now,
        ended_at=now + timedelta(milliseconds=350),
        total_tokens=150,
        status="success",
    )
    db_session.add(trace)
    await db_session.flush()

    # Span
    span = Span(
        trace_id=trace.id,
        org_id=org.id,
        function_name="call_openai",
        span_type="llm",
        model="gpt-4",
        started_at=now,
        ended_at=now + timedelta(milliseconds=300),
        prompt_text="What is Python?",
        prompt_tokens=5,
        completion_text="Python is a programming language.",
        completion_tokens=6,
    )
    db_session.add(span)
    await db_session.flush()

    # SpanSegment
    segment = SpanSegment(
        span_id=span.id,
        segment_name="system_prompt",
        segment_type="system",
        segment_text="You are a helpful assistant.",
        position_start=0,
        position_end=30,
        influence_score=0.85,
    )
    db_session.add(segment)
    await db_session.flush()

    # UsageEvent
    event = UsageEvent(
        org_id=org.id,
        event_type="span_ingested",
        quantity=1,
    )
    db_session.add(event)
    await db_session.commit()

    # Verify counts
    orgs = (await db_session.execute(select(Organization))).scalars().all()
    assert len(orgs) == 1

    traces = (await db_session.execute(select(Trace))).scalars().all()
    assert len(traces) == 1

    spans = (await db_session.execute(select(Span))).scalars().all()
    assert len(spans) == 1

    segments = (await db_session.execute(select(SpanSegment))).scalars().all()
    assert len(segments) == 1

    events = (await db_session.execute(select(UsageEvent))).scalars().all()
    assert len(events) == 1


async def test_trace_duration_ms(db_session: AsyncSession) -> None:
    """Verify hybrid_property computes duration correctly."""
    org = Organization(name="DurOrg")
    db_session.add(org)
    await db_session.flush()

    now = datetime.now(UTC)
    trace = Trace(
        org_id=org.id,
        function_name="slow_fn",
        started_at=now,
        ended_at=now + timedelta(milliseconds=1234),
    )
    db_session.add(trace)
    await db_session.commit()

    result = await db_session.execute(select(Trace))
    fetched = result.scalar_one()
    assert fetched.duration_ms == 1234


async def test_span_duration_ms(db_session: AsyncSession) -> None:
    """Verify span hybrid_property computes duration correctly."""
    org = Organization(name="SpanOrg")
    db_session.add(org)
    await db_session.flush()

    now = datetime.now(UTC)
    trace = Trace(
        org_id=org.id,
        function_name="fn",
        started_at=now,
        ended_at=now + timedelta(seconds=1),
    )
    db_session.add(trace)
    await db_session.flush()

    span = Span(
        trace_id=trace.id,
        org_id=org.id,
        function_name="inner",
        started_at=now,
        ended_at=now + timedelta(milliseconds=500),
    )
    db_session.add(span)
    await db_session.commit()

    result = await db_session.execute(select(Span))
    fetched = result.scalar_one()
    assert fetched.duration_ms == 500


async def test_span_segment_unique_constraint(db_session: AsyncSession) -> None:
    """Duplicate (span_id, segment_name) should raise IntegrityError."""
    import sqlalchemy

    org = Organization(name="UniqueOrg")
    db_session.add(org)
    await db_session.flush()

    now = datetime.now(UTC)
    trace = Trace(
        org_id=org.id,
        function_name="fn",
        started_at=now,
        ended_at=now + timedelta(seconds=1),
    )
    db_session.add(trace)
    await db_session.flush()

    span = Span(
        trace_id=trace.id,
        org_id=org.id,
        function_name="inner",
        started_at=now,
        ended_at=now + timedelta(milliseconds=100),
    )
    db_session.add(span)
    await db_session.flush()

    seg1 = SpanSegment(
        span_id=span.id,
        segment_name="chunk_1",
        segment_type="retrieval",
        segment_text="Some text",
    )
    db_session.add(seg1)
    await db_session.commit()

    seg2 = SpanSegment(
        span_id=span.id,
        segment_name="chunk_1",
        segment_type="retrieval",
        segment_text="Duplicate name",
    )
    db_session.add(seg2)
    try:
        await db_session.commit()
        raise AssertionError("Expected IntegrityError for duplicate segment_name")
    except sqlalchemy.exc.IntegrityError:
        await db_session.rollback()
