"""Correlates the delta with drivers; names the likely root cause by dimension."""

from __future__ import annotations

from google.adk import Agent

from finsight.agents.schemas import DriverFinding
from finsight.config import settings
from finsight.guardrails import DEFAULT_AFTER_TOOL_CALLBACKS, sql_readonly_guardrail
from finsight.tools.mcp_bigquery import load_tools

INSTRUCTION = """
You are FinSight's investigator agent. Given {plan} and {analyst_findings} (the overall
current-vs-prior revenue delta) already in state, find which product category is driving that
delta.

Steps:
1. Read {plan} for current_period and prior_period date ranges.
2. Call get_orders_by_category once for current_period and once for prior_period.
3. For every category that appears in either result, compute delta_revenue = current_revenue -
   prior_revenue (treat a category missing from a period's results as 0 revenue for that
   period).
4. Sort categories by |delta_revenue| descending. The top one is top_driver.
5. Compute share_of_total_delta_pct = top_driver's delta_revenue / analyst_findings.delta_revenue
   * 100 (if analyst_findings.delta_revenue is 0, report 0).
6. Output dimension="category", top_driver, top_driver_delta, share_of_total_delta_pct, and the
   full sorted breakdown (all categories).
"""


def build_investigator_agent() -> Agent:
    return Agent(
        name="investigator",
        model=settings.model_worker,
        description="Breaks the revenue delta down by product category to name the likely "
        "driver.",
        instruction=INSTRUCTION,
        tools=load_tools("get_orders_by_category"),
        before_tool_callback=sql_readonly_guardrail,
        after_tool_callback=DEFAULT_AFTER_TOOL_CALLBACKS,
        output_schema=DriverFinding,
        output_key="investigation",
    )
