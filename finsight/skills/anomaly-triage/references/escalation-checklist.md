# Escalation checklist: when to say "insufficient evidence"

Say evidence is insufficient, rather than naming a driver, when any of these hold:

- No single category/dimension explains at least ~40% of the net delta (FinSight's "low"
  confidence floor — see the `driver-attribution-calibration` skill).
- The net delta itself is flat (`abs(delta_pct) < 3`, per `direction-thresholds.md`) — there is no
  meaningful change for anything to have "driven."
- The requested date range returns no rows, or rows only for one of the two periods being
  compared.

## Correct phrasing

State it plainly: *"The available data does not show a single dominant driver for this change; the
[N]% net change is spread across [K] categories with no clear majority contributor."* Do not soften
this into a guess ("it appears to be driven by X, though other factors may contribute") — that
phrasing reads as attribution with a hedge, not as the explicit refusal to attribute that the
evidence actually supports.
