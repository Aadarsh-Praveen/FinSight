"""Root router: composes the plan -> pull -> forecast -> investigate -> report graph.

TODO(Phase 7): route verifier fail -> retry loop; pass -> reporter finalizes.
"""

from __future__ import annotations

from google.adk.agents import SequentialAgent

from finsight.agents.analyst import build_analyst_agent
from finsight.agents.forecaster import build_forecaster_agent
from finsight.agents.investigator import build_investigator_agent
from finsight.agents.planner import build_planner_agent
from finsight.agents.reporter import build_reporter_agent


def build_orchestrator_agent() -> SequentialAgent:
    return SequentialAgent(
        name="orchestrator",
        description="Investigates a revenue question end-to-end: plans comparison periods, "
        "pulls the top-line delta, computes a baseline forecast, finds the likely category "
        "driver, and writes a cited FinOps report.",
        sub_agents=[
            build_planner_agent(),
            build_analyst_agent(),
            build_forecaster_agent(),
            build_investigator_agent(),
            build_reporter_agent(),
        ],
    )


root_agent = build_orchestrator_agent()
