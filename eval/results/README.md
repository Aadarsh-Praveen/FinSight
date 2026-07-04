# eval/results/

`SUMMARY.json` holds the aggregate ablation statistics (task success mean/spread, `must_not_claim`
violation rate, per config) computed from the two real ablation runs behind `FINDINGS.md`:

- `main_run_135_trial_aggregate` — 3 configs × 15 tasks × 3 trials (the full benchmark minus
  `clean_attribution`, which was pre-flight-excluded that run — see `FINDINGS.md` finding 5).
- `custom_run_36_trial_clean_attribution` — the follow-up run that closed that gap: 3 configs ×
  4 fresh `clean_attribution` tasks × 3 trials.

The full per-trial raw JSON dumps these numbers were computed from (~250KB-900KB each) are
gitignored — regenerable via `python eval/ablation.py` (or `--task-ids=...` for a subset) against
live BigQuery/Gemini access. For the narrative behind these numbers — what they mean, why the
verifier's blind spot matters, the two adversarial severities, the methodology — see
[`FINDINGS.md`](../../FINDINGS.md) at the repo root, not this file.
