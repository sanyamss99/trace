"""Attribution service — segment detection and utilization scoring.

Phase 1 implements:
- Automatic segment detection from prompt_text (system, retrieval, query, few-shot)
- Retrieval utilization scoring via lexical overlap with uncertain completion tokens
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from api.dal import segments as segment_dal

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
from api.dal import spans as span_dal
from api.exceptions import AttributionError, NotFoundError
from api.logger import logger
from api.models import SpanSegment

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEGMENT_SYSTEM = "system"
SEGMENT_RETRIEVAL = "retrieval"
SEGMENT_QUERY = "query"
SEGMENT_FEW_SHOT = "few_shot"

# Logprob threshold — tokens with logprob below this are "uncertain"
# -0.3 captures moderately uncertain tokens, not just the very uncertain ones
_UNCERTAIN_LOGPROB_THRESHOLD = -0.3


# ---------------------------------------------------------------------------
# Detected segment dataclass
# ---------------------------------------------------------------------------


@dataclass
class DetectedSegment:
    """A segment detected within prompt_text."""

    name: str
    segment_type: str
    text: str
    position_start: int
    position_end: int
    retrieval_rank: int | None = None


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# SDK-formatted [role] markers
_ROLE_MARKER_RE = re.compile(
    r"^\[(system|user|human|assistant|model)\]\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Raw "Role:" format
_RAW_ROLE_RE = re.compile(
    r"^(System|Human|User|Assistant|AI|Model)\s*:\s*",
    re.MULTILINE | re.IGNORECASE,
)

# XML-tagged chunks: <doc>...</doc>, <context>...</context>, etc.
_XML_CHUNK_RE = re.compile(
    r"<(doc|context|chunk|document|source|passage)(?:\s[^>]*)?>(.+?)</\1>",
    re.DOTALL | re.IGNORECASE,
)

# Numbered list: "1. ...\n2. ..."
_NUMBERED_CHUNK_RE = re.compile(
    r"(?:^|\n)(\d+)\.\s+(.+?)(?=\n\d+\.\s|\Z)",
    re.DOTALL,
)

# Separator-delimited sections: --- or ===
_SEPARATOR_CHUNK_RE = re.compile(
    r"(?:^|\n)(?:---+|===+)\n(.+?)(?=\n(?:---+|===+)|\Z)",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Segment detection
# ---------------------------------------------------------------------------


def _parse_chat_format(prompt_text: str) -> list[tuple[str, str, int, int]] | None:
    """Parse prompt_text into (role, content, start, end) tuples.

    Returns None if the prompt is not in a recognizable chat format.
    """
    # Try SDK-formatted [role] markers first
    markers = list(_ROLE_MARKER_RE.finditer(prompt_text))
    if len(markers) >= 2:
        turns: list[tuple[str, str, int, int]] = []
        for i, match in enumerate(markers):
            role = match.group(1).lower()
            content_start = match.end()
            content_end = markers[i + 1].start() if i + 1 < len(markers) else len(prompt_text)
            content = prompt_text[content_start:content_end].strip()
            if content:
                turns.append((role, content, match.start(), content_end))
        return turns if turns else None

    # Try raw "Role:" format
    raw_markers = list(_RAW_ROLE_RE.finditer(prompt_text))
    if len(raw_markers) >= 2:
        turns = []
        for i, match in enumerate(raw_markers):
            role = match.group(1).lower()
            content_start = match.end()
            if i + 1 < len(raw_markers):
                content_end = raw_markers[i + 1].start()
            else:
                content_end = len(prompt_text)
            content = prompt_text[content_start:content_end].strip()
            if content:
                turns.append((role, content, match.start(), content_end))
        return turns if turns else None

    return None


def _detect_retrieval_chunks(text: str, base_offset: int) -> list[DetectedSegment]:
    """Detect retrieval chunks within a text segment."""
    segments: list[DetectedSegment] = []

    # XML tags (highest specificity)
    xml_matches = list(_XML_CHUNK_RE.finditer(text))
    if xml_matches:
        for i, match in enumerate(xml_matches):
            segments.append(
                DetectedSegment(
                    name=f"chunk_{i + 1}",
                    segment_type=SEGMENT_RETRIEVAL,
                    text=match.group(2).strip(),
                    position_start=base_offset + match.start(),
                    position_end=base_offset + match.end(),
                    retrieval_rank=i + 1,
                )
            )
        return segments

    # Numbered lists (need ≥2 to be confident)
    numbered_matches = list(_NUMBERED_CHUNK_RE.finditer(text))
    if len(numbered_matches) >= 2:
        for match in numbered_matches:
            rank = int(match.group(1))
            segments.append(
                DetectedSegment(
                    name=f"chunk_{rank}",
                    segment_type=SEGMENT_RETRIEVAL,
                    text=match.group(2).strip(),
                    position_start=base_offset + match.start(),
                    position_end=base_offset + match.end(),
                    retrieval_rank=rank,
                )
            )
        return segments

    # Separator-delimited (need ≥2)
    sep_matches = list(_SEPARATOR_CHUNK_RE.finditer(text))
    if len(sep_matches) >= 2:
        for i, match in enumerate(sep_matches):
            segments.append(
                DetectedSegment(
                    name=f"chunk_{i + 1}",
                    segment_type=SEGMENT_RETRIEVAL,
                    text=match.group(1).strip(),
                    position_start=base_offset + match.start(),
                    position_end=base_offset + match.end(),
                    retrieval_rank=i + 1,
                )
            )
        return segments

    return segments


def detect_segments(prompt_text: str) -> list[DetectedSegment]:
    """Auto-detect logical segments from prompt_text.

    Detection strategy:
    1. Parse into chat turns if recognizable format
    2. Identify system prompt (first system turn or pre-user content)
    3. Identify user query (last human/user turn)
    4. Identify few-shot examples (alternating user/assistant turns before final query)
    5. Within any turn, detect retrieval chunks
    6. Fallback: try chunk detection on entire text, else single full_prompt segment
    """
    if not prompt_text or not prompt_text.strip():
        return []

    segments: list[DetectedSegment] = []
    turns = _parse_chat_format(prompt_text)

    if turns:
        _detect_from_chat_turns(turns, segments)
    else:
        _detect_from_plain_text(prompt_text, segments)

    return segments


def _detect_from_chat_turns(
    turns: list[tuple[str, str, int, int]],
    segments: list[DetectedSegment],
) -> None:
    """Detect segments from parsed chat turns."""
    user_roles = {"user", "human"}

    # System turns
    system_turns = [(r, c, s, e) for r, c, s, e in turns if r == "system"]
    for i, (_role, content, start, end) in enumerate(system_turns):
        name = "system_prompt" if i == 0 else f"system_prompt_{i + 1}"
        retrieval = _detect_retrieval_chunks(content, start)
        if retrieval:
            segments.extend(retrieval)
        else:
            segments.append(
                DetectedSegment(
                    name=name,
                    segment_type=SEGMENT_SYSTEM,
                    text=content,
                    position_start=start,
                    position_end=end,
                )
            )

    # Non-system turns
    non_system = [(r, c, s, e) for r, c, s, e in turns if r != "system"]
    if not non_system:
        return

    # Find last user turn = user query
    last_user_idx = None
    for i in range(len(non_system) - 1, -1, -1):
        if non_system[i][0] in user_roles:
            last_user_idx = i
            break

    if last_user_idx is not None:
        _role, content, start, end = non_system[last_user_idx]

        # Check for retrieval chunks within the user query
        retrieval = _detect_retrieval_chunks(content, start)
        if retrieval:
            segments.extend(retrieval)

        segments.append(
            DetectedSegment(
                name="user_query",
                segment_type=SEGMENT_QUERY,
                text=content,
                position_start=start,
                position_end=end,
            )
        )

        # Turns before the last user turn = few-shot examples
        few_shot_turns = non_system[:last_user_idx]
        if len(few_shot_turns) >= 2:
            parts = [f"[{r}] {c}" for r, c, _s, _e in few_shot_turns]
            segments.append(
                DetectedSegment(
                    name="few_shot_examples",
                    segment_type=SEGMENT_FEW_SHOT,
                    text="\n".join(parts),
                    position_start=few_shot_turns[0][2],
                    position_end=few_shot_turns[-1][3],
                )
            )
    else:
        # No user turns — treat all non-system as context
        for i, (_role, content, start, end) in enumerate(non_system):
            retrieval = _detect_retrieval_chunks(content, start)
            if retrieval:
                segments.extend(retrieval)
            else:
                segments.append(
                    DetectedSegment(
                        name=f"context_{i + 1}",
                        segment_type=SEGMENT_RETRIEVAL,
                        text=content,
                        position_start=start,
                        position_end=end,
                    )
                )


def _detect_from_plain_text(
    prompt_text: str,
    segments: list[DetectedSegment],
) -> None:
    """Detect segments from non-chat-format prompt text."""
    retrieval = _detect_retrieval_chunks(prompt_text, 0)
    if retrieval:
        segments.extend(retrieval)
    else:
        segments.append(
            DetectedSegment(
                name="full_prompt",
                segment_type=SEGMENT_SYSTEM,
                text=prompt_text.strip(),
                position_start=0,
                position_end=len(prompt_text),
            )
        )


# ---------------------------------------------------------------------------
# Utilization scoring
# ---------------------------------------------------------------------------


def _clean_token(raw: str) -> str:
    """Normalize a token: strip whitespace and punctuation, lowercase."""
    return raw.strip().strip(".,;:!?\"'()[]{}/-").lower()


def _tokenize(text: str) -> set[str]:
    """Whitespace tokenizer with case-folding and punctuation stripping."""
    tokens: set[str] = set()
    for word in text.split():
        cleaned = _clean_token(word)
        if cleaned:
            tokens.add(cleaned)
    return tokens


def compute_utilization(
    chunk_text: str,
    completion_text: str,
    completion_logprobs: list[dict[str, object]] | list[float] | None = None,
) -> float:
    """Compute utilization score for a prompt segment.

    Measures what fraction of completion words appear in the segment
    (pure lexical recall). This answers: "how much of the output came
    from this segment?"

    Returns 0.0 if inputs are empty.
    """
    if not chunk_text or not completion_text:
        return 0.0

    chunk_tokens = _tokenize(chunk_text)
    completion_tokens = _tokenize(completion_text)

    if not completion_tokens:
        return 0.0

    overlap = len(chunk_tokens & completion_tokens)
    return overlap / len(completion_tokens)


def compute_influence(
    chunk_text: str,
    completion_text: str,
    completion_logprobs: list[dict[str, object]] | list[float] | None = None,
) -> float:
    """Compute influence score for a prompt segment.

    Blends two signals:
    - Presence (40%): lexical overlap regardless of confidence
    - Uncertainty-weighted overlap (60%): tokens the model was less sure
      about count more, answering "did this segment help with the hard parts?"

    When logprobs are unavailable, falls back to pure lexical overlap.

    Returns 0.0 if inputs are empty.
    """
    if not chunk_text or not completion_text:
        return 0.0

    chunk_tokens = _tokenize(chunk_text)
    completion_tokens = _tokenize(completion_text)

    if not completion_tokens:
        return 0.0

    # Presence baseline — pure lexical recall
    presence = len(chunk_tokens & completion_tokens) / len(completion_tokens)

    if not completion_logprobs:
        return presence

    # Build list of (cleaned_token, abs_logprob) for uncertain tokens
    uncertain: list[tuple[str, float]] = []

    if isinstance(completion_logprobs[0], dict):
        for entry in completion_logprobs:
            lp = float(entry["logprob"])  # type: ignore[arg-type]
            if lp < _UNCERTAIN_LOGPROB_THRESHOLD:
                token = _clean_token(str(entry.get("token", "")))
                if token:
                    uncertain.append((token, abs(lp)))
    else:
        completion_words = completion_text.split()
        min_len = min(len(completion_words), len(completion_logprobs))
        for i in range(min_len):
            lp = float(completion_logprobs[i])
            if lp < _UNCERTAIN_LOGPROB_THRESHOLD:
                cleaned = _clean_token(completion_words[i])
                if cleaned:
                    uncertain.append((cleaned, abs(lp)))

    if not uncertain:
        # No uncertain tokens — influence is just presence
        return presence

    total_weight = sum(w for _, w in uncertain)
    overlap_weight = sum(w for tok, w in uncertain if tok in chunk_tokens)
    logprob_score = overlap_weight / total_weight

    # Blend: 40% presence + 60% logprob-weighted
    return 0.4 * presence + 0.6 * logprob_score


# ---------------------------------------------------------------------------
# Attribution result
# ---------------------------------------------------------------------------


class AttributionResult:
    """Result of attribution computation."""

    def __init__(self, segments: list[SpanSegment], method: str) -> None:
        self.segments = segments
        self.method = method


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def compute_attribution(
    db: AsyncSession,
    span_id: str,
    org_id: str,
    *,
    force: bool = False,
) -> AttributionResult:
    """Compute attribution for a span.

    If segments already exist and ``force=False``, returns cached results.
    Otherwise, detects segments, computes utilization, and persists.
    """
    span = await span_dal.get_span_by_id(db, span_id, org_id)
    if not span:
        raise NotFoundError("Span", span_id)

    # Return existing segments if already computed (and not forcing)
    if not force:
        existing = await segment_dal.get_segments_by_span(db, span_id)
        if existing:
            method = existing[0].attribution_method or "utilization"
            return AttributionResult(segments=existing, method=method)

    if not span.prompt_text:
        raise AttributionError(
            f"Span '{span_id}' has no prompt_text. "
            "Ensure the SDK is capturing prompt text for LLM spans."
        )

    # Detect segments from prompt
    detected = detect_segments(span.prompt_text)
    if not detected:
        raise AttributionError(f"No segments detected in span '{span_id}' prompt text.")

    # Compute utilization and influence for all segments when completion text is available
    has_logprobs = bool(span.completion_logprobs)
    has_completion = bool(span.completion_text)

    orm_segments: list[SpanSegment] = []
    for seg in detected:
        utilization: float | None = None
        influence: float | None = None
        if has_completion:
            utilization = compute_utilization(
                chunk_text=seg.text,
                completion_text=span.completion_text,
            )
            influence = compute_influence(
                chunk_text=seg.text,
                completion_text=span.completion_text,
                completion_logprobs=span.completion_logprobs if has_logprobs else None,
            )

        orm_segments.append(
            SpanSegment(
                id=str(uuid4()),
                span_id=span_id,
                segment_name=seg.name,
                segment_type=seg.segment_type,
                segment_text=seg.text,
                position_start=seg.position_start,
                position_end=seg.position_end,
                retrieval_rank=seg.retrieval_rank,
                utilization_score=utilization,
                influence_score=influence,
                attribution_method="utilization" if has_logprobs else "detection_only",
            )
        )

    # Clear existing segments if forcing re-computation
    if force:
        await segment_dal.delete_segments_by_span(db, span_id)

    await segment_dal.bulk_upsert_segments(db, orm_segments)

    logger.info(
        "Attribution computed span_id=%s segments=%d method=%s",
        span_id,
        len(orm_segments),
        "utilization" if has_logprobs else "detection_only",
    )

    return AttributionResult(
        segments=orm_segments,
        method="utilization" if has_logprobs else "detection_only",
    )
