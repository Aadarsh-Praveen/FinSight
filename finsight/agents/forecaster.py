"""Computes an "expected" revenue forecast for the current period and compares it to actual.

Uses BigQuery's AI.FORECAST (TimesFM) as the primary method, with an automatic fallback to a
deterministic trailing-average baseline if AI.FORECAST errors, times out, or is otherwise
unavailable -- see finsight/tools/finops_tools.py::compute_timesfm_forecast for the fallback
logic (baked into the tool itself, not left to the agent to notice a failure and retry).

The deterministic baseline was the sole method through Phase 9's ablation (see PROGRESS.md and
BUILD_PLAN.md's risk register for why it was chosen initially: fast, dependency-free, easy to
reproduce). AI.FORECAST was verified live before being wired in here: a ~30-point daily series
returns a sane forecast whose prediction interval actually contained the real subsequent outcome
in testing, and it costs a negligible fraction of a cent per call. This upgrade happened after
the Phase 9 ablation -- FINDINGS.md's reported numbers reflect the deterministic baseline, and
the benchmark doesn't score forecast accuracy either way, so nothing reported there changes.
"""

from __future__ import annotations

from google.adk import Agent

from finsight.agents.schemas import ForecastResult
from finsight.config import settings
from finsight.guardrails import DEFAULT_AFTER_TOOL_CALLBACKS, sql_readonly_guardrail
from finsight.observability import log_tool_call_end, log_tool_call_start
from finsight.tools.finops_tools import compute_timesfm_forecast
from finsight.tools.mcp_bigquery import load_tools

INSTRUCTION = """
You are FinSight's forecaster agent. You compute an "expected" revenue forecast for the current
period and compare it to what actually happened, using {plan} and {analyst_findings} already in
state.

Steps:
1. Read {plan} for the prior_period date range (start_date, end_date).
2. Call get_daily_sales for that exact prior_period range to get daily revenue figures.
3. Call compute_timesfm_forecast with the daily series returned by get_daily_sales (pass the rows
   through as-is) and projection_days equal to the number of days in current_period (same length
   as prior_period, per {plan}).
4. Compare the resulting expected_total against {analyst_findings}'s current.revenue (the
   actual). Output expected_current_revenue, actual_current_revenue, surprise (actual -
   expected), surprise_pct (surprise / expected * 100, or 0 if expected is 0), and the method
   string returned by the tool verbatim -- it states which forecasting method actually ran
   (AI.FORECAST or the trailing-average fallback), so don't paraphrase or drop it.

Treat this as a sanity check for "was this period unusually high or low vs. its own recent
trend," not a guaranteed-precise prediction -- state your confidence accordingly rather than
treating the forecast as certain.
"""


def build_forecaster_agent() -> Agent:
    return Agent(
        name="forecaster",
        model=settings.model_worker,
        description="Forecasts expected current-period revenue (AI.FORECAST/TimesFM, with a "
        "deterministic fallback) and compares it to what actually happened.",
        instruction=INSTRUCTION,
        tools=[*load_tools("get_daily_sales"), compute_timesfm_forecast],
        before_tool_callback=[sql_readonly_guardrail, log_tool_call_start],
        after_tool_callback=[*DEFAULT_AFTER_TOOL_CALLBACKS, log_tool_call_end],
        output_schema=ForecastResult,
        output_key="forecast_result",
    )
