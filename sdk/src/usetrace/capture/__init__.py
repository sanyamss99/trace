"""Input/output capture logic."""

from usetrace.capture.llm_response import extract_llm_response
from usetrace.capture.locals import capture_locals

__all__ = ["capture_locals", "extract_llm_response"]
