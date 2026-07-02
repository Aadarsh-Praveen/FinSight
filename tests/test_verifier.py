"""Proves the verifier fails a deliberately unsupported claim and doesn't exit the retry loop,
and passes a properly grounded draft. These make real LLM calls (network + credentials
required), unlike the rest of the suite -- see PROGRESS.md Phase 7 for why this is a deliberate
exception (the checkpoint explicitly requires observing real verifier behavior on injected bad
data, not just testing the schema/plumbing).
"""

from __future__ import annotations

import asyncio

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from finsight.agents.verifier import build_verifier_agent

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
