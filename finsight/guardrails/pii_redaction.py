"""Redacts obvious PII (emails, names) from tool outputs before they reach the model/report.

None of FinSight's current BigQuery tools select PII columns (no email/name fields are in any
`SELECT` in tools.yaml), so there's no live PII leak path today. This is defense-in-depth for
if a future tool ever touches a table with customer PII (thelook_ecommerce.users has email,
first_name, last_name): redact recognizable emails anywhere in tool output text, and blank out
any dict field whose key names commonly hold PII, regardless of its content.
"""

from __future__ import annotations

import re
from typing import Any

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+")
REDACTED_EMAIL = "[REDACTED_EMAIL]"
REDACTED_FIELD = "[REDACTED]"

PII_FIELD_NAMES = {
    "email",
    "email_address",
    "first_name",
    "last_name",
    "full_name",
    "name",
    "customer_name",
    "user_name",
    "username",
}


def redact_pii(value: Any, key: str | None = None) -> Any:
    """Recursively redacts PII in a tool result, preserving its overall shape."""
    if isinstance(value, str):
        if key and key.lower() in PII_FIELD_NAMES:
            return REDACTED_FIELD
        return EMAIL_PATTERN.sub(REDACTED_EMAIL, value)
    if isinstance(value, dict):
        return {k: redact_pii(v, key=k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_pii(v) for v in value]
    return value


def pii_redaction_guardrail(
    tool: Any, args: dict[str, Any], tool_context: Any, tool_response: Any
) -> Any | None:
    """ADK after_tool_callback: redacts PII from a tool's response before the model sees it.

    Returning a non-None value replaces the tool's response with the redacted version;
    returning None leaves the original response untouched (nothing needed redaction).
    """
    redacted = redact_pii(tool_response)
    if redacted != tool_response:
        return redacted
    return None
