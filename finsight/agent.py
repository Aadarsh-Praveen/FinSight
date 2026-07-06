"""ADK entrypoint: defines `app` for `adk run finsight` / `adk web`.

Wrapped in an ADK `App` with `resumability_config` enabled -- this is what lets a paused
human-in-the-loop tool confirmation (see finsight/agents/reporter.py's `propose_recommendation`)
resume correctly at the sub-agent that actually raised it, instead of ADK restarting the whole
`SequentialAgent(planner, LoopAgent(...))` graph from `planner` on the next invocation. Both
`SequentialAgent` and `LoopAgent` already have the matching resume-state logic
(`current_sub_agent` tracking); it's only gated behind `is_resumable`, which defaults to False
unless the root agent is wrapped exactly like this. See PROGRESS.md for the full root-cause trace
and the confirm/approve/resume test this was validated against before merging.

Must be named `app` (not `root_agent`) -- ADK's CLI agent loader
(cli/utils/agent_loader.py::_load_from_submodule) specifically looks for an attribute named
`app` that `isinstance(..., App)`; a bare `root_agent` is only accepted if it's a plain
BaseAgent/BaseNode, which an App instance is neither. Confirmed by testing: naming it
`root_agent` produced a "No root_agent found for 'finsight'" error despite the module importing
and validating fine standalone.
"""

from google.adk.apps.app import App, ResumabilityConfig

from finsight.agents.orchestrator import root_agent as _root_agent

app = App(
    name="finsight",
    root_agent=_root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)

__all__ = ["app"]
