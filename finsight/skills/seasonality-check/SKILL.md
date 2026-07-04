---
name: seasonality-check
license: Apache-2.0
metadata:
  author: finsight
  version: "1.0"
description: |
  Playbook for distinguishing a genuine revenue driver from a seasonal effect by comparing
  against the same period one year prior, not just the immediately preceding period. Use when
  a month-over-month change might plausibly be seasonal (e.g. holiday months, back-to-school,
  category-specific seasons like outerwear/swimwear).
---

# Skill: seasonality-check

FinSight's default comparison is month-over-month (current period vs. the immediately prior
period). That comparison cannot distinguish "this category grew because something changed" from
"this category always grows in this month, every year." This playbook adds one extra check using
tools FinSight already has — it does not require any new tool.

## When to run this check

Run it whenever the top driver category has an intuitive seasonal story — outerwear/coats in
winter months, swimwear in summer, back-to-school categories in August/September, gift categories
in November/December — or whenever a stakeholder's question spans a period crossing a holiday.

## How to run it

1. Take the top driver category and the current period's date range from `{investigation}` /
   `{plan}`.
2. Call `compare_period_over_period` again, but with `current_start`/`current_end` set to the same
   calendar dates **one year earlier**, and `prior_start`/`prior_end` set to one year earlier than
   that — i.e., shift both windows back 12 months, reusing the same tool with different dates.
3. Compare: did the same category show a similar swing in the year-ago comparison?
   - **Yes, similarly large** → likely seasonal. Say so explicitly in the report and lower
     confidence that this reflects a new, actionable business change, even if the current period's
     `share_of_total_delta_pct` is high per the `driver-attribution-calibration` skill.
   - **No, or much smaller** → the current swing is less likely to be routine seasonality; the
     `driver-attribution-calibration` tiers can be reported without this caveat.

## Why this matters for recommendations

A recommendation like "investigate what marketing did differently this December" is misleading if
outerwear grows every December regardless of marketing — see `references/seasonal-categories.md`
for categories in this dataset with a documented recurring seasonal pattern.
