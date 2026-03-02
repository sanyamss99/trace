"""Tests for usetrace.capture.locals."""

from usetrace.capture.locals import MAX_DICT_KEYS, MAX_LIST_ITEMS, MAX_STRING_LENGTH, capture_locals


def _sample_func(a: int, b: str, c: float = 3.14) -> None:
    pass


def test_captures_positional_and_keyword_args() -> None:
    result = capture_locals(_sample_func, (1, "hello"), {"c": 2.71})
    assert result == {"a": 1, "b": "hello", "c": 2.71}


def test_captures_defaults() -> None:
    result = capture_locals(_sample_func, (1, "hello"), {})
    assert result == {"a": 1, "b": "hello", "c": 3.14}


def test_truncates_long_strings() -> None:
    long_str = "x" * (MAX_STRING_LENGTH + 500)
    result = capture_locals(_sample_func, (1, long_str), {})
    assert len(result["b"]) < len(long_str)
    assert result["b"].endswith("...[truncated]")


def test_truncates_long_lists() -> None:
    def func(items: list[int]) -> None:
        pass

    big_list = list(range(100))
    result = capture_locals(func, (big_list,), {})
    assert len(result["items"]) == MAX_LIST_ITEMS + 1  # items + truncation marker
    assert "more items" in result["items"][-1]


def test_truncates_large_dicts() -> None:
    def func(data: dict[str, int]) -> None:
        pass

    big_dict = {f"key_{i}": i for i in range(50)}
    result = capture_locals(func, (big_dict,), {})
    assert len(result["data"]) == MAX_DICT_KEYS + 1  # keys + truncation marker
    assert "__truncated__" in result["data"]


def test_handles_primitives() -> None:
    def func(a: int, b: float, c: bool, d: None) -> None:
        pass

    result = capture_locals(func, (42, 3.14, True, None), {})
    assert result == {"a": 42, "b": 3.14, "c": True, "d": None}


def test_handles_non_serializable_objects() -> None:
    class CustomObj:
        pass

    def func(obj: object) -> None:
        pass

    result = capture_locals(func, (CustomObj(),), {})
    assert "CustomObj" in result["obj"]


def test_never_raises_on_bad_input() -> None:
    """The capture function must never raise, even with pathological input."""
    # Not a callable with a valid signature
    result = capture_locals(42, (1, 2), {})  # type: ignore[arg-type]
    assert result == {}


def test_never_raises_on_mismatched_args() -> None:
    result = capture_locals(_sample_func, (1,), {})  # missing required 'b'
    assert result == {}
