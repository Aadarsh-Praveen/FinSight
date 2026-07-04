"""Decomposes the question into an ordered analysis plan (which tools, which periods)."""

from __future__ import annotations

from google.adk import Agent

from finsight.agents.schemas import InvestigationPlan
from finsight.config import settings
from finsight.guardrails import DEFAULT_AFTER_TOOL_CALLBACKS, sql_readonly_guardrail
from finsight.observability import log_tool_call_end, log_tool_call_start
from finsight.tools.mcp_bigquery import load_tools

INSTRUCTION = """
You are FinSight's planner agent. Your only job is to turn the user's question into two
concrete, equal-length date ranges to compare: a current_period and a prior_period (the same
number of days, immediately preceding current_period).

Steps:
1. Call get_dataset_date_range to find the dataset's actual earliest_date and latest_date. Do
   NOT assume "today" -- this dataset does not necessarily extend to the present, and you have
   no other way to know its real coverage.
2. Interpret the question's time reference relative to latest_date, not "today":
   - If the question names an explicit range, use it directly (clamped to
     [earliest_date, latest_date]).
   - If the question says something relative like "last month" or "the prior period" with no
     other anchor, default current_period to the 30 days ending on latest_date (inclusive), and
     prior_period to the 30 days immediately before that (also inclusive, same length).
3. Output both ranges, the original question verbatim, and a one-sentence reasoning for how you
   picked the dates.

Only call get_dataset_date_range. Do not call any other tool.
"""


def build_planner_agent() -> Agent:
    return Agent(
        name="planner",
        model=settings.model_worker,
        description="Turns the user's question into a current_period/prior_period date-range "
        "plan, grounded in the dataset's real date coverage.",
        instruction=INSTRUCTION,
        tools=load_tools("get_dataset_date_range"),
        before_tool_callback=[sql_readonly_guardrail, log_tool_call_start],
        after_tool_callback=[*DEFAULT_AFTER_TOOL_CALLBACKS, log_tool_call_end],
        output_schema=InvestigationPlan,
        output_key="plan",
    )
