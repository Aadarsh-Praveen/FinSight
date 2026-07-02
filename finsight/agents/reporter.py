"""Writes the final structured, cited recommendation report.

Human-in-the-loop: before the report can call its recommendation "approved," it must call
propose_recommendation, which is wrapped with require_confirmation=True (ADK's built-in HITL
tool-confirmation pattern). On a normal single-turn run there is no pending confirmation from a
human yet, so the tool call comes back requiring approval -- the report must reflect that
("pending_human_confirmation"), not silently present the action as already approved.
"""

from __future__ import annotations

from google.adk import Agent
from google.adk.tools import FunctionTool

from finsight.agents.schemas import FinOpsReport
from finsight.config import settings
from finsight.guardrails import DEFAULT_AFTER_TOOL_CALLBACKS
from finsight.tools.finops_tools import propose_recommendation

INSTRUCTION = """
You are FinSight's reporter agent. You write the final brief for a FinOps stakeholder, using
only what's already in state: {plan}, {analyst_findings}, {forecast_result}, and {investigation}.
Do not invent any figure that isn't in that state.

If {verification?} is present in state, it is the verifier's critique of your PREVIOUS attempt at
this report -- it failed for the reasons listed there. Fix exactly those issues this time (e.g.
if it flagged an unsupported figure, only cite numbers that literally appear in state; if it
flagged confidence not matching the evidence, recompute confidence from
investigation.share_of_total_delta_pct per the rule below).

Steps:
1. Draft summary, root_cause, evidence, recommendation, and confidence:
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
2. Before finalizing, call propose_recommendation(recommendation=..., confidence=...) with the
   text you drafted. This call requires human confirmation and will not silently succeed on a
   fresh run -- read its result:
   - If it returns an error about requiring confirmation or being rejected, set
     recommendation_status to "pending_human_confirmation" (or "rejected" if explicitly
     rejected). Keep your drafted recommendation text as-is, but do NOT claim it has been acted
     on -- it is awaiting human approval.
   - If it returns status "approved", set recommendation_status to "approved".
"""


def build_reporter_agent() -> Agent:
    return Agent(
        name="reporter",
        model=settings.model_verifier,
        description="Synthesizes the final structured, cited FinOps report.",
        instruction=INSTRUCTION,
        tools=[FunctionTool(propose_recommendation, require_confirmation=True)],
        after_tool_callback=DEFAULT_AFTER_TOOL_CALLBACKS,
        output_schema=FinOpsReport,
        output_key="report",
    )
