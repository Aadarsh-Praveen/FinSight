"""Heuristic scan of retrieved text for prompt-injection patterns (OWASP LLM01).

Tool results (not just direct user input) are a real injection vector: if a future tool ever
surfaces free-text data (a product review, a support ticket, a category name someone crafted),
an attacker could plant "ignore previous instructions" style text hoping the agent obeys it
instead of treating it as data. This scans every string in a tool's response and neutralizes any
match rather than passing it through to the model verbatim.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

NEUTRALIZED_MARKER = "[NEUTRALIZED_POSSIBLE_PROMPT_INJECTION]"

_INJECTION_PATTERNS = (
    re.compile(r"ignore (all |any )?(previous|prior|above) instructions", re.IGNORECASE),
    re.compile(
        r"disregard (the |all )?(system|previous|prior) (prompt|instructions)", re.IGNORECASE
    ),
    re.compile(r"\byou are now\b", re.IGNORECASE),
    re.compile(r"new instructions\s*:", re.IGNORECASE),
    re.compile(r"reveal (your|the) (system prompt|instructions)", re.IGNORECASE),
    re.compile(r"<\s*/?\s*tool_call", re.IGNORECASE),
    re.compile(r"^\s*system\s*:", re.IGNORECASE | re.MULTILINE),
)


def scan_for_injection(text: str) -> str | None:
    """Returns the matched pattern text if `text` looks like a prompt-injection attempt."""
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group()
    return None


def _neutralize(value: Any) -> Any:
    if isinstance(value, str):
        match = scan_for_injection(value)
        if match:
            logger.warning("Neutralized possible prompt injection in tool output: %r", match)
            return NEUTRALIZED_MARKER
        return value
    if isinstance(value, dict):
        return {k: _neutralize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_neutralize(v) for v in value]
    return value


def injection_guard_callback(
    tool: Any, args: dict[str, Any], tool_context: Any, tool_response: Any
) -> Any | None:
    """ADK after_tool_callback: neutralizes prompt-injection patterns in a tool's response.

    Returning a non-None value replaces the tool's response with the neutralized version;
    returning None leaves the original response untouched (nothing matched).
    """
    neutralized = _neutralize(tool_response)
    if neutralized != tool_response:
        return neutralized
    return None
