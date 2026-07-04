# Candidate seasonal categories (hypotheses to verify, not confirmed facts)

These are general retail-domain priors for *which* categories are worth running the year-ago
comparison on — they are starting hypotheses to check against this specific dataset's real
year-ago figures, not verified claims about `thelook_ecommerce` itself. Interestingly, the
`clean_attribution` benchmark tasks (`eval/benchmark/finops_tasks.jsonl`) found "Outerwear & Coats"
as the top driver in several *different* months (November, March, June, December) across different
years — which argues against a simple single-season story for that category in this dataset, and
is itself a reason to actually run the check rather than assume the obvious seasonal story applies.

| Category pattern | Typical retail hypothesis |
|---|---|
| Outerwear & Coats, Sweaters | Cold-weather months (varies by hemisphere/region — verify, don't assume) |
| Swim, Shorts | Warm-weather months |
| Fashion Hoodies & Sweatshirts, Sleep & Lounge | Back-to-school / fall onset |
| Gift-adjacent categories broadly | November-December |

**The point of this file is the instruction, not the table**: always run the actual year-ago
`compare_period_over_period` call per `SKILL.md` rather than pattern-matching a category name to
this table and skipping the real check.
