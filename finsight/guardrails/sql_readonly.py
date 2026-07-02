"""Blocks non-SELECT / DDL / DML SQL. Wired as an ADK before-tool callback.

Every real BigQuery tool in mcp-toolbox/tools.yaml is a fixed `bigquery-sql` statement with typed
named parameters, so an agent can never compose arbitrary SQL through them -- that's the primary
read-only guarantee (see the comment block at the top of tools.yaml). This module is a
defense-in-depth second layer that runs before any tool call:

1. Refuses to call any tool whose name suggests raw/arbitrary SQL execution (e.g. a hypothetical
   future `execute_sql` tool), so that guarantee is enforced in code, not just left as a comment
   telling future contributors not to add one to the toolset.
2. Scans every string-valued tool argument for SQL injection / multi-statement patterns, in case
   a malicious value is stuffed into an otherwise-innocuous parameter (e.g. a date field).
"""

from __future__ import annotations

import re
from typing import Any

BLOCKED_TOOL_NAME_SUBSTRINGS = (
    "execute_sql",
    "exec_sql",
    "run_sql",
    "raw_sql",
)

# Word-boundary match so e.g. a legitimate "updated_at"-style value doesn't false-positive,
# but "UPDATE orders SET ..." does.
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(drop|delete|insert|update|merge|alter|truncate|create|grant|revoke|exec|execute|call)\b",
    re.IGNORECASE,
)
_STATEMENT_SEPARATOR_OR_COMMENT = re.compile(r";|--|/\*|\*/")


def _string_values(args: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for value in args.values():
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, (list, tuple)):
            values.extend(v for v in value if isinstance(v, str))
    return values


def check_sql_injection(tool_name: str, args: dict[str, Any]) -> str | None:
    """Returns a violation reason if the call should be blocked, else None."""
    lowered_name = tool_name.lower()
    for pattern in BLOCKED_TOOL_NAME_SUBSTRINGS:
        if pattern in lowered_name:
            return (
                f"Tool '{tool_name}' is not permitted: raw/arbitrary SQL execution tools "
                "are disabled for this agent."
            )

    for value in _string_values(args):
        if _STATEMENT_SEPARATOR_OR_COMMENT.search(value):
            return (
                "Argument value rejected: contains a statement separator or SQL comment "
                f"marker: {value!r}"
            )
        match = _FORBIDDEN_KEYWORDS.search(value)
        if match:
            return (
                f"Argument value rejected: contains forbidden SQL keyword "
                f"'{match.group()}': {value!r}"
            )
    return None


def sql_readonly_guardrail(
    tool: Any, args: dict[str, Any], tool_context: Any
) -> dict[str, Any] | None:
    """ADK before_tool_callback: blocks calls that look like SQL injection or a write attempt.

    Returning a non-None dict short-circuits the real tool call and uses this dict as the tool's
    response; returning None lets the call proceed normally.
    """
    reason = check_sql_injection(getattr(tool, "name", str(tool)), args)
    if reason:
        return {"error": "blocked_by_sql_readonly_guardrail", "reason": reason}
    return None
