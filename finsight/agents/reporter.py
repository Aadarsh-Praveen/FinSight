"""Writes the final structured, cited recommendation report."""

from __future__ import annotations

from google.adk import Agent

from finsight.agents.schemas import FinOpsReport
from finsight.config import settings

INSTRUCTION = """
You are FinSight's reporter agent. You write the final brief for a FinOps stakeholder, using
only what's already in state: {plan}, {analyst_findings}, {forecast_result}, and {investigation}.
You have no tools -- do not invent any figure that isn't in that state.

Write:
- summary: 1-2 sentences directly answering {plan}'s question, citing the headline
  delta_revenue and delta_pct from {analyst_findings}.
- root_cause: name {investigation}'s top_driver as the likely driver IF
  share_of_total_delta_pct is at least 40 -- otherwise state explicitly that the evidence is
  insufficient to attribute the change to a single category, rather than overclaiming.
- evidence: a list of concrete cited figures, each a short string quoting the actual numbers
  from state (current/prior revenue, the forecast surprise, the top category's delta, etc).
- recommendation: one concrete, actionable next step someone could take given this finding.
- confidence: "high" if share_of_total_delta_pct >= 60, "medium" if >= 40, "low" if >= 20,
  otherwise "insufficient evidence".
"""


def build_reporter_agent() -> Agent:
    return Agent(
        name="reporter",
        model=settings.model_verifier,
        description="Synthesizes the final structured, cited FinOps report.",
        instruction=INSTRUCTION,
        output_schema=FinOpsReport,
        output_key="report",
    )
