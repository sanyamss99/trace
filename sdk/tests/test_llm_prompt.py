"""Tests for LLM prompt extraction from call arguments."""

from usetrace.capture.llm_prompt import extract_llm_prompt


def test_openai_messages() -> None:
    """OpenAI-style messages kwarg produces prompt text with role markers."""
    kwargs = {
        "messages": [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is 2+2?"},
        ],
        "model": "gpt-4o",
    }
    result = extract_llm_prompt((), kwargs)
    assert result is not None
    assert "[system]" in result
    assert "You are helpful." in result
    assert "[user]" in result
    assert "What is 2+2?" in result


def test_anthropic_separate_system() -> None:
    """Anthropic-style separate system kwarg is prepended."""
    kwargs = {
        "messages": [{"role": "user", "content": "Hello"}],
        "system": "Be concise.",
        "model": "claude-3-opus-20240229",
    }
    result = extract_llm_prompt((), kwargs)
    assert result is not None
    assert "Be concise." in result
    assert "Hello" in result
    # System should appear before user content
    assert result.index("Be concise.") < result.index("Hello")


def test_raw_prompt_kwarg() -> None:
    """Raw prompt= kwarg is returned as-is."""
    result = extract_llm_prompt((), {"prompt": "Once upon a time"})
    assert result == "Once upon a time"


def test_gemini_contents_kwarg() -> None:
    """Gemini-style contents= kwarg is extracted."""
    result = extract_llm_prompt((), {"contents": "Tell me about Python"})
    assert result == "Tell me about Python"


def test_positional_string_arg() -> None:
    """First positional string arg (Gemini style) is extracted."""
    result = extract_llm_prompt(("Tell me a story",), {})
    assert result == "Tell me a story"


def test_no_prompt_found() -> None:
    """Returns None when no recognizable prompt pattern."""
    result = extract_llm_prompt((), {"temperature": 0.7})
    assert result is None


def test_empty_args() -> None:
    """Returns None for empty args and kwargs."""
    result = extract_llm_prompt((), {})
    assert result is None


def test_multipart_content_blocks() -> None:
    """Handles Anthropic-style multi-part content blocks."""
    kwargs = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image."},
                    {"type": "image", "source": {"data": "..."}},
                ],
            },
        ],
    }
    result = extract_llm_prompt((), kwargs)
    assert result is not None
    assert "Describe this image." in result


def test_messages_priority_over_prompt() -> None:
    """Messages kwarg takes priority over prompt kwarg."""
    kwargs = {
        "messages": [{"role": "user", "content": "from messages"}],
        "prompt": "from prompt kwarg",
    }
    result = extract_llm_prompt((), kwargs)
    assert result is not None
    assert "from messages" in result


def test_empty_messages_falls_through() -> None:
    """Empty messages list falls through to next detection."""
    result = extract_llm_prompt((), {"messages": [], "prompt": "fallback"})
    assert result == "fallback"


def test_multiple_turns() -> None:
    """Multiple chat turns are all captured."""
    kwargs = {
        "messages": [
            {"role": "system", "content": "You are a tutor."},
            {"role": "user", "content": "What is gravity?"},
            {"role": "assistant", "content": "Gravity is a force."},
            {"role": "user", "content": "Tell me more."},
        ],
    }
    result = extract_llm_prompt((), kwargs)
    assert result is not None
    assert "tutor" in result
    assert "gravity" in result.lower()
    assert "Tell me more." in result
