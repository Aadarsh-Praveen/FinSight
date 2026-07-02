"""Security callbacks wired onto agents: read-only SQL, PII redaction, injection scanning."""

from finsight.guardrails.injection_guard import injection_guard_callback
from finsight.guardrails.pii_redaction import pii_redaction_guardrail
from finsight.guardrails.sql_readonly import sql_readonly_guardrail

DEFAULT_AFTER_TOOL_CALLBACKS = [pii_redaction_guardrail, injection_guard_callback]

__all__ = [
    "sql_readonly_guardrail",
    "pii_redaction_guardrail",
    "injection_guard_callback",
    "DEFAULT_AFTER_TOOL_CALLBACKS",
]
