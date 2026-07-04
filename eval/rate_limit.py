"""Retry-with-exponential-backoff for eval scripts.

Built in from the start per the eval methodology: 3 configs x ~30 tasks x 3-5 trials x multiple
Gemini calls each (agent turns + judge calls) is a lot of calls, which will hit 429s on the AI
Studio free tier. Every LLM-calling function in eval/ should go through with_retry.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_RATE_LIMIT_MARKERS = ("429", "RESOURCE_EXHAUSTED", "rate limit", "quota")


def is_rate_limit_error(exc: Exception) -> bool:
    """Whether `exc` looks like a rate-limit/quota error worth retrying, as opposed to a real
    failure (bad request, auth error, etc.) that retrying would just repeat pointlessly.
    """
    text = str(exc)
    return any(marker.lower() in text.lower() for marker in _RATE_LIMIT_MARKERS)


def with_retry(
    fn: Callable[[], T],
    max_attempts: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    label: str = "call",
) -> T:
    """Calls fn(), retrying with exponential backoff + jitter only on rate-limit-shaped errors.

    Non-rate-limit exceptions propagate immediately -- retrying a real bug just wastes time and
    hides the failure.
    """
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            is_last = attempt == max_attempts - 1
            if is_last or not is_rate_limit_error(exc):
                raise
            delay = min(max_delay, base_delay * (2**attempt)) + random.uniform(0, 1)
            print(
                f"[rate_limit] {label}: attempt {attempt + 1}/{max_attempts} hit "
                f"{exc.__class__.__name__}, retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
    raise RuntimeError("unreachable")  # pragma: no cover
