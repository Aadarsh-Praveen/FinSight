"""Critic: groundedness / sufficiency / policy check before output.

Sits at the end of the retry loop in the orchestrator (finsight/agents/orchestrator.py): given
the draft {report} and the state it should be grounded in, decide pass/fail. On pass, an
after_agent_callback (not the model calling a tool -- see below) escalates to stop the LoopAgent;
on fail, the loop retries analyst -> forecaster -> investigator -> reporter with this agent's
critique available in state.

Why not ADK's exit_loop tool: exit_loop sets tool_context.actions.skip_summarization = True,
which is meant for critics whose only output IS the tool call. But it also suppresses the
model's next turn entirely -- including the turn that would produce this agent's own
output_schema JSON. In testing, that meant `verification` never got saved to state on the pass
path (only on fail, when exit_loop is never called). Deciding escalation deterministically from
the already-parsed VerifierResult, in Python, sidesteps that interaction entirely and is more
robust than trusting the model to both call a tool and still remember to answer in schema.
"""

from __future__ import annotations

from typing import Any

from google.adk import Agent

from finsight.agents.schemas import VerifierResult
from finsight.config import settings
from finsight.guardrails import DEFAULT_AFTER_TOOL_CALLBACKS
from finsight.observability import log_tool_call_end, log_tool_call_start
from finsight.tools.finops_tools import check_text_for_policy_violations

INSTRUCTION = """
You are FinSight's verifier agent, a critic that checks the draft report before it is shown to
anyone. Check {report} (the draft) against {plan}, {analyst_findings}, {forecast_result}, and
{investigation} (the source of truth), plus any prior {verification?} critique from an earlier
attempt.

Perform exactly three checks:

1. GROUNDEDNESS: every number in {report}.evidence and the claim in {report}.root_cause must be
   traceable to a figure that actually appears in {analyst_findings}, {forecast_result}, or
   {investigation} (reasonable rounding is fine; a fabricated or materially different number is
   not). If anything is unsupported, groundedness_ok = false and name the specific figure in
   issues.
2. SUFFICIENCY: {report}.confidence must be consistent with
   {investigation}.share_of_total_delta_pct: "high" requires >= 60, "medium" requires >= 40,
   "low" requires >= 20, otherwise it must be "insufficient evidence". If {report}.root_cause
   names a specific driver as the cause but the confidence/share don't support that,
   sufficiency_ok = false.
3. POLICY: call check_text_for_policy_violations once, passing the concatenation of
   {report}.summary, {report}.root_cause, and {report}.recommendation as `text`. If the result
   has pii_found=true or injection_found=true, policy_ok = false.

Set passed = groundedness_ok AND sufficiency_ok AND policy_ok. If passed is false, write a
specific, actionable critique in the critique field (e.g. "the $X figure in evidence does not
match any state value; recompute from analyst_findings") so the next attempt can fix exactly
what's wrong. If passed is true, critique should briefly confirm why.
"""


def _escalate_when_verification_passed(callback_context: Any) -> None:
    """after_agent_callback: stops the retry loop once {verification}.passed is true.

    Setting callback_context.state also (not just .actions.escalate) is required: the
    surrounding framework only emits an event carrying this callback's actions if either the
    callback returns Content or the state has a delta (see base_agent.py's
    _handle_after_agent_callback) -- escalate alone, with no state write, would silently vanish.
    """
    verification = callback_context.state.get("verification")
    if verification and verification.get("passed"):
        callback_context.state["verification_passed"] = True
        callback_context.actions.escalate = True
    return None


def build_verifier_agent() -> Agent:
    return Agent(
        name="verifier",
        model=settings.model_verifier,
        description="Checks the draft report for groundedness, sufficiency, and policy "
        "compliance before it's finalized; ends the retry loop on pass.",
        instruction=INSTRUCTION,
        tools=[check_text_for_policy_violations],
        before_tool_callback=log_tool_call_start,
        after_tool_callback=[*DEFAULT_AFTER_TOOL_CALLBACKS, log_tool_call_end],
        after_agent_callback=_escalate_when_verification_passed,
        output_schema=VerifierResult,
        output_key="verification",
    )
