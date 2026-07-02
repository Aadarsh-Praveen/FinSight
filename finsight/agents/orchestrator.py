"""Root router: composes the plan -> [pull -> forecast -> investigate -> report -> verify]* graph.

The bracketed steps run inside a bounded LoopAgent: verifier's after_agent_callback escalates
(stops the loop) once {verification}.passed is true; on fail, the loop retries
analyst -> forecaster -> investigator -> reporter with the verifier's critique available in
state (reporter reads {verification?}). `planner` runs once, outside the loop -- a bad
root-cause claim is a reporter/investigator problem far more often than a bad date-range choice,
so replanning on every retry would be wasted work.

Note: SequentialAgent and LoopAgent are both deprecated in the installed google-adk (2.3.0) in
favor of google.adk.Workflow, a graph API (nodes/edges/conditional routing). Kept the
deprecated-but-working primitives here rather than migrating, given the Phase 9 eval harness is
the higher-priority remaining work under the deadline -- see PROGRESS.md Phase 7 for the
migration path if revisited.
"""

from __future__ import annotations

from google.adk.agents import LoopAgent, SequentialAgent

from finsight.agents.analyst import build_analyst_agent
from finsight.agents.forecaster import build_forecaster_agent
from finsight.agents.investigator import build_investigator_agent
from finsight.agents.planner import build_planner_agent
from finsight.agents.reporter import build_reporter_agent
from finsight.agents.verifier import build_verifier_agent

MAX_VERIFICATION_ATTEMPTS = 3


def build_orchestrator_agent() -> SequentialAgent:
    investigate_and_verify_loop = LoopAgent(
        name="investigate_and_verify_loop",
        description="Pulls data, forecasts, investigates, drafts a report, and verifies it; "
        "retries (bounded) on verification failure.",
        max_iterations=MAX_VERIFICATION_ATTEMPTS,
        sub_agents=[
            build_analyst_agent(),
            build_forecaster_agent(),
            build_investigator_agent(),
            build_reporter_agent(),
            build_verifier_agent(),
        ],
    )
    return SequentialAgent(
        name="orchestrator",
        description="Investigates a revenue question end-to-end: plans comparison periods, "
        "then pulls/forecasts/investigates/reports/verifies in a bounded retry loop until the "
        "verifier passes the draft or the retry budget is exhausted.",
        sub_agents=[
            build_planner_agent(),
            investigate_and_verify_loop,
        ],
    )


root_agent = build_orchestrator_agent()
