# Direction thresholds (exact bands)

FinSight's benchmark (`eval/README.md`) defines direction against `delta_pct` (net change /
prior-period total):

- `abs(delta_pct) > 7` → confident "up" or "down" (sign of the delta).
- `abs(delta_pct) < 3` → "flat" — no category should be described as having "driven" a change
  that, net, didn't meaningfully happen.
- `3 <= abs(delta_pct) <= 7` → gray zone. Do not assert a confident direction; say the change is
  small and within normal period-to-period variation for this dataset.

## Why these specific bands

Chosen to avoid manufacturing false confidence on borderline cases — a 4% swing in a
regenerating synthetic dataset is not distinguishable from noise, and confidently calling it
"up" or "down" would overstate what the data supports.
