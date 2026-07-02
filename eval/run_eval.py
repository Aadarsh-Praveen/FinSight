"""Runs the agent over the benchmark, scores each task, and prints report + judge verdict.

This is intentionally a single-trial, single-config runner for now -- sufficient for the Phase 9
judge-validation sample run (show actual reports + verdicts for a human to check). The full
multi-trial x 3-config comparison lives in eval/ablation.py (not yet built): repeated trials and
the pre-flight re-verification step described in eval/README.md belong there, not here.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from eval.llm_judge import judge_report
from eval.rate_limit import with_retry
from finsight.agents.orchestrator import build_orchestrator_agent

BENCHMARK_PATH = Path(__file__).parent / "benchmark" / "finops_tasks.jsonl"

# Which tool(s) count as "examining" each required_dimension value.
DIMENSION_TOOLS = {
    "category": {"get_orders_by_category"},
}

APP_NAME = "finsight-eval"
USER_ID = "eval-runner"


def load_tasks(path: Path = BENCHMARK_PATH) -> list[dict[str, Any]]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _tool_calls(events: list) -> list[str]:
    calls = []
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    calls.append(part.function_call.name)
    return calls


def _last_state_delta(events: list, author: str, key: str) -> Any:
    matches = [
        e.actions.state_delta[key]
        for e in events
        if e.author == author and e.actions and e.actions.state_delta.get(key)
    ]
    return matches[-1] if matches else None


def run_task(task: dict[str, Any], enable_verifier: bool = True) -> dict[str, Any]:
    """Runs one task through the real orchestrator once and scores it. One real trial."""
    session_service = InMemorySessionService()
    session = asyncio.run(session_service.create_session(app_name=APP_NAME, user_id=USER_ID))
    runner = Runner(
        agent=build_orchestrator_agent(
            enable_verifier=enable_verifier, require_recommendation_confirmation=False
        ),
        app_name=APP_NAME,
        session_service=session_service,
    )

    def _run() -> list:
        return list(
            runner.run(
                user_id=USER_ID,
                session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part(text=task["question"])]),
            )
        )

    events = with_retry(_run, label=f"agent_run:{task['id']}")

    report = _last_state_delta(events, "reporter", "report")
    analyst_findings = _last_state_delta(events, "analyst", "analyst_findings")
    investigation = _last_state_delta(events, "investigator", "investigation")
    verification = _last_state_delta(events, "verifier", "verification")
    tool_calls = _tool_calls(events)
    examined_dimensions = {
        dim for dim, tools in DIMENSION_TOOLS.items() if tools & set(tool_calls)
    }

    result: dict[str, Any] = {
        "task_id": task["id"],
        "task_type": task["task_type"],
        "report": report,
        "analyst_findings": analyst_findings,
        "investigation": investigation,
        "verification": verification,
        "tool_calls": tool_calls,
        "programmatic": {},
    }

    if report is None:
        result["programmatic"]["error"] = "no report produced"
        return result

    ground_truth = task["ground_truth"]

    if ground_truth["largest_driver_category"] is not None:
        actual_driver = investigation.get("top_driver") if investigation else None
        result["programmatic"]["largest_driver_category_match"] = (
            actual_driver == ground_truth["largest_driver_category"]
        )
        result["programmatic"]["actual_driver"] = actual_driver

    missing_dimensions = set(ground_truth["required_dimensions"]) - examined_dimensions
    result["programmatic"]["required_dimensions_examined"] = not missing_dimensions
    if missing_dimensions:
        result["programmatic"]["missing_dimensions"] = sorted(missing_dimensions)

    share_pct = investigation.get("share_of_total_delta_pct") if investigation else None
    verdict = with_retry(
        lambda: judge_report(task, report, share_pct=share_pct), label=f"judge:{task['id']}"
    )
    result["judge_verdict"] = verdict.model_dump()

    return result


def print_result(result: dict[str, Any]) -> None:
    print(f"\n{'=' * 78}\n{result['task_id']}  ({result['task_type']})\n{'=' * 78}")
    if "error" in result["programmatic"]:
        print(f"ERROR: {result['programmatic']['error']}")
        return

    print("\n--- REPORT ---")
    print(json.dumps(result["report"], indent=2))

    print("\n--- ANALYST_FINDINGS (top-line pull, before reporter sees it) ---")
    print(json.dumps(result["analyst_findings"], indent=2))

    print("\n--- INVESTIGATION (agent's own driver analysis) ---")
    print(json.dumps(result["investigation"], indent=2))

    print("\n--- VERIFIER'S OWN VERDICT (if verifier was enabled) ---")
    print(json.dumps(result["verification"], indent=2))

    print("\n--- PROGRAMMATIC CHECKS ---")
    print(json.dumps(result["programmatic"], indent=2))

    verdict = result["judge_verdict"]
    print("\n--- JUDGE: must_not_claim ---")
    for v in verdict["must_not_claim_verdicts"]:
        status = "VIOLATED" if v["violated"] else "ok"
        print(f"  [{v['method']:11s}] {status:8s} {v['claim']!r}\n              {v['explanation']}")

    print("\n--- JUDGE: required_behaviors ---")
    for v in verdict["required_behavior_verdicts"]:
        status = "satisfied" if v["satisfied"] else "NOT satisfied"
        print(f"  {status:14s} {v['behavior']:28s} {v['explanation']}")

    print(
        f"\n--- JUDGE: reasoning_quality={verdict['reasoning_quality_score']}/5  "
        f"groundedness={verdict['groundedness_score']}/5 ---"
    )
    print(f"  {verdict['overall_notes']}")


if __name__ == "__main__":
    task_ids = sys.argv[1:] or None
    all_tasks = load_tasks()
    tasks = [t for t in all_tasks if task_ids is None or t["id"] in task_ids]
    if task_ids and len(tasks) != len(task_ids):
        found = {t["id"] for t in tasks}
        missing = set(task_ids) - found
        raise SystemExit(f"Task ID(s) not found in benchmark: {sorted(missing)}")

    for task in tasks:
        result = run_task(task)
        print_result(result)
