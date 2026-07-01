# PROGRESS.md — FinSight Build Log

> Claude Code updates this file after **every phase**: what was done, key decisions, any deviations
> from `BUILD_PLAN.md`, and what's next. Keep entries short and factual.

## Phase status

| Phase | Name | Status | Commit | Notes |
|-------|------|--------|--------|-------|
| 0 | Repo bootstrap & hygiene | ✅ Done | (pending) | venv recreated w/ Python 3.11 |
| 1 | Config & environment plumbing | ⬜ Not started | — | |
| 2 | Google Cloud + BigQuery readiness | ⬜ Not started | — | |
| 3 | MCP Toolbox: read-only BigQuery tools | ⬜ Not started | — | |
| 4 | First single agent (vertical slice) | ⬜ Not started | — | |
| 5 | Full multi-agent workflow | ⬜ Not started | — | |
| 6 | Guardrails & security | ⬜ Not started | — | |
| 7 | Verifier agent | ⬜ Not started | — | |
| 8 | Skills, memory, observability | ⬜ Not started | — | |
| 9 | Eval harness + benchmark + ablation | ⬜ Not started | — | |
| 10 | Deploy, CI, submission packaging | ⬜ Not started | — | |

Status key: ⬜ Not started · 🟡 In progress · ✅ Done · ⚠️ Blocked

## Environment facts (fill in once, reference throughout)
- OS / arch: macOS, arm64 (Apple Silicon)
- GCP Project ID: `finsight-hackathon-501118`
- Region: `us-central1`
- Dataset: `bigquery-public-data.thelook_ecommerce` (default)
- ADK version installed: `google-adk` 2.3.0
- MCP Toolbox version: not yet downloaded (Phase 3)

## Open blockers (things waiting on the human)
- [x] GCP project created + billing enabled
- [x] `gcloud auth application-default login` done (account: aadarshfinsight@gmail.com)
- [x] `.env` filled from `.env.example`
- [ ] MCP Toolbox binary downloaded for the correct OS (macOS arm64) — Phase 3
- [x] Official Kaggle deadline confirmed: **July 6, 2026** (user-confirmed 2026-07-01)

## Deviations from BUILD_PLAN.md
_(Record any place the installed library API differed from the plan, and what was done instead.)_
- The pre-existing `.venv` used Python 3.14.5 (homebrew default), which is very new and risked
  missing wheels for pinned deps. Recreated `.venv` with Python 3.11.15 (homebrew `python@3.11`)
  before installing `requirements.txt`. All deps, including `google-adk~=2.0` (resolved to 2.3.0),
  installed cleanly with no compatibility issues.
- Added a top-level `scripts/` directory (not explicitly in the section-2 tree) to hold
  `scripts/check_bigquery.py` per the Phase 2 instructions.

## Log
### 2026-07-01 — Phase 0
- Confirmed real deadline with user: July 6, 2026 (~5 days from build start). Prioritize Phases
  0-7 + 9 as must-haves per the risk register; Phase 8 extras and Phase 10 polish are cuttable.
- Scaffolded the full repo folder tree from BUILD_PLAN.md section 2 (finsight/ package with
  agents/, tools/, skills/, guardrails/, memory/ subpackages; eval/, tests/, deployment/,
  mcp-toolbox/, .github/workflows/, scripts/), all with placeholder docstring+TODO modules.
- Wrote `.gitignore`, `.env.example` (template only, no secrets), `requirements.txt`,
  `pyproject.toml` (ruff + pytest config), `Dockerfile`, `.dockerignore`, README skeleton.
- Recreated `.venv` with Python 3.11.15 (see Deviations) and installed all pinned deps.
- Checkpoint verified: `pip install -r requirements.txt` succeeded; `python -c "import
  google.adk"` works (v2.3.0); `ruff check .` passes clean; `pytest` runs with 0 tests collected
  (exit 5, expected).
- Confirmed already-done human steps: GCP APIs (bigquery, run, aiplatform, cloudtrace) enabled;
  ADC authenticated; `.env` populated with real values; GitHub remote already linked
  (`github.com/Aadarsh-Praveen/FinSight`).
- Next: Phase 1 (config loader) — should be quick since `.env` is already fully populated.
