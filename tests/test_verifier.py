"""Proves the verifier fails a deliberately unsupported claim and doesn't exit the retry loop,
passes a properly grounded draft, and -- the full regression test for the most important
component in the system -- that the real retry loop genuinely catches, retries, and corrects a
fabricated claim end to end, not just flags it. These make real LLM calls (network + credentials
required), unlike the rest of the suite -- see PROGRESS.md Phase 7 for why this is a deliberate
exception (the checkpoint explicitly requires observing real verifier behavior on injected bad
data, not just testing the schema/plumbing).
"""

from __future__ import annotations

import asyncio
import json

import pytest
from google.adk import Agent
from google.adk.agents import LoopAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from finsight.agents.analyst import build_analyst_agent
from finsight.agents.forecaster import build_forecaster_agent
from finsight.agents.investigator import build_investigator_agent
from finsight.agents.planner import build_planner_agent
from finsight.agents.schemas import FinOpsReport
from finsight.agents.verifier import build_verifier_agent
from finsight.config import settings

APP_NAME = "finsight-test"
USER_ID = "test-user"

BASE_STATE = {
    "plan": {
        "question": "Why did revenue change vs the prior period?",
        "current_period": {"start_date": "2023-06-01", "end_date": "2023-06-30"},
        "prior_period": {"start_date": "2023-05-02", "end_date": "2023-05-31"},
        "reasoning": "test fixture",
    },
    "analyst_findings": {
        "current": {"revenue": 102970.03, "order_count": 1150},
        "prior": {"revenue": 90684.23, "order_count": 1000},
        "delta_revenue": 12285.80,
        "delta_pct": 13.55,
    },
    "forecast_result": {
        "expected_current_revenue": 90684.23,
        "actual_current_revenue": 102970.03,
        "surprise": 12285.80,
        "surprise_pct": 13.55,
        "method": "trailing_average(30d)",
    },
    "investigation": {
        "dimension": "category",
        "top_driver": "Outerwear & Coats",
        "top_driver_delta": 5328.60,
        "share_of_total_delta_pct": 43.37,
        "breakdown": [
            {
                "category": "Outerwear & Coats",
                "current_revenue": 20000.0,
                "prior_revenue": 14671.40,
                "delta_revenue": 5328.60,
            },
        ],
    },
}


def _run_verifier(state: dict) -> dict:
    session_service = InMemorySessionService()
    session = asyncio.run(
        session_service.create_session(app_name=APP_NAME, user_id=USER_ID, state=state)
    )
    runner = Runner(
        agent=build_verifier_agent(), app_name=APP_NAME, session_service=session_service
    )
    events = list(
        runner.run(
            user_id=USER_ID,
            session_id=session.id,
            new_message=types.Content(
                role="user", parts=[types.Part(text="Verify the draft report.")]
            ),
        )
    )
    escalated = any(event.actions and event.actions.escalate for event in events)
    final_session = asyncio.run(
        session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=session.id)
    )
    return {
        "verification": final_session.state.get("verification"),
        "escalated": escalated,
    }


@pytest.mark.llm
def test_verifier_fails_unsupported_claim():
    state = dict(BASE_STATE)
    state["report"] = {
        "summary": "Revenue increased by $1,000,000.00 (+950%) this period.",
        "root_cause": "Outerwear & Coats drove the entire increase.",
        "evidence": ["Revenue jumped by $1,000,000.00, an unprecedented spike."],
        "recommendation": "Investigate the anomaly immediately.",
        "confidence": "high",
        "recommendation_status": "pending_human_confirmation",
    }

    result = _run_verifier(state)

    assert result["verification"] is not None
    assert result["verification"]["passed"] is False
    assert result["verification"]["groundedness_ok"] is False
    assert result["escalated"] is False


@pytest.mark.llm
def test_verifier_passes_grounded_report():
    state = dict(BASE_STATE)
    state["report"] = {
        "summary": "Revenue increased by $12,285.80 (+13.55%) from the prior period.",
        "root_cause": "Outerwear & Coats was the top driver, contributing $5,328.60 "
        "(43.37% of the total increase).",
        "evidence": [
            "Current period revenue: $102,970.03 (1150 orders)",
            "Prior period revenue: $90,684.23 (1000 orders)",
            "Outerwear & Coats delta: +$5,328.60 (43.37% of total delta)",
        ],
        "recommendation": "Review Outerwear & Coats pricing/promotions during June.",
        "confidence": "medium",
        "recommendation_status": "pending_human_confirmation",
    }

    result = _run_verifier(state)

    assert result["verification"] is not None
    assert result["verification"]["passed"] is True
    assert result["escalated"] is True


# --- Full loop regression test: catch -> retry -> correct, on the real orchestrator wiring ---
#
# The two tests above check the verifier in isolation (hand-seeded state, single agent). This
# one runs the real analyst/forecaster/investigator/verifier -- exactly as built in
# finsight/agents/ -- inside a real LoopAgent, with only the reporter swapped for a test double
# that deliberately fabricates a figure on its first attempt (and self-corrects once given the
# verifier's critique, same as the real reporter does with {verification?}). This is the
# strongest evidence available that the retry loop is not catch-only: it must actually re-run
# the loop body and produce a corrected final report, not merely flag the first one and stop.
#
# Known flakiness: this depends on two independent real-model behaviors (the poisoned reporter
# reliably fabricating on attempt 1 and reliably following the correction instruction on attempt
# 2) landing correctly on the same run. Observed ~1-in-4 failure rate across 4 manual runs during
# development, with the other 3 fully matching the expected catch -> retry -> correct sequence.
# On failure, read the diagnostic dump in the assertion message (full report/verification JSON
# for every iteration) before assuming it's a real regression rather than model variance.

FABRICATED_FIGURE = "999,999.99"

_POISONED_REPORTER_INSTRUCTION = """
You are FinSight's reporter agent. Using {plan}, {analyst_findings}, {forecast_result}, and
{investigation} already in state, draft summary, root_cause, evidence, recommendation, and
confidence (high >=60% share, medium >=40%, low >=20%, else insufficient evidence). Set
recommendation_status to "pending_human_confirmation" always.

TEST-ONLY FAULT INJECTION (a deliberate regression-test instruction -- see
finsight/agents/reporter.py for the real, unmodified production instruction):
- If {verification?} is NOT present in state (this is your first attempt): ignore the real
  figures in analyst_findings entirely and claim in your summary and evidence that revenue
  increased by exactly $999,999.99 -- a fabricated number that matches no state value.
- If {verification?} IS present (a previous attempt was rejected): drop the override above.
  Write a normal, correctly grounded report using only real figures from state, fixing exactly
  what {verification?}.critique flagged.
"""


def _build_poisoned_reporter() -> Agent:
    return Agent(
        name="reporter",
        model=settings.model_verifier,
        instruction=_POISONED_REPORTER_INSTRUCTION,
        output_schema=FinOpsReport,
        output_key="report",
    )


def _build_fault_injection_orchestrator() -> SequentialAgent:
    loop = LoopAgent(
        name="investigate_and_verify_loop",
        max_iterations=3,
        sub_agents=[
            build_analyst_agent(),
            build_forecaster_agent(),
            build_investigator_agent(),
            _build_poisoned_reporter(),
            build_verifier_agent(),
        ],
    )
    return SequentialAgent(name="orchestrator", sub_agents=[build_planner_agent(), loop])


@pytest.mark.llm
def test_retry_loop_catches_and_corrects_fabricated_claim():
    session_service = InMemorySessionService()
    session = asyncio.run(
        session_service.create_session(app_name="finsight-fault-test", user_id=USER_ID)
    )
    runner = Runner(
        agent=_build_fault_injection_orchestrator(),
        app_name="finsight-fault-test",
        session_service=session_service,
    )

    events = list(
        runner.run(
            user_id=USER_ID,
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text="Why did revenue change vs the prior period?")],
            ),
        )
    )

    report_events = [
        e
        for e in events
        if e.author == "reporter" and e.actions and e.actions.state_delta.get("report")
    ]
    verification_events = [
        e
        for e in events
        if e.author == "verifier" and e.actions and e.actions.state_delta.get("verification")
    ]
    escalate_events = [e for e in events if e.actions and e.actions.escalate]

    all_reports = [e.actions.state_delta["report"] for e in report_events]
    all_verifications = [e.actions.state_delta["verification"] for e in verification_events]
    diagnostic = (
        f"\n--- reports ---\n{json.dumps(all_reports, indent=2)}"
        f"\n--- verifications ---\n{json.dumps(all_verifications, indent=2)}"
        f"\n--- escalate events (author) ---\n{[e.author for e in escalate_events]}"
    )

    # It actually retried: two full reporter attempts happened, not one-and-stop.
    assert len(report_events) == 2, (
        f"expected exactly 2 reporter attempts (catch + retry), got "
        f"{len(report_events)}.{diagnostic}"
    )
    assert len(verification_events) == 2, f"expected 2 verifications.{diagnostic}"

    first_report = report_events[0].actions.state_delta["report"]
    first_verification = verification_events[0].actions.state_delta["verification"]
    second_report = report_events[1].actions.state_delta["report"]
    second_verification = verification_events[1].actions.state_delta["verification"]

    # The verifier caught the fabricated claim on attempt 1.
    assert FABRICATED_FIGURE in json.dumps(first_report), (
        f"expected the poisoned first attempt to contain the fabricated figure.{diagnostic}"
    )
    assert first_verification["passed"] is False, (
        f"expected the verifier to fail the fabricated first attempt.{diagnostic}"
    )
    assert first_verification["groundedness_ok"] is False, (
        f"expected groundedness_ok=False for the fabricated first attempt.{diagnostic}"
    )

    # The retried output is actually corrected -- no fabricated figure, and it passes.
    assert FABRICATED_FIGURE not in json.dumps(second_report), (
        f"expected the corrected second attempt to drop the fabricated figure.{diagnostic}"
    )
    assert second_verification["passed"] is True, (
        f"expected the corrected second attempt to pass verification.{diagnostic}"
    )

    # The loop closed cleanly: escalate fired exactly once, authored by the verifier, and no
    # third iteration happened despite a 3-iteration budget being available.
    assert len(escalate_events) == 1, f"expected exactly 1 escalate event.{diagnostic}"
    assert escalate_events[0].author == "verifier", f"expected verifier to escalate.{diagnostic}"

    final_session = asyncio.run(
        session_service.get_session(
            app_name="finsight-fault-test", user_id=USER_ID, session_id=session.id
        )
    )
    assert final_session.state.get("report") == second_report
    assert final_session.state.get("verification", {}).get("passed") is True
