"""Loads the MCP Toolbox toolset into ADK via toolbox-core's ToolboxSyncClient."""

from __future__ import annotations

from toolbox_core import ToolboxSyncClient
from toolbox_core.sync_tool import ToolboxSyncTool

from finsight.config import settings

FINOPS_READONLY_TOOLSET = "finops_readonly"

_client: ToolboxSyncClient | None = None


def get_toolbox_client() -> ToolboxSyncClient:
    """Returns a process-wide ToolboxSyncClient, creating it on first use.

    Kept alive for the process lifetime: each loaded tool calls back through this
    client's background event loop, so it must not be closed while tools are in use.
    """
    global _client
    if _client is None:
        _client = ToolboxSyncClient(settings.toolbox_url)
    return _client


def load_finops_readonly_tools() -> list[ToolboxSyncTool]:
    """Loads the full finops_readonly toolset: read-only, parameterized BigQuery tools.

    Requires the MCP Toolbox server (see mcp-toolbox/README.md) to be running at
    settings.toolbox_url.
    """
    return get_toolbox_client().load_toolset(FINOPS_READONLY_TOOLSET)


def load_tools(*names: str) -> list[ToolboxSyncTool]:
    """Loads specific tools by name (least-privilege alternative to the full toolset).

    Use this for graph sub-agents that only need one or two of the finops_readonly tools,
    rather than handing every agent the entire toolset.
    """
    client = get_toolbox_client()
    return [client.load_tool(name) for name in names]
