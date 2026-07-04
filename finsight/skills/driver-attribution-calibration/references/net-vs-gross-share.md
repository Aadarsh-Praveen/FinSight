# Net-delta share vs. gross-movement share: a worked real example

From a real ablation trial (`multi_agent_verifier`, task `clean-010-suits-dec19-high`, trial 0 —
see `FINDINGS.md` and `KAGGLE_WRITEUP.md` §2 for the full write-up):

- Net period-over-period revenue delta: **+$2,024.78** (Nov 2019 → Dec 2019).
- Top driver ("Suits & Sport Coats") delta: **+$2,238.35**.
- **Net-delta share** (the metric FinSight actually uses): 2238.35 / 2024.78 × 100 = **110.56%**.
- **Gross-movement share** (top driver's delta ÷ the sum of *all 26* categories' absolute deltas,
  ≈$6,365.80 in this trial): 2238.35 / 6365.80 × 100 = **35.16%** — a completely different number,
  and one that's mathematically bounded at 100% by construction (a single category's delta can
  never exceed the sum of everyone's absolute movement, including its own).

The net-delta share exceeded 100% here because several other categories moved in the *opposite*
direction in the same period (Tops & Tees −$461.87, Suits −$459.54, Outerwear & Coats −$210.33),
shrinking the net delta below the top driver's own delta. This is a real, correct property of the
net-delta formula, not a bug — and it is why FinSight uses net-delta share specifically, since it's
the metric that answers "how much of what actually happened, net, does this category explain,"
which is the question a stakeholder is actually asking.
