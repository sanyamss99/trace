"""Tests for usetrace.capture.llm_response — multi-vendor extraction."""

from types import SimpleNamespace

from usetrace.capture.llm_response import extract_llm_response

# ---------------------------------------------------------------------------
# Helpers to build mock vendor responses
# ---------------------------------------------------------------------------


def _make_openai_response(
    content: str = "Hello!",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    logprobs: object | None = None,
) -> SimpleNamespace:
    """OpenAI / xAI (Grok) / Together ChatCompletion shape."""
    choice = SimpleNamespace(
        message=SimpleNamespace(content=content),
        logprobs=logprobs,
    )
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    return SimpleNamespace(choices=[choice], usage=usage)


def _make_anthropic_response(
    text: str = "Hello from Claude!",
    input_tokens: int = 15,
    output_tokens: int = 8,
) -> SimpleNamespace:
    """Anthropic Messages API shape: .content[0].text, .usage.input_tokens."""
    content_block = SimpleNamespace(type="text", text=text)
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(
        content=[content_block],
        usage=usage,
        role="assistant",
        stop_reason="end_turn",
    )


def _make_gemini_response(
    text: str = "Hello from Gemini!",
    prompt_token_count: int = 20,
    candidates_token_count: int = 12,
    logprobs_result: object | None = None,
) -> SimpleNamespace:
    """Google Gemini GenerateContentResponse shape."""
    candidate = SimpleNamespace(
        content=SimpleNamespace(parts=[SimpleNamespace(text=text)]),
        logprobs_result=logprobs_result,
    )
    usage_metadata = SimpleNamespace(
        prompt_token_count=prompt_token_count,
        candidates_token_count=candidates_token_count,
        total_token_count=prompt_token_count + candidates_token_count,
    )
    return SimpleNamespace(
        text=text,
        candidates=[candidate],
        usage_metadata=usage_metadata,
    )


def _make_ollama_response(
    content: str = "Hello from Ollama!",
    prompt_eval_count: int = 25,
    eval_count: int = 10,
    logprobs: list[object] | None = None,
) -> SimpleNamespace:
    """Ollama ChatResponse shape: .message.content, .prompt_eval_count."""
    return SimpleNamespace(
        message=SimpleNamespace(content=content, role="assistant"),
        prompt_eval_count=prompt_eval_count,
        eval_count=eval_count,
        logprobs=logprobs,
    )


# ---------------------------------------------------------------------------
# OpenAI / xAI / Together tests
# ---------------------------------------------------------------------------


class TestOpenAIExtraction:
    def test_extracts_completion_text(self) -> None:
        resp = _make_openai_response(content="The answer is 42.")
        result = extract_llm_response(resp)
        assert result["completion_text"] == "The answer is 42."

    def test_extracts_token_counts(self) -> None:
        resp = _make_openai_response(prompt_tokens=100, completion_tokens=50)
        result = extract_llm_response(resp)
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50

    def test_extracts_together_logprobs(self) -> None:
        """Together flat format: logprobs.token_logprobs (parallel array)."""
        logprobs = SimpleNamespace(token_logprobs=[-0.1, -0.5, -0.3])
        resp = _make_openai_response(logprobs=logprobs)
        result = extract_llm_response(resp)
        assert result["completion_logprobs"] == [-0.1, -0.5, -0.3]

    def test_extracts_openai_new_format_logprobs(self) -> None:
        """OpenAI newer format: logprobs.content[].logprob."""
        content_logprobs = [
            SimpleNamespace(logprob=-0.2),
            SimpleNamespace(logprob=-0.8),
        ]
        logprobs = SimpleNamespace(token_logprobs=None, content=content_logprobs)
        resp = _make_openai_response(logprobs=logprobs)
        result = extract_llm_response(resp)
        assert result["completion_logprobs"] == [-0.2, -0.8]

    def test_handles_missing_usage(self) -> None:
        choice = SimpleNamespace(message=SimpleNamespace(content="hi"), logprobs=None)
        resp = SimpleNamespace(choices=[choice])
        result = extract_llm_response(resp)
        assert result["completion_text"] == "hi"
        assert "prompt_tokens" not in result

    def test_handles_empty_choices(self) -> None:
        resp = SimpleNamespace(choices=[], usage=None)
        result = extract_llm_response(resp)
        assert "completion_text" not in result


# ---------------------------------------------------------------------------
# Anthropic (Claude) tests
# ---------------------------------------------------------------------------


class TestAnthropicExtraction:
    def test_extracts_completion_text(self) -> None:
        resp = _make_anthropic_response(text="Claude says hello")
        result = extract_llm_response(resp)
        assert result["completion_text"] == "Claude says hello"

    def test_extracts_token_counts(self) -> None:
        resp = _make_anthropic_response(input_tokens=50, output_tokens=30)
        result = extract_llm_response(resp)
        assert result["prompt_tokens"] == 50
        assert result["completion_tokens"] == 30

    def test_handles_multiple_content_blocks(self) -> None:
        """Anthropic can return multiple content blocks; we extract the first text."""
        blocks = [
            SimpleNamespace(type="text", text="First block"),
            SimpleNamespace(type="text", text="Second block"),
        ]
        usage = SimpleNamespace(input_tokens=10, output_tokens=5)
        resp = SimpleNamespace(content=blocks, usage=usage)
        result = extract_llm_response(resp)
        assert result["completion_text"] == "First block"

    def test_no_logprobs(self) -> None:
        """Anthropic does not support logprobs."""
        resp = _make_anthropic_response()
        result = extract_llm_response(resp)
        assert "completion_logprobs" not in result


# ---------------------------------------------------------------------------
# Google Gemini tests
# ---------------------------------------------------------------------------


class TestGeminiExtraction:
    def test_extracts_completion_text(self) -> None:
        resp = _make_gemini_response(text="Gemini says hello")
        result = extract_llm_response(resp)
        assert result["completion_text"] == "Gemini says hello"

    def test_extracts_token_counts(self) -> None:
        resp = _make_gemini_response(prompt_token_count=100, candidates_token_count=40)
        result = extract_llm_response(resp)
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 40

    def test_extracts_logprobs(self) -> None:
        chosen = [
            SimpleNamespace(token="Hello", log_probability=-0.1, token_id=1),
            SimpleNamespace(token="!", log_probability=-0.05, token_id=2),
        ]
        logprobs_result = SimpleNamespace(chosen_candidates=chosen)
        resp = _make_gemini_response(logprobs_result=logprobs_result)
        result = extract_llm_response(resp)
        assert result["completion_logprobs"] == [-0.1, -0.05]


# ---------------------------------------------------------------------------
# Ollama tests
# ---------------------------------------------------------------------------


class TestOllamaExtraction:
    def test_extracts_completion_text(self) -> None:
        resp = _make_ollama_response(content="Ollama says hello")
        result = extract_llm_response(resp)
        assert result["completion_text"] == "Ollama says hello"

    def test_extracts_token_counts(self) -> None:
        resp = _make_ollama_response(prompt_eval_count=80, eval_count=20)
        result = extract_llm_response(resp)
        assert result["prompt_tokens"] == 80
        assert result["completion_tokens"] == 20

    def test_extracts_logprobs(self) -> None:
        logprobs = [
            SimpleNamespace(token="Hi", logprob=-0.3, top_logprobs=None),
            SimpleNamespace(token="!", logprob=-0.1, top_logprobs=None),
        ]
        resp = _make_ollama_response(logprobs=logprobs)
        result = extract_llm_response(resp)
        assert result["completion_logprobs"] == [-0.3, -0.1]


# ---------------------------------------------------------------------------
# Never-raises contract
# ---------------------------------------------------------------------------


class TestNeverRaises:
    def test_string_input(self) -> None:
        result = extract_llm_response("just a string")
        assert isinstance(result, dict)

    def test_none_input(self) -> None:
        result = extract_llm_response(None)
        assert isinstance(result, dict)

    def test_number_input(self) -> None:
        result = extract_llm_response(42)
        assert isinstance(result, dict)

    def test_empty_object(self) -> None:
        result = extract_llm_response(SimpleNamespace())
        assert isinstance(result, dict)

    def test_malformed_choices(self) -> None:
        """choices exists but contains garbage."""
        resp = SimpleNamespace(choices=[None])
        result = extract_llm_response(resp)
        assert isinstance(result, dict)
