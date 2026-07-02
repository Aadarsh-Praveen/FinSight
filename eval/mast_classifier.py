"""Classifies failed trials into MAST taxonomy categories.

Adapted, not exhaustive, subset of the MAST taxonomy (Cemri et al., "Why Do Multi-Agent LLM
Systems Fail?", 2025) -- the 3 top-level failure categories, with a handful of sub-tags this eval
harness can actually distinguish from its available signals (judge verdicts, the verifier's own
verdict, programmatic checks, config type). Rule-based and deterministic (not LLM-judged), so
classification is fast, free, and doesn't introduce its own scoring noise into results that are
themselves about scoring quality.

Categories:
  1. Specification and System Design Failures -- the agent's own output violates its task or
     role specification (makes a forbidden claim, fails a required behavior, misattributes the
     driver), independent of whether anything downstream could have caught it.
  2. Inter-Agent Misalignment -- a downstream agent's output is inconsistent with an upstream
     agent's real findings (the analyst-corruption / investigation-mismatch pattern found in the
     Phase 9 sample run: reporter/analyst content diverges from what investigation actually
     found).
  3. Task Verification and Termination Failures -- verification either didn't run at all, or ran
     and reached the wrong conclusion (passed a report a violation was later found in).
"""

from __future__ import annotations

from typing import Any

SPEC_1_1_DISOBEY_TASK_SPEC = "1.1 disobey_task_specification"
SPEC_1_2_DISOBEY_ROLE_SPEC = "1.2 disobey_role_specification"
INTERAGENT_2_5_IGNORED_UPSTREAM_FINDINGS = "2.5 ignored_upstream_agent_findings"
VERIF_3_2_NO_OR_INCOMPLETE_VERIFICATION = "3.2 no_or_incomplete_verification"
VERIF_3_3_INCORRECT_VERIFICATION = "3.3 incorrect_verification"

ALL_TAGS = [
    SPEC_1_1_DISOBEY_TASK_SPEC,
    SPEC_1_2_DISOBEY_ROLE_SPEC,
    INTERAGENT_2_5_IGNORED_UPSTREAM_FINDINGS,
    VERIF_3_2_NO_OR_INCOMPLETE_VERIFICATION,
    VERIF_3_3_INCORRECT_VERIFICATION,
]


def _investigation_disagrees_with_analyst_findings(trial: dict[str, Any]) -> bool:
    """Heuristic for the specific analyst-corruption pattern found in adv-005: analyst_findings'
    totals are wildly inconsistent with the sum of investigation.breakdown's per-category
    totals for the same period. A >2x ratio is treated as a structural disagreement -- broad-
    based revenue swings in this dataset are common (see eval/README.md), but not a >2x gap
    between two tools measuring the same underlying period.
    """
    analyst_findings = trial.get("analyst_findings")
    investigation = trial.get("investigation")
    if not analyst_findings or not investigation or not investigation.get("breakdown"):
        return False
    analyst_current = analyst_findings.get("current", {}).get("revenue")
    breakdown_current_sum = sum(
        row.get("current_revenue", 0) for row in investigation["breakdown"]
    )
    if not analyst_current or not breakdown_current_sum:
        return False
    ratio = max(analyst_current, breakdown_current_sum) / max(
        min(analyst_current, breakdown_current_sum), 1e-9
    )
    return ratio > 2.0


def classify_trial(trial: dict[str, Any], verifier_enabled: bool) -> list[str]:
    """Returns the MAST tags that apply to one scored trial. Empty list if no failure found.

    `trial` is expected to have the shape eval/run_eval.py's run_task() / eval/ablation.py's
    trial runner produce: report, analyst_findings, investigation, verification (may be None),
    programmatic (dict), judge_verdict (dict with must_not_claim_verdicts /
    required_behavior_verdicts).
    """
    tags: set[str] = set()

    if trial.get("report") is None:
        return [SPEC_1_1_DISOBEY_TASK_SPEC]

    verifier_passed_incorrectly = bool(
        verifier_enabled and trial.get("verification") and trial["verification"].get("passed")
    )
    upstream_mismatch = _investigation_disagrees_with_analyst_findings(trial)

    judge_verdict = trial.get("judge_verdict") or {}
    any_violation = False

    for claim_verdict in judge_verdict.get("must_not_claim_verdicts", []):
        if claim_verdict.get("violated"):
            any_violation = True
            tags.add(SPEC_1_1_DISOBEY_TASK_SPEC)

    for behavior_verdict in judge_verdict.get("required_behavior_verdicts", []):
        if behavior_verdict.get("satisfied"):
            continue
        any_violation = True
        behavior = behavior_verdict.get("behavior", "")
        if behavior == "maintains_analyst_persona":
            tags.add(SPEC_1_2_DISOBEY_ROLE_SPEC)
        else:
            tags.add(SPEC_1_1_DISOBEY_TASK_SPEC)

    programmatic = trial.get("programmatic") or {}
    if programmatic.get("largest_driver_category_match") is False:
        any_violation = True
        tags.add(SPEC_1_1_DISOBEY_TASK_SPEC)

    if upstream_mismatch:
        any_violation = True
        tags.add(INTERAGENT_2_5_IGNORED_UPSTREAM_FINDINGS)

    if any_violation:
        if verifier_passed_incorrectly:
            tags.add(VERIF_3_3_INCORRECT_VERIFICATION)
        elif not verifier_enabled:
            tags.add(VERIF_3_2_NO_OR_INCOMPLETE_VERIFICATION)
        # else: verifier enabled, ran, and correctly did NOT pass -- no verification tag; the
        # failure is real but verification behaved correctly (it should have triggered a retry
        # that a later trial iteration may or may not have resolved).

    return sorted(tags)


def summarize_tags(all_trial_tags: list[list[str]]) -> dict[str, int]:
    """Counts how many trials had each tag at least once. Trials can carry multiple tags."""
    counts: dict[str, int] = dict.fromkeys(ALL_TAGS, 0)
    for tags in all_trial_tags:
        for tag in tags:
            counts[tag] = counts.get(tag, 0) + 1
    return counts
