"""ADK entrypoint: defines `root_agent` for `adk run finsight` / `adk web`.

TODO(Phase 5): switch root_agent to the orchestrator (full multi-agent graph).
"""

from finsight.agents.analyst import root_agent

__all__ = ["root_agent"]
