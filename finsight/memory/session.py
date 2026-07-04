"""Session persistence and long-term memory for FinSight.

Two distinct pieces of Phase 8's "memory" concept:

1. Session persistence across runs -- handled by ADK's own real, built-in mechanism, not custom
   code: `adk run finsight --session_service_uri=sqlite://finsight_sessions.db` (or the CLI's
   default `--use_local_storage` behavior) persists conversation state across separate CLI
   invocations via `google.adk.sessions.SqliteSessionService`. No wiring needed here.
2. Org-context long-term memory (category -> owner) -- ADK's `BaseMemoryService` has no
   direct-write path for `InMemoryMemoryService` (only session/event-based ingestion, see
   `add_memory`'s NotImplementedError in the base class), so org context is seeded as a synthetic
   session ingested via `add_session_to_memory`, then made searchable via the same
   `search_memory`/`LoadMemoryTool` path a real investigation would use.

Known limitation, documented rather than glossed over: `InMemoryMemoryService` is process-local --
seeded context does not survive a process restart. A persistent alternative
(`VertexAiMemoryBankService` / `VertexAiRagMemoryService`) needs provisioned GCP resources this
project doesn't have pre-deploy (see PROGRESS.md's Phase 8 entry). For the CLI/demo, org-context
memory is demonstrated by seeding it once per process and querying it within that same run --
genuine use of the real ADK memory API, just not yet durable across process restarts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.adk.events.event import Event
from google.adk.memory import BaseMemoryService, InMemoryMemoryService
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types

_ORG_CONTEXT_PATH = Path(__file__).parent / "org_context.json"
_ORG_MEMORY_APP_NAME = "finsight-org-context"
_ORG_MEMORY_USER_ID = "org"


def build_memory_service() -> BaseMemoryService:
    """Returns the memory service FinSight wires into its Runner.

    In-memory, process-local (see module docstring for why, and the durability caveat).
    """
    return InMemoryMemoryService()


def load_org_context() -> dict[str, str]:
    """Reads the category -> owner map, skipping the `_comment` documentation key."""
    raw = json.loads(_ORG_CONTEXT_PATH.read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}


async def seed_org_context(
    memory_service: BaseMemoryService, session_service: BaseSessionService | None = None
) -> None:
    """Ingests the category->owner map into `memory_service` so `search_memory`/`load_memory`
    can find it. Call once per process, before running any investigation that should be able to
    look up category ownership.
    """
    session_service = session_service or InMemorySessionService()
    session = await session_service.create_session(
        app_name=_ORG_MEMORY_APP_NAME, user_id=_ORG_MEMORY_USER_ID
    )
    org_context = load_org_context()
    text = "Category ownership (org context):\n" + "\n".join(
        f"- {category}: owned by {owner}" for category, owner in org_context.items()
    )
    event = Event(
        author="system",
        content=types.Content(role="user", parts=[types.Part(text=text)]),
    )
    await session_service.append_event(session, event)
    await memory_service.add_session_to_memory(session)


async def load_memory(query: str, tool_context: Any) -> dict[str, list[str]]:
    """Searches org-context/prior-investigation memory for `query`.

    A defensive replacement for ADK's own `LoadMemoryTool`: that tool raises `ValueError` outright
    if the Runner it's attached to has no `memory_service` configured. That's exactly what happens
    under plain `adk web`/`adk run` -- the CLI's auto-constructed Runner has no hook for wiring a
    pre-seeded custom memory service in (org-context seeding needs `seed_org_context` called
    against a concrete service instance first, which only eval/ and a dedicated script currently
    do). Rather than crash the whole reporter turn over an optional lookup, this returns an empty
    result so the model can proceed without a cited owner.
    """
    try:
        response = await tool_context.search_memory(query)
    except ValueError:
        return {"memories": []}
    return {
        "memories": [
            part.text
            for m in response.memories
            if m.content and m.content.parts
            for part in m.content.parts
            if part.text
        ]
    }


def build_load_memory_tool() -> FunctionTool:
    return FunctionTool(load_memory)
