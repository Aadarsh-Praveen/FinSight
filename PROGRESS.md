# PROGRESS.md — FinSight Build Log

> Claude Code updates this file after **every phase**: what was done, key decisions, any deviations
> from `BUILD_PLAN.md`, and what's next. Keep entries short and factual.

## Phase status

| Phase | Name | Status | Commit | Notes |
|-------|------|--------|--------|-------|
| 0 | Repo bootstrap & hygiene | ✅ Done | `120268a` | venv recreated w/ Python 3.11 |
| 1 | Config & environment plumbing | ✅ Done | `38cd311` | pydantic Settings, fails loudly |
| 2 | Google Cloud + BigQuery readiness | ✅ Done | `871a60e` | fixed location mismatch bug |
| 3 | MCP Toolbox: read-only BigQuery tools | ✅ Done | `927ae90` | server verified live via MCP calls |
| 4 | First single agent (vertical slice) | ✅ Done | (pending) | adk run verified, grounded answers |
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
- MCP Toolbox version: `1.6.0+dev.darwin.arm64`, running locally on `http://127.0.0.1:5000`

## Open blockers (things waiting on the human)
- [x] GCP project created + billing enabled
- [x] `gcloud auth application-default login` done (account: aadarshfinsight@gmail.com)
- [x] `.env` filled from `.env.example`
- [x] MCP Toolbox binary downloaded for the correct OS (macOS arm64) — Phase 3, running as PID
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

### 2026-07-01 — Phase 3 (in progress — waiting on human step)
- **Deviation from BUILD_PLAN.md (schema format):** the project was renamed
  `genai-toolbox` -> `mcp-toolbox` (still ships a binary called `toolbox`) and the config
  schema changed from the plan's assumed single-document `sources: {...}` / `tools: {...}` /
  `toolset: {...}` nesting to a **multi-document YAML** format, each document starting with
  `kind: source|tool|toolset`, `name:`, and (for tools) `type: bigquery-sql`. Verified this
  against the actual ground-truth prebuilt config in the `googleapis/mcp-toolbox` GitHub repo
  (`internal/prebuiltconfigs/tools/bigquery.yaml`) and the `bigquery-sql` tool doc page, not just
  blog posts, since a wrong schema would silently fail. `mcp-toolbox/tools.yaml` uses the new
  format.
- **Deviation (CLI flag):** the plan assumed `--tools-file`; that flag was removed in v0.31.0.
  Current flag is `--config` (confirmed v1.6.0, released 2026-07-01, is latest). README updated
  accordingly.
- **Deviation (download URL):** bucket moved from `storage.googleapis.com/genai-toolbox/...` to
  `storage.googleapis.com/mcp-toolbox-for-databases/v<VERSION>/darwin/arm64/toolbox`. Also noted
  a Homebrew option (`brew install mcp-toolbox`) as an alternative in the README.
- Wrote `mcp-toolbox/tools.yaml`: one `bigquery` source (`finsight-bigquery`, no forced
  `location:` — see Phase 2 note; `writeMode: blocked` + `allowedDatasets:
  [bigquery-public-data.thelook_ecommerce]` + a 1 GiB `maximumBytesBilled` cap as defense in
  depth, though the real read-only guarantee is that every tool below is a fixed-SQL
  `bigquery-sql` tool, never `bigquery-execute-sql`) and 4 read-only tools: `get_daily_sales`,
  `get_revenue_by_period`, `get_orders_by_category`, `compare_period_over_period`, grouped into
  the `finops_readonly` toolset.
- Verified real table schemas (`order_items`, `products`, `orders` in `thelook_ecommerce`) via
  the BigQuery client before writing SQL, rather than guessing field names.
- Validated `tools.yaml` parses as 6 valid YAML documents (1 source + 4 tools + 1 toolset), and
  ran the `get_orders_by_category` and `compare_period_over_period` SQL statements directly
  against BigQuery with real parameters — both returned correctly shaped, sensible results.
- `ruff check .` clean, `pytest` 0 tests (exit 5) — no Python changed, sanity re-run only.
- **Blocked on human step:** downloading the `toolbox` v1.6.0 binary for macOS arm64
  (`mcp-toolbox/README.md` has the exact command) — no outbound binary fetch available to the
  agent. Once downloaded and run (`./toolbox --config "tools.yaml"` from `mcp-toolbox/`), the
  Phase 3 checkpoint (server confirms tools loaded) still needs to be verified by the human or in
  a follow-up turn.

### 2026-07-02 — Phase 3 checkpoint verified (server running)
- User downloaded and started the binary (`toolbox --config tools.yaml`, PID confirmed via `ps`,
  listening on `127.0.0.1:5000`). Root endpoint returns the toolbox banner; server reports
  `serverInfo.version = "1.6.0+dev.darwin.arm64"` via a raw MCP `initialize` JSON-RPC call
  (matches the version pinned in the README).
- Note: `/api/toolset/*` (the old genai-toolbox HTTP API) is disabled by default in this
  version — returns `410 Gone` pointing at the `/mcp` JSON-RPC endpoint instead. Verified tool
  loading via a real `tools/list` JSON-RPC call instead: all 4 tools present
  (`get_revenue_by_period`, `get_orders_by_category`, `compare_period_over_period`,
  `get_daily_sales`) with the exact names/descriptions/parameter schemas from `tools.yaml`.
- Ran a live `tools/call` for `get_revenue_by_period(start_date=2023-01-01, end_date=2023-01-31)`
  through the running server: `{"revenue":91939.83,"order_count":1083}` — real, grounded data,
  confirming the full path (MCP client -> toolbox -> ADC -> BigQuery) works end to end.
- **Important finding for Phase 9 (eval benchmark):** re-ran the identical query directly against
  BigQuery (bypassing the toolbox) and got the same numbers just now, confirming the toolbox
  itself is correct — but this **does not match** the result for the same date range from
  Phase 3's earlier verification the previous day (91239.50 / 1124 orders vs today's 91939.83 /
  1083 orders). `bigquery-public-data.thelook_ecommerce` appears to be a **periodically
  regenerated/synthetic dataset**, not a fixed static snapshot. This means eval benchmark
  ground-truth answers (Phase 9) that hardcode expected numbers could go stale between when the
  benchmark is authored and when it's run. Will need to either (a) snapshot the query results
  used as ground truth close to eval-run time, or (b) design benchmark expectations around
  relative/structural correctness (e.g. "category X has the highest revenue") rather than exact
  dollar figures, or (c) materialize a frozen copy of the dataset into our own project. Revisit
  when building `eval/benchmark/finops_tasks.jsonl`.
- MCP tool annotations returned by the server show `"readOnlyHint": false, "destructiveHint":
  true` for all 4 tools — this is a generic default the toolbox applies to the `bigquery-sql`
  tool type (since the type could theoretically run non-SELECT SQL depending on `writeMode`),
  not a reflection of our actual fixed-SELECT queries. Don't rely on MCP tool annotations as a
  safety signal in Phase 6 guardrails — enforce read-only via our own `sql_readonly` guardrail
  and the fixed SQL in `tools.yaml`, as already planned.
- Phase 3 checkpoint fully met. Next: Phase 4 (first single agent — analyst vertical slice).

### 2026-07-02 — Phase 4
- Inspected the installed `google-adk` 2.3.0 API directly (per BUILD_PLAN.md's "trust the
  installed library" guidance) rather than assuming: `google.adk.Agent`/`LlmAgent` is a pydantic
  model with `name`, `model`, `instruction`, `tools` (accepts bare `Callable`s, not just
  `BaseTool`), and `before_tool_callback`/`after_tool_callback` hooks (useful later for Phase 6
  guardrails). `adk run AGENT_DIR` / `adk web AGENTS_DIR` both dynamically import `agent.py`
  inside the target folder and read its `root_agent`, matching BUILD_PLAN.md's assumed layout.
- Confirmed `toolbox_core.ToolboxSyncClient.load_toolset()` returns `ToolboxSyncTool` objects
  that are directly callable with a real `__signature__` (per-tool, reflecting each tool's actual
  params) -- these drop straight into ADK's `tools=[...]` list with no wrapping needed. Verified
  this live against the running toolbox server before wiring it into the agent.
- Implemented `finsight/tools/mcp_bigquery.py` (process-wide lazy `ToolboxSyncClient` singleton,
  since the client's tools call back through its background event loop and must stay alive) and
  `finsight/agents/analyst.py` (single `Agent` with `model=MODEL_WORKER`, the 4
  `finops_readonly` tools, and an instruction that requires tool-grounded answers). Set
  `finsight/agent.py`'s `root_agent` to the analyst per the plan.
- Checkpoint verified with real runs, not just import checks:
  - `adk run finsight "What was total revenue and order count from 2023-01-01 to
    2023-01-31?"` -> agent called `get_revenue_by_period` and answered "91939.83" / "1083",
    which is exactly what Phase 3's live BigQuery check returned for the same range today --
    genuinely grounded, not hallucinated.
  - The plan's own example question ("What were total sales last month by category?") initially
    made the agent ask a clarifying question about the ambiguous date range instead of
    answering -- reasonable, but stalls a single-turn CLI/demo flow. Tightened the instruction to
    require picking a concrete assumed range and stating it, rather than asking. Re-ran: agent
    assumed April 2023, stated that upfront, and returned a full grounded category breakdown via
    `get_orders_by_category`.
- `ruff check .` clean, `pytest` 0 tests (exit 5).
- Next: Phase 5 (full multi-agent workflow — planner/analyst/forecaster/investigator/reporter
  composed via an ADK `Workflow`/graph, orchestrator becomes `root_agent`).
