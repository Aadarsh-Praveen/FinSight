---
name: driver-attribution-calibration
license: Apache-2.0
metadata:
  author: finsight
  version: "1.0"
description: |
  Playbook for computing a category driver's share of a revenue change and stating a
  confidence level that matches the evidence, without over- or under-claiming. Use whenever
  naming a category as the cause of a revenue change and before stating a confidence level.
---

# Skill: driver-attribution-calibration

This formalizes a rule already applied informally in FinSight's investigator/reporter/verifier
prompts and in `eval/README.md`'s `clean_attribution` scoring — consult this skill rather than
re-deriving the thresholds from memory, since they are exact and load-bearing for scoring.

## 1. The share formula (there is only one correct one)

```
share_of_total_delta_pct = top_driver's delta_revenue / net_period_over_period_delta * 100
```

Divide by the **net** delta (`analyst_findings.delta_revenue`), never by the sum of every
category's *absolute* delta. These give meaningfully different, both-valid-looking numbers when
categories move in offsetting directions — see `references/net-vs-gross-share.md` for a worked
real example where net-delta share came out to 110.56% while the same trial's gross-movement share
was 35.16%.

**A share above 100% is not an error.** It happens whenever other categories moved in the opposite
direction of the top driver, shrinking the net delta below the top driver's own delta. Don't clip
or "correct" it — report it as computed, and treat >=60% (net-delta share) as squarely "high"
confidence regardless of how far above 100% it is.

## 2. Confidence tiers (exact thresholds)

| share_of_total_delta_pct | confidence |
|---|---|
| >= 60 | high |
| >= 40 | medium |
| >= 20 | low |
| < 20 | insufficient evidence |

- **Overclaiming** = stating a higher tier than the share supports, or asserting the driver as
  sole/dominant cause without qualification when the tier is medium or lower.
- **Underclaiming** = saying there's no identifiable driver, or claiming insufficient evidence,
  when the tier is low or higher and a leading driver was in fact found.
- If `net_period_over_period_delta` is itself flat/near-zero, this formula is mathematically
  meaningless (division by ~0) — see the `anomaly-triage` skill's direction-thresholds reference
  instead; do not compute or cite a share in this case.

## 3. Don't assume the typical case

A systematic search across the dataset found most month-pairs land in a ~43-54% ("medium") band —
but real outliers exist on both ends (a 110%+ case is documented in
`references/net-vs-gross-share.md`). Compute the share fresh for the specific period in question;
never assume "medium" is the safe default answer.
