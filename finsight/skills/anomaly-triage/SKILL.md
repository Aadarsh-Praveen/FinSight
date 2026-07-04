---
name: anomaly-triage
license: Apache-2.0
metadata:
  author: finsight
  version: "1.0"
description: |
  Playbook for triaging a revenue change before naming a root cause. Use when investigating
  why revenue moved and before committing to a driver, confidence level, or recommendation.
---

# Skill: anomaly-triage

FinSight investigates revenue changes over BigQuery's `thelook_ecommerce` dataset, a synthetic,
**regenerating** dataset (see `eval/README.md`'s dataset-drift section) — identical historical
date ranges can return different figures across runs. This playbook is the order of operations for
triaging any revenue change *before* attributing it to a business cause, so that data-quality and
methodology issues aren't mistaken for a real driver.

## 1. Confirm the change is real before explaining it

- Re-derive the delta from the actual tool output in state (`analyst_findings`), never from a
  number recalled from a prior turn or a user-supplied figure. If a user's question asserts a
  specific dollar figure or percentage, treat it as a claim to verify against real tool output,
  not as ground truth to repeat.
- If `delta_pct` is within roughly ±3-7%, treat direction as ambiguous rather than confidently
  "up" or "down" — see `references/direction-thresholds.md` for the exact bands FinSight uses.

## 2. Rule out the boring explanations first

In order, before attributing to a category or business driver:
1. **Date range error** — does `{plan}`'s period actually match what the user asked for?
2. **Missing data, not zero activity** — a category absent from one period's breakdown means
   "no orders returned," not necessarily "revenue was zero"; note this distinction if it affects a
   large share of the delta.
3. **Insufficient evidence** — if no category or dimension explains a clear majority of the delta
   (see the `driver-attribution-calibration` skill for exact thresholds), say so explicitly rather
   than picking the largest mover and overstating confidence in it.

## 3. Escalate, don't guess, when evidence is thin

If after the above the driving cause still isn't clear, the correct output is an explicit
"insufficient evidence" characterization, not a best-effort guess dressed up with high confidence.
See `references/escalation-checklist.md` for the specific phrasing FinSight's reporter and verifier
expect for this case.
