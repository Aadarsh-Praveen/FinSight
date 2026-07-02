"""NL -> SQL over BigQuery via MCP Toolbox (read-only tools).

Phase 5 role: analyst is the top-line data-pull node in the orchestrator graph -- given
{plan}'s current/prior date ranges, it pulls the overall revenue delta. Category-level and
daily breakdowns are handled by the investigator and forecaster nodes respectively, so this
agent only needs one tool.
"""

from __future__ import annotations

from google.adk import Agent

from finsight.agents.schemas import AnalystFindings
from finsight.config import settings
from finsight.guardrails import DEFAULT_AFTER_TOOL_CALLBACKS, sql_readonly_guardrail
from finsight.tools.mcp_bigquery import load_tools

INSTRUCTION = """
You are FinSight's analyst agent. Given {plan} (current_period and prior_period date ranges)
already in state, pull the top-line revenue and order-count figures for both periods.

Steps:
1. Read {plan} for current_period and prior_period.
2. Call compare_period_over_period with current_start/current_end/prior_start/prior_end from
   {plan}.
3. Output current and prior PeriodFigures, delta_revenue (current.revenue - prior.revenue), and
   delta_pct (delta_revenue / prior.revenue * 100, rounded to 2 decimal places; if
   prior.revenue is 0, report delta_pct as 0).
"""


def build_analyst_agent() -> Agent:
    return Agent(
        name="analyst",
        model=settings.model_worker,
        description="Pulls the top-line current-vs-prior revenue delta for the planned periods.",
        instruction=INSTRUCTION,
        tools=load_tools("compare_period_over_period"),
        before_tool_callback=sql_readonly_guardrail,
        after_tool_callback=DEFAULT_AFTER_TOOL_CALLBACKS,
        output_schema=AnalystFindings,
        output_key="analyst_findings",
    )
