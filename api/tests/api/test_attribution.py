"""Tests for attribution detection, scoring, and API endpoints."""

import pytest
from httpx import AsyncClient

from api.services.attribution import (
    SEGMENT_FEW_SHOT,
    SEGMENT_QUERY,
    SEGMENT_RETRIEVAL,
    SEGMENT_SYSTEM,
    compute_influence,
    compute_utilization,
    detect_segments,
)

# ---------------------------------------------------------------------------
# Unit tests — segment detection
# ---------------------------------------------------------------------------


class TestSegmentDetection:
    """Unit tests for detect_segments."""

    def test_chat_format_system_and_user(self) -> None:
        """Detects system prompt and user query from [role] format."""
        prompt = "[system]\nYou are a helpful assistant.\n\n[user]\nWhat is Python?"
        segments = detect_segments(prompt)
        types = {s.segment_type for s in segments}
        assert SEGMENT_SYSTEM in types
        assert SEGMENT_QUERY in types
        system_seg = next(s for s in segments if s.segment_type == SEGMENT_SYSTEM)
        assert "helpful assistant" in system_seg.text

    def test_user_query_detected(self) -> None:
        """Last user turn is labeled as query."""
        prompt = "[system]\nBe concise.\n\n[user]\nWhat is 2+2?"
        segments = detect_segments(prompt)
        query = next(s for s in segments if s.segment_type == SEGMENT_QUERY)
        assert "2+2" in query.text

    def test_chat_format_with_few_shot(self) -> None:
        """Detects few-shot examples from alternating turns before last user."""
        prompt = (
            "[system]\nAnswer questions.\n\n"
            "[user]\nWhat is 1+1?\n\n"
            "[assistant]\n2\n\n"
            "[user]\nWhat is 2+2?"
        )
        segments = detect_segments(prompt)
        types = {s.segment_type for s in segments}
        assert SEGMENT_FEW_SHOT in types

    def test_xml_retrieval_chunks(self) -> None:
        """Detects XML-tagged retrieval chunks."""
        prompt = (
            "[system]\nUse the context below.\n"
            "<doc>First document about Python.</doc>\n"
            "<doc>Second document about Java.</doc>\n\n"
            "[user]\nCompare the two."
        )
        segments = detect_segments(prompt)
        retrieval = [s for s in segments if s.segment_type == SEGMENT_RETRIEVAL]
        assert len(retrieval) == 2
        assert retrieval[0].retrieval_rank == 1
        assert retrieval[1].retrieval_rank == 2
        assert "Python" in retrieval[0].text

    def test_numbered_retrieval_chunks(self) -> None:
        """Detects numbered-list retrieval chunks."""
        prompt = (
            "1. The sky is blue due to Rayleigh scattering.\n"
            "2. Water appears blue because it absorbs red light."
        )
        segments = detect_segments(prompt)
        retrieval = [s for s in segments if s.segment_type == SEGMENT_RETRIEVAL]
        assert len(retrieval) == 2

    def test_separator_retrieval_chunks(self) -> None:
        """Detects separator-delimited retrieval chunks."""
        prompt = "---\nFirst section content.\n---\nSecond section content."
        segments = detect_segments(prompt)
        retrieval = [s for s in segments if s.segment_type == SEGMENT_RETRIEVAL]
        assert len(retrieval) == 2

    def test_empty_prompt(self) -> None:
        """Empty prompt returns no segments."""
        assert detect_segments("") == []
        assert detect_segments("   ") == []

    def test_plain_text_fallback(self) -> None:
        """Non-chat prompt without chunks produces a single full_prompt segment."""
        segments = detect_segments("Just a plain text prompt.")
        assert len(segments) == 1
        assert segments[0].name == "full_prompt"
        assert segments[0].segment_type == SEGMENT_SYSTEM

    def test_raw_role_format(self) -> None:
        """Detects segments from 'Role: content' format."""
        prompt = "System: You are helpful.\nUser: Hello there"
        segments = detect_segments(prompt)
        types = {s.segment_type for s in segments}
        assert SEGMENT_SYSTEM in types or SEGMENT_QUERY in types
        assert len(segments) >= 2

    def test_position_offsets_set(self) -> None:
        """Segments have position_start and position_end set."""
        prompt = "[system]\nHello world.\n\n[user]\nTest query"
        segments = detect_segments(prompt)
        for seg in segments:
            assert seg.position_start is not None
            assert seg.position_end is not None
            assert seg.position_start < seg.position_end

    def test_segment_names_unique(self) -> None:
        """All segment names within a detection are unique."""
        prompt = (
            "[system]\nUse context.\n"
            "<doc>Doc one.</doc>\n"
            "<doc>Doc two.</doc>\n"
            "<doc>Doc three.</doc>\n\n"
            "[user]\nSummarize."
        )
        segments = detect_segments(prompt)
        names = [s.name for s in segments]
        assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# Unit tests — utilization scoring
# ---------------------------------------------------------------------------


class TestUtilizationScoring:
    """Unit tests for compute_utilization."""

    def test_high_utilization(self) -> None:
        """Chunk words in uncertain completion tokens score > 0."""
        chunk = "machine learning neural networks"
        completion = "machine learning uses neural architectures"
        logprobs = [
            {"token": "machine", "logprob": -2.0},
            {"token": " learning", "logprob": -2.0},
            {"token": " uses", "logprob": -2.0},
            {"token": " neural", "logprob": -2.0},
            {"token": " architectures", "logprob": -2.0},
        ]
        score = compute_utilization(chunk, completion, logprobs)
        assert score > 0.0

    def test_no_uncertain_tokens(self) -> None:
        """All-confident completion returns 0.0."""
        chunk = "some context text"
        completion = "confident output here"
        logprobs = [
            {"token": "confident", "logprob": -0.1},
            {"token": " output", "logprob": -0.2},
            {"token": " here", "logprob": -0.3},
        ]
        score = compute_utilization(chunk, completion, logprobs)
        assert score == 0.0

    def test_no_overlap(self) -> None:
        """Uncertain tokens with zero overlap score 0.0."""
        chunk = "completely different vocabulary"
        completion = "unrelated tokens here"
        logprobs = [
            {"token": "unrelated", "logprob": -2.0},
            {"token": " tokens", "logprob": -2.0},
            {"token": " here", "logprob": -2.0},
        ]
        score = compute_utilization(chunk, completion, logprobs)
        assert score == 0.0

    def test_empty_inputs(self) -> None:
        """Empty inputs return 0.0."""
        assert compute_utilization("", "text", [{"token": "t", "logprob": -1.5}]) == 0.0
        assert compute_utilization("text", "", [{"token": "t", "logprob": -1.5}]) == 0.0
        assert compute_utilization("text", "text", []) == 0.0

    def test_score_between_zero_and_one(self) -> None:
        """Score is always in [0.0, 1.0] range."""
        chunk = "python programming language"
        completion = "python is a great programming language for beginners"
        logprobs = [
            {"token": "python", "logprob": -2.0},
            {"token": " is", "logprob": -0.5},
            {"token": " a", "logprob": -0.5},
            {"token": " great", "logprob": -2.0},
            {"token": " programming", "logprob": -2.0},
            {"token": " language", "logprob": -2.0},
            {"token": " for", "logprob": -2.0},
            {"token": " beginners", "logprob": -2.0},
        ]
        score = compute_utilization(chunk, completion, logprobs)
        assert 0.0 <= score <= 1.0

    def test_legacy_float_format(self) -> None:
        """Legacy list[float] format still works via whitespace alignment."""
        chunk = "machine learning"
        completion = "machine learning works"
        logprobs = [-2.0, -2.0, -2.0]
        score = compute_utilization(chunk, completion, logprobs)
        assert score > 0.0


# ---------------------------------------------------------------------------
# Unit tests — influence scoring
# ---------------------------------------------------------------------------


class TestInfluenceScoring:
    """Unit tests for compute_influence."""

    def test_weights_by_uncertainty(self) -> None:
        """More uncertain overlapping tokens produce higher influence."""
        chunk = "neural networks"
        completion = "neural networks are powerful"
        # "neural" is very uncertain (-5.0), "networks" moderately (-2.0)
        logprobs = [
            {"token": "neural", "logprob": -5.0},
            {"token": " networks", "logprob": -2.0},
            {"token": " are", "logprob": -2.0},
            {"token": " powerful", "logprob": -2.0},
        ]
        score = compute_influence(chunk, completion, logprobs)
        assert score > 0.0
        # overlap weight = 5.0 + 2.0 = 7.0, total = 5.0+2.0+2.0+2.0 = 11.0
        assert abs(score - 7.0 / 11.0) < 0.01

    def test_no_overlap_zero_influence(self) -> None:
        """No overlapping tokens = 0.0 influence."""
        chunk = "completely different words"
        completion = "unrelated tokens here"
        logprobs = [
            {"token": "unrelated", "logprob": -2.0},
            {"token": " tokens", "logprob": -2.0},
            {"token": " here", "logprob": -2.0},
        ]
        assert compute_influence(chunk, completion, logprobs) == 0.0

    def test_no_uncertain_tokens(self) -> None:
        """All confident tokens = 0.0."""
        chunk = "some text"
        completion = "some text here"
        logprobs = [
            {"token": "some", "logprob": -0.1},
            {"token": " text", "logprob": -0.2},
            {"token": " here", "logprob": -0.3},
        ]
        assert compute_influence(chunk, completion, logprobs) == 0.0

    def test_empty_inputs(self) -> None:
        """Empty inputs return 0.0."""
        assert compute_influence("", "text", [{"token": "t", "logprob": -1.5}]) == 0.0
        assert compute_influence("text", "", [{"token": "t", "logprob": -1.5}]) == 0.0
        assert compute_influence("text", "text", []) == 0.0

    def test_influence_between_zero_and_one(self) -> None:
        """Score is always in [0.0, 1.0]."""
        chunk = "python language"
        completion = "python is a language for beginners"
        logprobs = [
            {"token": "python", "logprob": -3.0},
            {"token": " is", "logprob": -0.5},
            {"token": " a", "logprob": -0.5},
            {"token": " language", "logprob": -2.0},
            {"token": " for", "logprob": -2.0},
            {"token": " beginners", "logprob": -2.0},
        ]
        score = compute_influence(chunk, completion, logprobs)
        assert 0.0 <= score <= 1.0

    def test_influence_differs_from_utilization(self) -> None:
        """Influence and utilization can differ when uncertainty varies."""
        chunk = "deep learning"
        completion = "deep learning is useful"
        # "deep" is extremely uncertain, "learning" only slightly
        logprobs = [
            {"token": "deep", "logprob": -10.0},
            {"token": " learning", "logprob": -1.5},
            {"token": " is", "logprob": -2.0},
            {"token": " useful", "logprob": -2.0},
        ]
        util = compute_utilization(chunk, completion, logprobs)
        infl = compute_influence(chunk, completion, logprobs)
        # Both > 0, but influence should be higher because "deep" is very uncertain
        assert util > 0.0
        assert infl > 0.0
        assert infl > util


# ---------------------------------------------------------------------------
# Integration tests — API endpoints
# ---------------------------------------------------------------------------


def _make_span_with_prompt(**overrides: object) -> dict:
    """Build a span payload with prompt_text and logprobs."""
    base: dict = {
        "trace_id": "attr_trace_1",
        "span_id": "attr_span_1",
        "span_type": "llm",
        "function_name": "my_rag.answer",
        "module": "my_rag",
        "start_time": "2026-03-01T00:00:00+00:00",
        "end_time": "2026-03-01T00:00:01+00:00",
        "duration_ms": 1000.0,
        "status": "ok",
        "model": "gpt-4o",
        "prompt_text": (
            "[system]\nYou are a helpful assistant. Use the context below.\n"
            "<doc>Python was created by Guido van Rossum.</doc>\n"
            "<doc>Python 3.11 added exception groups.</doc>\n\n"
            "[user]\nWho created Python?"
        ),
        "completion_text": "Python was created by Guido van Rossum.",
        "completion_logprobs": [
            {"token": "Python", "logprob": -0.1},
            {"token": " was", "logprob": -0.2},
            {"token": " created", "logprob": -0.3},
            {"token": " by", "logprob": -2.0},
            {"token": " Guido", "logprob": -1.5},
            {"token": " van", "logprob": -2.0},
            {"token": " Rossum", "logprob": -0.1},
        ],
        "prompt_tokens": 50,
        "completion_tokens": 7,
        "environment": "test",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_get_attribution_endpoint(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """GET /traces/spans/:id/attribution triggers computation and returns segments."""
    raw_key, _ = create_api_key
    headers = {"X-Trace-Key": raw_key}

    await client.post("/ingest/batch", json=[_make_span_with_prompt()], headers=headers)

    response = await client.get("/traces/spans/attr_span_1/attribution", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["span_id"] == "attr_span_1"
    assert len(data["segments"]) > 0
    types = {s["segment_type"] for s in data["segments"]}
    assert "retrieval" in types


@pytest.mark.asyncio
async def test_span_includes_segments_after_attribution(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """After attribution is computed, GET /spans/:id includes segments."""
    raw_key, _ = create_api_key
    headers = {"X-Trace-Key": raw_key}

    await client.post(
        "/ingest/batch",
        json=[_make_span_with_prompt(span_id="seg_span_1")],
        headers=headers,
    )

    # Trigger attribution
    await client.get("/traces/spans/seg_span_1/attribution", headers=headers)

    # GET span should now include segments
    response = await client.get("/traces/spans/seg_span_1", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["segments"]) > 0


@pytest.mark.asyncio
async def test_attribution_no_prompt_text(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Attribution on span without prompt_text returns 422."""
    raw_key, _ = create_api_key
    headers = {"X-Trace-Key": raw_key}

    await client.post(
        "/ingest/batch",
        json=[_make_span_with_prompt(span_id="no_prompt_1", prompt_text=None)],
        headers=headers,
    )

    response = await client.get("/traces/spans/no_prompt_1/attribution", headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_attribution_nonexistent_span(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Attribution on nonexistent span returns 404."""
    raw_key, _ = create_api_key
    response = await client.get(
        "/traces/spans/nonexistent_span/attribution",
        headers={"X-Trace-Key": raw_key},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_attribution_idempotent(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Calling attribution twice returns same results (cached from DB)."""
    raw_key, _ = create_api_key
    headers = {"X-Trace-Key": raw_key}

    await client.post(
        "/ingest/batch",
        json=[_make_span_with_prompt(span_id="idem_span_1")],
        headers=headers,
    )

    r1 = await client.get("/traces/spans/idem_span_1/attribution", headers=headers)
    r2 = await client.get("/traces/spans/idem_span_1/attribution", headers=headers)
    assert r1.status_code == 200
    assert r1.json() == r2.json()


@pytest.mark.asyncio
async def test_attribution_force_recompute(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """force=true triggers re-computation."""
    raw_key, _ = create_api_key
    headers = {"X-Trace-Key": raw_key}

    await client.post(
        "/ingest/batch",
        json=[_make_span_with_prompt(span_id="force_span_1")],
        headers=headers,
    )

    r1 = await client.get("/traces/spans/force_span_1/attribution", headers=headers)
    assert r1.status_code == 200

    r2 = await client.get(
        "/traces/spans/force_span_1/attribution",
        params={"force": "true"},
        headers=headers,
    )
    assert r2.status_code == 200
    assert len(r2.json()["segments"]) > 0


@pytest.mark.asyncio
async def test_trace_detail_includes_segments(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """GET /traces/:id includes segments on spans after attribution."""
    raw_key, _ = create_api_key
    headers = {"X-Trace-Key": raw_key}

    await client.post(
        "/ingest/batch",
        json=[_make_span_with_prompt(trace_id="detail_trace_1", span_id="detail_span_1")],
        headers=headers,
    )

    # Trigger attribution
    await client.get("/traces/spans/detail_span_1/attribution", headers=headers)

    # GET trace should include segments on the span
    response = await client.get("/traces/detail_trace_1", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["spans"]) == 1
    assert len(data["spans"][0]["segments"]) > 0


@pytest.mark.asyncio
async def test_attribution_unauthenticated(
    client: AsyncClient,
) -> None:
    """Attribution without auth returns 401."""
    response = await client.get("/traces/spans/any_span/attribution")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_utilization_scores_on_retrieval_chunks(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """Retrieval chunks get utilization_score when logprobs are available."""
    raw_key, _ = create_api_key
    headers = {"X-Trace-Key": raw_key}

    await client.post(
        "/ingest/batch",
        json=[_make_span_with_prompt(span_id="util_span_1")],
        headers=headers,
    )

    response = await client.get("/traces/spans/util_span_1/attribution", headers=headers)
    assert response.status_code == 200
    data = response.json()
    retrieval_segs = [s for s in data["segments"] if s["segment_type"] == "retrieval"]
    assert len(retrieval_segs) > 0
    for seg in retrieval_segs:
        assert seg["utilization_score"] is not None
        assert seg["influence_score"] is not None
