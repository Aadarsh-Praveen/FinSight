"""Writes the final structured, cited recommendation report.

Human-in-the-loop: before the report can call its recommendation "approved," it must call
propose_recommendation, which is wrapped with require_confirmation=True (ADK's built-in HITL
tool-confirmation pattern). On a normal single-turn run there is no pending confirmation from a
human yet, so the tool call comes back requiring approval -- the report must reflect that
("pending_human_confirmation"), not silently present the action as already approved.
"""

from __future__ import annotations

from pathlib import Path

from google.adk import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools import FunctionTool
from google.adk.tools.skill_toolset import SkillToolset

from finsight.agents.schemas import FinOpsReport
from finsight.config import settings
from finsight.guardrails import DEFAULT_AFTER_TOOL_CALLBACKS
from finsight.memory.session import build_load_memory_tool
from finsight.observability import log_tool_call_end, log_tool_call_start
from finsight.tools.finops_tools import propose_recommendation

_SKILLS_DIR = Path(__file__).parent.parent / "skills"
_SKILL_NAMES = ("anomaly-triage", "driver-attribution-calibration", "seasonality-check")


def _load_finsight_skills() -> list:
    return [load_skill_from_dir(_SKILLS_DIR / name) for name in _SKILL_NAMES]

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
1. Before drafting, consider whether a skill applies, and load it if so: `anomaly-triage` for the
   general order of checks before naming a cause, `driver-attribution-calibration` for the exact
   confidence-tier thresholds (authoritative -- use this instead of recomputing thresholds from
   memory), and `seasonality-check` when the top driver category has an obvious seasonal story.
2. Draft summary, root_cause, evidence, recommendation, and confidence:
   - summary: 1-2 sentences directly answering {plan}'s question, citing the headline
     delta_revenue and delta_pct from {analyst_findings}.
   - root_cause: name {investigation}'s top_driver as the likely driver IF
     share_of_total_delta_pct is at least 40 -- otherwise state explicitly that the evidence is
     insufficient to attribute the change to a single category, rather than overclaiming.
   - evidence: a list of concrete cited figures, each a short string quoting the actual numbers
     from state (current/prior revenue, the forecast surprise, the top category's delta, etc).
   - recommendation: one concrete, actionable next step someone could take given this finding.
     If {investigation} names a top_driver, call load_memory(query=top_driver's category name)
     to check org-context memory for a category owner; if found, address the recommendation to
     that owner by name. If not found, give the recommendation without a named owner -- do not
     invent one.
   - confidence: per the `driver-attribution-calibration` skill's thresholds (high >= 60,
     medium >= 40, low >= 20, otherwise insufficient evidence, all against
     investigation.share_of_total_delta_pct).
3. Before finalizing, call propose_recommendation(recommendation=..., confidence=...) with the
   text you drafted. This call requires human confirmation and will not silently succeed on a
   fresh run -- read its result:
   - If it returns an error about requiring confirmation or being rejected, set
     recommendation_status to "pending_human_confirmation" (or "rejected" if explicitly
     rejected). Keep your drafted recommendation text as-is, but do NOT claim it has been acted
     on -- it is awaiting human approval.
   - If it returns status "approved", set recommendation_status to "approved".
"""


def build_reporter_agent(require_confirmation: bool = True) -> Agent:
    """Builds the reporter.

    Args:
        require_confirmation: gate propose_recommendation behind ADK's HITL tool-confirmation
            (the real product behavior, default True). Set False for automated contexts with no
            human to approve -- e.g. eval/run_eval.py -- where every run would otherwise pause on
            propose_recommendation's first call.

            Resuming that pause used to be broken for confirmations raised inside a nested
            SequentialAgent>LoopAgent>LlmAgent hierarchy -- approving would restart the whole
            orchestrator from `planner` and fail to resolve the tool against the right agent. This
            is now fixed for the real app: `finsight/agent.py` wraps `root_agent` in an ADK `App`
            with `ResumabilityConfig(is_resumable=True)`, which lets both `SequentialAgent` and
            `LoopAgent` correctly resume at the sub-agent that actually raised the confirmation
            (verified live, in production, with a real confirm -> approve -> resume round trip --
            see PROGRESS.md). eval/ still uses `require_confirmation=False` regardless -- its
            Runner is built directly from `build_orchestrator_agent(...)`, bypassing the `App`
            wrapper entirely, by design (automated runs have no human available to approve, and
            eval scores report *content*, not the separate HITL mechanism, which has its own
            dedicated tests) -- not because the underlying resume bug still exists.
    """
    return Agent(
        name="reporter",
        model=settings.model_verifier,
        description="Synthesizes the final structured, cited FinOps report.",
        instruction=INSTRUCTION,
        tools=[
            FunctionTool(propose_recommendation, require_confirmation=require_confirmation),
            SkillToolset(skills=_load_finsight_skills()),
            build_load_memory_tool(),
        ],
        before_tool_callback=log_tool_call_start,
        after_tool_callback=[*DEFAULT_AFTER_TOOL_CALLBACKS, log_tool_call_end],
        output_schema=FinOpsReport,
        output_key="report",
    )
