"""ADK entrypoint: defines `root_agent` for `adk run finsight` / `adk web`."""

from finsight.agents.orchestrator import root_agent

__all__ = ["root_agent"]
