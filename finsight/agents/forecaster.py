"""Computes a trailing-average baseline forecast for expected vs actual revenue.

Deliberately not BigQuery AI.FORECAST/TimesFM: a fast, deterministic, dependency-free baseline
is easier to reason about and to reproduce in the Phase 9 eval harness. See BUILD_PLAN.md's
risk register, which explicitly sanctions this fallback.
"""

from __future__ import annotations

from google.adk import Agent

from finsight.agents.schemas import ForecastResult
from finsight.config import settings
from finsight.tools.finops_tools import compute_baseline_forecast
from finsight.tools.mcp_bigquery import load_tools

INSTRUCTION = """
You are FinSight's forecaster agent. You compute a simple baseline "expected" revenue for the
current period and compare it to what actually happened, using {plan} and {analyst_findings}
already in state.

Steps:
1. Read {plan} for the prior_period date range (start_date, end_date).
2. Call get_daily_sales for that exact prior_period range to get daily revenue figures.
3. Call compute_baseline_forecast with those daily revenue values and projection_days equal to
   the number of days in current_period (same length as prior_period, per {plan}).
4. Compare the resulting expected_total against {analyst_findings}'s current.revenue (the
   actual). Output expected_current_revenue, actual_current_revenue, surprise (actual -
   expected), surprise_pct (surprise / expected * 100, or 0 if expected is 0), and the method
   string returned by the tool.

This is a trailing-average baseline, not a true forecasting model -- treat it as a sanity check
for "was this period unusually high or low vs. its own recent trend," not a precise prediction.
"""


def build_forecaster_agent() -> Agent:
    return Agent(
        name="forecaster",
        model=settings.model_worker,
        description="Computes a trailing-average baseline forecast and compares it to actual "
        "current-period revenue.",
        instruction=INSTRUCTION,
        tools=[*load_tools("get_daily_sales"), compute_baseline_forecast],
        output_schema=ForecastResult,
        output_key="forecast_result",
    )
