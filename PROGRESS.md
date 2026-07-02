# PROGRESS.md — FinSight Build Log

> Claude Code updates this file after **every phase**: what was done, key decisions, any deviations
> from `BUILD_PLAN.md`, and what's next. Keep entries short and factual.

## Phase status

| Phase | Name | Status | Commit | Notes |
|-------|------|--------|--------|-------|
| 0 | Repo bootstrap & hygiene | ✅ Done | `120268a` | venv recreated w/ Python 3.11 |
| 1 | Config & environment plumbing | ✅ Done | `38cd311` | pydantic Settings, fails loudly |
| 2 | Google Cloud + BigQuery readiness | ✅ Done | `871a60e` | fixed location mismatch bug |
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

### 2026-07-01 — Phase 1
- Implemented `finsight/config.py`: a pydantic `Settings` model loaded from `.env` via
  `python-dotenv`. Validates all required vars are present (fails with a clear `RuntimeError`
  listing exactly which vars are missing) and cross-validates that `GOOGLE_API_KEY` is set when
  `GOOGLE_GENAI_USE_VERTEXAI` is `FALSE`.
- `python -m finsight.config` self-check prints resolved non-secret settings; `GOOGLE_API_KEY` is
  shown as `<set>`/`<not set>` rather than echoing the value.
- Verified the failure path by temporarily moving `.env` aside and re-running the self-check —
  got the expected `RuntimeError` naming all 9 missing vars, exit code 1. Restored `.env`
  immediately after.
- Note: `python-dotenv`'s `load_dotenv()` (no `usecwd=True`) searches upward from the *calling
  module's* location, not the shell's cwd — so `.env` at the repo root is found regardless of
  where `finsight.config` is imported from. Worth remembering if `.env` is ever moved.
- Re-ran `ruff check .` (clean) and `pytest` (0 tests, exit 5) — checkpoint still green.
- Next: Phase 2 (Google Cloud + BigQuery readiness) — write `scripts/check_bigquery.py`;
  connectivity/auth already manually verified by the user, so this is mostly about producing the
  repo artifact.

### 2026-07-01 — Phase 2
- Wrote `scripts/check_bigquery.py`: standalone script (loads `.env` directly, doesn't import
  `finsight.config`, to avoid sys.path issues when run as a plain script) that runs
  `SELECT COUNT(*)` against `bigquery-public-data.thelook_ecommerce.orders`.
- First run hit `403 Access Denied` — root cause was **not** a real permission problem: the
  `bigquery.Client` was constructed with `location=GOOGLE_CLOUD_LOCATION` (`us-central1`), but
  `bigquery-public-data` datasets live in the `US` multi-region. Forcing a mismatched job location
  produces a misleading access-denied error instead of a location error. Fixed by not passing
  `location` to the client and letting BigQuery auto-detect it per query; added a comment
  explaining why, since it's a non-obvious gotcha.
- Verified: `python scripts/check_bigquery.py` prints `... orders row count: 124838`, exit 0.
  `ruff check .` clean, `pytest` 0 tests (exit 5).
- **Deviation to remember:** `GOOGLE_CLOUD_LOCATION` should only be used for Cloud Run /
  agent-execution region, not forced onto BigQuery jobs that touch public multi-region datasets.
  Keep this in mind when the MCP Toolbox `tools.yaml` `bigquery` source is configured in Phase 3
  — don't hardcode `us-central1` as the dataset location there either.
- Next: Phase 3 (MCP Toolbox: read-only BigQuery tools) — write `mcp-toolbox/tools.yaml` and
  README; human step to download the toolbox binary for macOS arm64.
