"""Structured logging + local OpenTelemetry tracing for FinSight agent runs.

Two independent pieces, per Phase 8's observability goal:

1. **Structured JSONL logging of every tool call** -- `log_tool_call_start`/`log_tool_call_end`,
   an ADK before/after_tool_callback pair. Works everywhere immediately, no OTel setup required.
   One JSON line per completed tool call: agent name, tool name, argument keys (not values --
   avoid duplicating whatever the PII/injection guardrails already redact), latency, and whether
   the response looked like an error.
2. **Local OpenTelemetry spans**, via ADK's own `google.adk.telemetry.sqlite_span_exporter`
   (real, first-party ADK code -- not something built from scratch here). Captures ADK's internal
   LLM-call and tool-call spans to a local SQLite file, viewable with any SQLite browser or a
   simple `SELECT * FROM spans` -- the same shape of data Cloud Trace would show, without needing
   a deployed, billed GCP project. `adk run`/`adk web`'s own `--trace_to_cloud`/`--otel_to_cloud`
   flags require exactly that (see BUILD_PLAN.md Phase 8), which this project doesn't have until
   Phase 10's deploy step -- this is the honest local substitute, not a lesser version of the same
   thing wired differently.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("finsight.observability")

DEFAULT_TOOL_CALL_LOG_PATH = Path("finsight_tool_calls.jsonl")
DEFAULT_TRACE_DB_PATH = "finsight_traces.db"

_pending_calls: dict[tuple[str, str], float] = {}


def _call_key(tool_context: Any, tool: Any) -> tuple[str, str]:
    return (tool_context.invocation_id, getattr(tool, "name", str(tool)))


def log_tool_call_start(tool: Any, args: dict[str, Any], tool_context: Any) -> None:
    """ADK before_tool_callback: records a start time for latency measurement.

    Never short-circuits the call -- always returns None.
    """
    _pending_calls[_call_key(tool_context, tool)] = time.time()
    return None


def log_tool_call_end(
    tool: Any, args: dict[str, Any], tool_context: Any, tool_response: Any
) -> None:
    """ADK after_tool_callback: appends one structured JSON line for the completed tool call.

    Never replaces the response -- always returns None.
    """
    start = _pending_calls.pop(_call_key(tool_context, tool), None)
    latency_ms = round((time.time() - start) * 1000, 1) if start is not None else None
    record = {
        "timestamp": time.time(),
        "agent": tool_context.agent_name,
        "tool": getattr(tool, "name", str(tool)),
        "arg_keys": sorted(args.keys()),
        "latency_ms": latency_ms,
        "looks_like_error": bool(isinstance(tool_response, dict) and tool_response.get("error")),
    }
    try:
        with open(DEFAULT_TOOL_CALL_LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        logger.warning("Could not write tool-call log entry", exc_info=True)
    return None


_tracing_enabled = False


def enable_local_tracing(db_path: str = DEFAULT_TRACE_DB_PATH) -> None:
    """Registers a global OTel TracerProvider backed by ADK's local SqliteSpanExporter.

    Idempotent -- safe to call more than once per process (e.g. once per eval trial subprocess).
    """
    global _tracing_enabled
    if _tracing_enabled:
        return

    from google.adk.telemetry.sqlite_span_exporter import SqliteSpanExporter
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(SqliteSpanExporter(db_path=db_path)))
    trace.set_tracer_provider(provider)
    _tracing_enabled = True
