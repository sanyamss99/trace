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
    """Unit tests for compute_utilization (pure lexical overlap)."""

    def test_high_utilization(self) -> None:
        """Chunk words appearing in completion score > 0."""
        chunk = "machine learning neural networks"
        completion = "machine learning uses neural architectures"
        score = compute_utilization(chunk, completion)
        # "machine", "learning", "neural" overlap — 3/5 = 0.6
        assert score > 0.5

    def test_full_overlap(self) -> None:
        """Completion that quotes the chunk verbatim scores 1.0."""
        chunk = "Python was created by Guido van Rossum"
        completion = "Python was created by Guido van Rossum"
        score = compute_utilization(chunk, completion)
        assert score == 1.0

    def test_no_overlap(self) -> None:
        """No shared words = 0.0."""
        chunk = "completely different vocabulary"
        completion = "unrelated tokens here"
        score = compute_utilization(chunk, completion)
        assert score == 0.0

    def test_empty_inputs(self) -> None:
        """Empty inputs return 0.0."""
        assert compute_utilization("", "text") == 0.0
        assert compute_utilization("text", "") == 0.0

    def test_score_between_zero_and_one(self) -> None:
        """Score is always in [0.0, 1.0] range."""
        chunk = "python programming language"
        completion = "python is a great programming language for beginners"
        score = compute_utilization(chunk, completion)
        assert 0.0 <= score <= 1.0

    def test_partial_overlap(self) -> None:
        """Partial overlap produces fractional score."""
        chunk = "python language"
        completion = "python is a language for beginners"
        score = compute_utilization(chunk, completion)
        # "python", "language" overlap — 2/6 = 0.333
        assert 0.3 <= score <= 0.4


# ---------------------------------------------------------------------------
# Unit tests — influence scoring
# ---------------------------------------------------------------------------


class TestInfluenceScoring:
    """Unit tests for compute_influence (blended presence + logprob-weighted)."""

    def test_weights_by_uncertainty(self) -> None:
        """Uncertain overlapping tokens produce high influence."""
        chunk = "neural networks"
        completion = "neural networks are powerful"
        logprobs = [
            {"token": "neural", "logprob": -5.0},
            {"token": " networks", "logprob": -2.0},
            {"token": " are", "logprob": -2.0},
            {"token": " powerful", "logprob": -2.0},
        ]
        score = compute_influence(chunk, completion, logprobs)
        assert score > 0.5
        # presence = 2/4 = 0.5, logprob = 7/11 = 0.636
        # blended = 0.4*0.5 + 0.6*0.636 ≈ 0.58
        assert 0.55 <= score <= 0.65

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

    def test_confident_tokens_still_score_via_presence(self) -> None:
        """Presence baseline gives non-zero score even when all tokens confident."""
        chunk = "some text here"
        completion = "some text here"
        logprobs = [
            {"token": "some", "logprob": -0.1},
            {"token": " text", "logprob": -0.1},
            {"token": " here", "logprob": -0.1},
        ]
        score = compute_influence(chunk, completion, logprobs)
        # All confident (no uncertain tokens) → falls back to presence = 3/3 = 1.0
        assert score == 1.0

    def test_empty_inputs(self) -> None:
        """Empty inputs return 0.0."""
        assert compute_influence("", "text", [{"token": "t", "logprob": -1.5}]) == 0.0
        assert compute_influence("text", "", [{"token": "t", "logprob": -1.5}]) == 0.0

    def test_no_logprobs_uses_presence(self) -> None:
        """Without logprobs, influence falls back to pure presence."""
        chunk = "python language"
        completion = "python is a language for beginners"
        score = compute_influence(chunk, completion, None)
        # "python", "language" overlap — 2/6 = 0.333
        assert 0.3 <= score <= 0.4

    def test_influence_between_zero_and_one(self) -> None:
        """Score is always in [0.0, 1.0]."""
        chunk = "python language"
        completion = "python is a language for beginners"
        logprobs = [
            {"token": "python", "logprob": -3.0},
            {"token": " is", "logprob": -0.1},
            {"token": " a", "logprob": -0.1},
            {"token": " language", "logprob": -2.0},
            {"token": " for", "logprob": -2.0},
            {"token": " beginners", "logprob": -2.0},
        ]
        score = compute_influence(chunk, completion, logprobs)
        assert 0.0 <= score <= 1.0

    def test_influence_higher_than_utilization_for_uncertain_overlap(self) -> None:
        """Influence rewards uncertain-token overlap more than raw utilization."""
        chunk = "deep learning"
        completion = "deep learning is useful"
        logprobs = [
            {"token": "deep", "logprob": -10.0},
            {"token": " learning", "logprob": -1.5},
            {"token": " is", "logprob": -2.0},
            {"token": " useful", "logprob": -2.0},
        ]
        util = compute_utilization(chunk, completion)
        infl = compute_influence(chunk, completion, logprobs)
        assert util > 0.0
        assert infl > 0.0
        assert infl > util


# ---------------------------------------------------------------------------
# Integration tests — API endpoints
# ---------------------------------------------------------------------------


def _make_span_with_prompt(**overrides: object) -> dict:
    """Build a span payload with prompt_text and logprobs.

    Simulates a RAG pipeline answering a question about the Transformer
    architecture using chunked Wikipedia article text.
    """
    base: dict = {
        "trace_id": "attr_trace_1",
        "span_id": "attr_span_1",
        "span_type": "llm",
        "function_name": "rag_pipeline.generate_answer",
        "module": "rag_pipeline",
        "start_time": "2026-03-01T00:00:00+00:00",
        "end_time": "2026-03-01T00:00:03+00:00",
        "duration_ms": 3000.0,
        "status": "ok",
        "model": "gpt-4o",
        "prompt_text": (
            "[system]\n"
            "You are a knowledgeable AI assistant. Answer the user's question using "
            "ONLY the provided context documents. Be precise and cite details.\n"
            "<doc title=\"History\">"
            "The Transformer architecture was introduced in 2017 by researchers at "
            "Google Brain in the paper \"Attention Is All You Need\" by Ashish Vaswani, "
            "Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan Gomez, "
            "Lukasz Kaiser, and Illia Polosukhin. It was presented at NeurIPS 2017. "
            "Prior to the Transformer, dominant models were recurrent neural networks "
            "like LSTMs and GRUs which processed tokens sequentially, creating a "
            "bottleneck where the hidden state had to carry all prior information."
            "</doc>\n"
            "<doc title=\"Architecture\">"
            "The Transformer follows an encoder-decoder structure using stacked "
            "self-attention and feed-forward layers. The encoder has N=6 identical "
            "layers with multi-head self-attention and position-wise feed-forward "
            "networks. Residual connections and layer normalization are used around "
            "each sub-layer. The decoder adds a third sub-layer for cross-attention "
            "over the encoder output."
            "</doc>\n"
            "<doc title=\"Attention\">"
            "The core innovation is scaled dot-product attention: "
            "Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) V. The scaling factor "
            "1/sqrt(d_k) prevents dot products from growing too large. Multi-head "
            "attention projects Q, K, V with h=8 different learned projections and "
            "concatenates results, allowing the model to attend to different "
            "representation subspaces simultaneously."
            "</doc>\n"
            "<doc title=\"Impact\">"
            "BERT (2018) used the encoder for masked language modeling. The GPT "
            "family from OpenAI uses the decoder trained autoregressively. GPT-3 "
            "with 175 billion parameters showed few-shot learning. Beyond text, "
            "Vision Transformers handle image classification, AlphaFold 2 predicts "
            "protein structures, and DALL-E generates images from text."
            "</doc>\n\n"
            "[user]\n"
            "How does multi-head attention work in the Transformer and why is the "
            "scaling factor important?"
        ),
        "completion_text": (
            "Multi-head attention works by projecting queries, keys, and values "
            "through h=8 different learned linear projections and performing scaled "
            "dot-product attention on each in parallel. The results are concatenated "
            "and linearly transformed. This lets the model attend to different "
            "representation subspaces at different positions simultaneously.\n\n"
            "The scaling factor 1/sqrt(d_k) is important because without it, the "
            "dot products between queries and keys grow large in magnitude for "
            "high-dimensional vectors, pushing the softmax into regions with "
            "extremely small gradients that impede learning."
        ),
        "completion_logprobs": [
            {"token": "Multi", "logprob": -0.10},
            {"token": "-head", "logprob": -0.06},
            {"token": " attention", "logprob": -0.04},
            {"token": " works", "logprob": -0.08},
            {"token": " by", "logprob": -0.04},
            {"token": " projecting", "logprob": -0.20},
            {"token": " queries", "logprob": -0.12},
            {"token": ",", "logprob": -0.02},
            {"token": " keys", "logprob": -0.08},
            {"token": ",", "logprob": -0.02},
            {"token": " and", "logprob": -0.03},
            {"token": " values", "logprob": -0.08},
            {"token": " through", "logprob": -0.10},
            {"token": " h", "logprob": -0.15},
            {"token": "=8", "logprob": -0.45},
            {"token": " different", "logprob": -0.10},
            {"token": " learned", "logprob": -0.15},
            {"token": " linear", "logprob": -0.18},
            {"token": " projections", "logprob": -0.12},
            {"token": " and", "logprob": -0.03},
            {"token": " performing", "logprob": -0.10},
            {"token": " scaled", "logprob": -0.12},
            {"token": " dot", "logprob": -0.08},
            {"token": "-product", "logprob": -0.06},
            {"token": " attention", "logprob": -0.04},
            {"token": " on", "logprob": -0.03},
            {"token": " each", "logprob": -0.06},
            {"token": " in", "logprob": -0.04},
            {"token": " parallel", "logprob": -0.08},
            {"token": ".", "logprob": -0.02},
            {"token": " The", "logprob": -0.05},
            {"token": " results", "logprob": -0.06},
            {"token": " are", "logprob": -0.04},
            {"token": " concatenated", "logprob": -0.25},
            {"token": " and", "logprob": -0.03},
            {"token": " linearly", "logprob": -0.30},
            {"token": " transformed", "logprob": -0.18},
            {"token": ".", "logprob": -0.02},
            {"token": " This", "logprob": -0.06},
            {"token": " lets", "logprob": -0.12},
            {"token": " the", "logprob": -0.02},
            {"token": " model", "logprob": -0.05},
            {"token": " attend", "logprob": -0.12},
            {"token": " to", "logprob": -0.03},
            {"token": " different", "logprob": -0.06},
            {"token": " representation", "logprob": -0.18},
            {"token": " subspaces", "logprob": -0.40},
            {"token": " at", "logprob": -0.04},
            {"token": " different", "logprob": -0.06},
            {"token": " positions", "logprob": -0.08},
            {"token": " simultaneously", "logprob": -0.20},
            {"token": ".", "logprob": -0.02},
            {"token": "\n\n", "logprob": -0.06},
            {"token": "The", "logprob": -0.05},
            {"token": " scaling", "logprob": -0.10},
            {"token": " factor", "logprob": -0.06},
            {"token": " 1", "logprob": -0.15},
            {"token": "/sqrt", "logprob": -0.12},
            {"token": "(d", "logprob": -0.10},
            {"token": "_k", "logprob": -0.08},
            {"token": ")", "logprob": -0.03},
            {"token": " is", "logprob": -0.03},
            {"token": " important", "logprob": -0.08},
            {"token": " because", "logprob": -0.05},
            {"token": " without", "logprob": -0.12},
            {"token": " it", "logprob": -0.04},
            {"token": ",", "logprob": -0.02},
            {"token": " the", "logprob": -0.02},
            {"token": " dot", "logprob": -0.08},
            {"token": " products", "logprob": -0.10},
            {"token": " between", "logprob": -0.08},
            {"token": " queries", "logprob": -0.10},
            {"token": " and", "logprob": -0.03},
            {"token": " keys", "logprob": -0.06},
            {"token": " grow", "logprob": -0.20},
            {"token": " large", "logprob": -0.12},
            {"token": " in", "logprob": -0.03},
            {"token": " magnitude", "logprob": -0.25},
            {"token": " for", "logprob": -0.04},
            {"token": " high", "logprob": -0.15},
            {"token": "-dimensional", "logprob": -0.10},
            {"token": " vectors", "logprob": -0.18},
            {"token": ",", "logprob": -0.02},
            {"token": " pushing", "logprob": -0.30},
            {"token": " the", "logprob": -0.02},
            {"token": " softmax", "logprob": -0.08},
            {"token": " into", "logprob": -0.06},
            {"token": " regions", "logprob": -0.25},
            {"token": " with", "logprob": -0.04},
            {"token": " extremely", "logprob": -0.20},
            {"token": " small", "logprob": -0.12},
            {"token": " gradients", "logprob": -0.18},
            {"token": " that", "logprob": -0.06},
            {"token": " impede", "logprob": -0.70},
            {"token": " learning", "logprob": -0.08},
            {"token": ".", "logprob": -0.02},
        ],
        "prompt_tokens": 680,
        "completion_tokens": 92,
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
async def test_all_segments_scored(
    client: AsyncClient,
    create_api_key: tuple[str, str],
) -> None:
    """All segment types get utilization and influence scores."""
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
    assert len(data["segments"]) > 0
    for seg in data["segments"]:
        assert seg["utilization_score"] is not None
        assert seg["influence_score"] is not None

    # Retrieval chunks should have meaningful non-zero scores
    retrieval_segs = [s for s in data["segments"] if s["segment_type"] == "retrieval"]
    assert len(retrieval_segs) > 0
    top_chunk = max(retrieval_segs, key=lambda s: s["influence_score"])
    assert top_chunk["influence_score"] > 0.15
