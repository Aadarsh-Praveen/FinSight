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
| 4 | First single agent (vertical slice) | ✅ Done | `60494ab` | adk run verified, grounded answers |
| 5 | Full multi-agent workflow | ✅ Done | `0686aae` | SequentialAgent, structured hand-offs |
| 6 | Guardrails & security | ✅ Done | `1aaaac2` | 17 tests pass; HITL resume has a caveat |
| 7 | Verifier agent | ✅ Done | `ffd359f` | retry loop verified live, both pass/fail paths |
| 8 | Skills, memory, observability | ⬜ Not started | — | |
| 9 | Eval harness + benchmark + ablation | 🟡 In progress | — | schema + 6 example tasks + methodology done |
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

### 2026-07-02 — Phase 5
- **Design choice (structured state, not the "Workflow" graph class):** inspected
  `google.adk.agents.SequentialAgent` and confirmed it runs sub-agents in a fixed order sharing
  one session, which is exactly "plan -> pull -> forecast -> investigate -> report." Used that
  instead of the top-level `google.adk.Workflow`/`Task` API BUILD_PLAN.md mentions, since
  `SequentialAgent` is the documented, stable primitive for this exact fixed-order pattern in the
  installed 2.3.0 API and is sufficient for now. `Workflow` remains available if Phase 7's
  verifier retry-loop needs branching that `SequentialAgent` can't express.
- **Design choice (structured hand-offs):** confirmed ADK 2.3.0 explicitly supports combining
  `output_schema` with `tools` on the same `LlmAgent` ("exposing tools during the thought loop,
  enforcing structure only on the final output" -- see `llm_agent.py` docstring). Added
  `finsight/agents/schemas.py` with one pydantic model per hand-off
  (`InvestigationPlan`, `AnalystFindings`, `ForecastResult`, `DriverFinding`, `FinOpsReport`).
  Each sub-agent sets `output_key`, and downstream agents reference prior state via `{plan}`,
  `{analyst_findings}`, etc. in their instruction strings -- confirmed this auto-templates via
  `google/adk/flows/llm_flows/instructions.py`'s `_process_agent_instruction`, not something I
  need to wire manually. This is the literal "manage shared state so agents pass structured data,
  not prose" requirement from BUILD_PLAN.md.
- Added a 5th BigQuery tool, `get_dataset_date_range` (min/max order date), specifically so the
  new **planner** agent can ground relative time references ("last month") in the dataset's real
  coverage instead of the model's assumption about "today". Verified via the toolbox's default
  hot-reload (`--disable-reload` is opt-out, so editing `tools.yaml` needed no server restart) --
  confirmed the new tool immediately callable, and confirmed the dataset now spans
  **2019-01-16 to 2026-07-05** (the max date is itself past today, 2026-07-02, reinforcing the
  Phase 3 finding that this dataset is regenerated/synthetic, not static).
- Split agent responsibilities to avoid redundant BigQuery calls: `analyst` pulls only the
  top-line current-vs-prior delta (`compare_period_over_period`); `investigator` independently
  pulls category breakdowns for both periods (`get_orders_by_category` x2) to compute
  per-category deltas and name the top driver; `forecaster` pulls prior-period daily figures
  (`get_daily_sales`) and feeds them through a new pure-Python tool,
  `finsight/tools/finops_tools.py::compute_baseline_forecast` (trailing-average baseline).
  Deliberately **not** BigQuery `AI.FORECAST`/TimesFM -- BUILD_PLAN.md's risk register explicitly
  sanctions a moving-average fallback, and a fast, deterministic, dependency-free baseline is
  easier to reason about and reproduce in the Phase 9 eval harness than a live model call with
  unknown quota/latency/cost on a fresh GCP project.
- Least-privilege tool scoping: added `mcp_bigquery.load_tools(*names)` (loads specific tools by
  name via `ToolboxSyncClient.load_tool`) alongside the existing `load_finops_readonly_tools()`.
  Each Phase 5 sub-agent gets only the 1-2 tools its role needs (planner: date range only;
  analyst: compare only; forecaster: daily sales + baseline compute; investigator: category
  only), rather than the full toolset -- smaller tool-schema footprint per agent and a concrete,
  demoable least-privilege story ahead of Phase 6.
- Model assignment follows BUILD_PLAN.md section 0 exactly: `MODEL_WORKER` (gemini-2.5-flash)
  for planner/analyst/forecaster/investigator, `MODEL_VERIFIER` (gemini-2.5-pro) for reporter
  ("stronger model for the verifier and final report writer").
- Repurposed `analyst.py` for its Phase 5 role (structured top-line pull) rather than keeping the
  Phase 4 general-Q&A instruction -- `root_agent` now points at the orchestrator, so the old
  free-form single-agent entrypoint is superseded, not preserved in parallel. Removed the
  module-level `root_agent = build_analyst_agent()` eager instantiation that Phase 4 had (it did
  a live toolbox round-trip at import time); Phase 5 agent builders are all lazy, only
  instantiated when `build_orchestrator_agent()` runs.
- **Checkpoint verified with real `adk run` calls (not import-only):**
  - `adk run finsight "Why did revenue change vs the prior period?"` -> full 5-agent trace ran
    end to end. Planner grounded on real dataset coverage (chose 2026-06-06..07-05 vs
    2026-05-07..06-05 current 30 days = 30 days.) Analyst found +$376,970.25 (+80.53%). Forecaster
    confirmed the same surprise vs. its trailing baseline. Investigator found the top category
    driver ("Outerwear & Coats") explains only 14.86% of the delta. Reporter correctly refused to
    over-attribute the cause to one category, returned `"confidence": "insufficient evidence"`,
    and recommended investigating a site-wide cause instead -- exactly the "don't overclaim"
    behavior Phase 9's benchmark trap cases are meant to test for, showing up naturally already.
  - A second run with explicit dates ("Compare revenue for 2023-06-01 to 2023-06-30 against the
    prior 30 days") also worked end to end and returned a `"medium"` confidence, named-driver
    report -- confirms the graph handles both ambiguous and explicit questions correctly.
- **Known limitation to revisit:** because `forecaster`'s lookback window is exactly
  `prior_period` (same dates `analyst` already used) and `projection_days` equals that same
  period's length, `expected_current_revenue` is currently always numerically identical to
  `analyst_findings.prior.revenue` -- a mathematically valid trailing-average baseline, but it
  doesn't yet add information beyond what analyst already established. A real improvement (if
  time allows, e.g. Phase 8/9 polish) would give forecaster a longer/independent lookback window
  (e.g. several periods back) so it's a genuinely distinct signal, not a restatement of the prior
  period.
- `ruff check .` clean, `pytest` 0 tests (exit 5).
- Next: Phase 6 (guardrails & security — `sql_readonly`, `pii_redaction`, `injection_guard`,
  human-in-the-loop confirmation before "action" recommendations).

### 2026-07-02 — Phase 6
- Inspected ADK 2.3.0's actual callback invocation code
  (`google/adk/flows/llm_flows/functions.py`) rather than assuming semantics: a
  `before_tool_callback` that returns a non-None dict **short-circuits** the real tool call and
  becomes the response; an `after_tool_callback` that returns non-None **replaces** the tool's
  response. Both accept lists (`agent.canonical_before_tool_callbacks` /
  `canonical_after_tool_callbacks`), so every agent gets one `before_tool_callback`
  (`sql_readonly_guardrail`) and a list of two `after_tool_callback`s
  (`pii_redaction_guardrail`, `injection_guard_callback`) via a new
  `finsight/guardrails/__init__.py::DEFAULT_AFTER_TOOL_CALLBACKS` convenience export. Callback
  kwargs are `tool=`/`args=`/`tool_context=`(/`tool_response=` for after-callbacks) — matched
  those exact parameter names in each guardrail function.
- `finsight/guardrails/sql_readonly.py`: since every real BigQuery tool already only has
  fixed SQL with typed params (the actual read-only guarantee, per Phase 3), this is
  defense-in-depth: (a) refuses any tool whose name contains `execute_sql`/`exec_sql`/`run_sql`/
  `raw_sql` substrings, turning the Phase 3 tools.yaml comment ("don't add
  bigquery-execute-sql") into an enforced runtime check, not just a comment; (b) scans every
  string-valued tool argument for SQL statement separators/comment markers (`;`, `--`, `/*`)
  and forbidden DML/DDL keywords (word-boundary matched to avoid false positives like
  "updated_at").
- `finsight/guardrails/pii_redaction.py`: redacts email-pattern text anywhere in a tool
  response, and blanks out any dict field whose key is a known PII field name (email,
  first_name, last_name, etc.) regardless of content. None of our current tools select PII
  columns, so this has no live trigger today -- it's ready for if a future tool ever touches
  `thelook_ecommerce.users`.
- `finsight/guardrails/injection_guard.py`: scans tool response text for prompt-injection
  patterns ("ignore previous instructions", "you are now", fake `<tool_call>` markers, etc.)
  and replaces matched strings with a neutralization marker, logging a warning. Framed as
  protecting against indirect injection via *retrieved data* (OWASP LLM01), not just user input.
- **Human-in-the-loop:** discovered ADK 2.3.0 has a first-class primitive for exactly this --
  `FunctionTool(func, require_confirmation=True)` (confirmed by reading
  `google/adk/tools/function_tool.py`). Added `finsight/tools/finops_tools.py::
  propose_recommendation` and wired it onto `reporter` as a confirmation-gated tool; extended
  `FinOpsReport` with a `recommendation_status` field so the report explicitly states
  "pending_human_confirmation" rather than silently presenting a recommendation as approved.
- `tests/test_guardrails.py`: 17 tests covering all three guardrails plus the HITL wiring
  (SQL keyword/statement-separator/tool-name blocking, clean-input pass-through, PII redaction
  by pattern and by field name including nested structures, injection pattern detection and
  neutralization, and confirming `propose_recommendation` is wrapped with
  `require_confirmation=True`). All 17 pass. Checkpoint's literal requirement ("malicious SQL
  blocked", "PII field redacted") is a subset of this coverage.
- Needed `pythonpath = ["."]` under `[tool.pytest.ini_options]` in `pyproject.toml` --
  without it, `pytest` couldn't import `finsight.*` from `tests/` (no installed package, no
  `conftest.py`). Not mentioned in BUILD_PLAN.md; discovered when the first test run failed
  with `ModuleNotFoundError`.
- **Live-verified the HITL block-by-default behavior**, not just the unit test: ran
  `adk run finsight "Why did revenue change vs the prior period?"` (persistent session, not
  `--in_memory`) through the full 5-agent graph. When reporter called `propose_recommendation`,
  the CLI correctly paused with `🚨 [PAUSED] Workflow is waiting for human input!` and a
  `--session_id` to resume with -- proving the gate blocks by default and doesn't silently
  approve.
- **Known limitation (logged, not fixed -- time-boxed given the 2026-07-06 deadline):**
  resuming that paused session in a **new** `adk run` process
  (`adk run finsight "yes" --session_id <id>`) failed with `Tool 'propose_recommendation' not
  found. Available tools: get_dataset_date_range` -- i.e. resume routed the pending function
  call to the wrong sub-agent's tool registry (that's `planner`'s tool, not `reporter`'s).
  Root cause is most likely that each `adk run` process calls `build_orchestrator_agent()` from
  scratch, which calls `load_tools()` fresh per sub-agent (new `ToolboxSyncTool`/`FunctionTool`
  object identities each process) -- the persisted session's pending function call likely can't
  be re-matched to the freshly-rebuilt agent tree correctly across a process boundary. This
  looks like an ADK limitation/rough edge with `SequentialAgent` sub-agent tool-confirmation
  resume across separate CLI invocations, not a misconfiguration in our code (the `require_
  confirmation` wiring itself is exactly per ADK's documented pattern, and the initial-block
  behavior is correct). **If revisited:** try resuming within one continuous process (e.g. via
  `adk web`'s live server, or a custom script using `Runner` directly) instead of separate CLI
  invocations for the demo video (Phase 10) and eval harness (Phase 9) to sidestep this.
- `ruff check .` clean, `pytest` 17 passed (guardrail tests) + 0 collected elsewhere (exit 5 ->
  now folded into the 17, since test_guardrails.py is the only test file with content so far).
- Added `.adk/` and `*/agents_log/` to `.gitignore` (local session/artifact storage created by
  `adk run`, discovered as untracked cruft after the live HITL test).
- Next: Phase 7 (verifier agent — groundedness/sufficiency/policy critic + retry loop; this is
  also where the SequentialAgent-vs-branching-Workflow question from Phase 5 gets revisited).

### 2026-07-02 — Phase 7
- **Revisited the SequentialAgent/Workflow question from Phase 5:** discovered both
  `SequentialAgent` and `LoopAgent` are marked `@deprecated` in the installed google-adk 2.3.0
  ("will be removed in future versions, use Workflow instead"). Inspected `google.adk.Workflow`
  (`google.adk.workflow`: `Node`/`Edge`/`START`/conditional dict-keyed routing, `FunctionNode`,
  `JoinNode`) -- it's a genuinely different graph-builder API, not a drop-in rename. Given
  `SequentialAgent`/`LoopAgent` are fully working and tested, and Phase 9 (eval harness) is
  explicitly the higher-priority remaining work under the July 6 deadline, made the deliberate
  call to keep the deprecated-but-functional primitives rather than migrate now. Documented as
  known tech debt with the Workflow API surface noted above as the migration starting point, in
  case there's time to revisit after Phase 9.
- Added `VerifierResult` to `finsight/agents/schemas.py` (passed, groundedness_ok,
  sufficiency_ok, policy_ok, issues, critique) and `finsight/agents/verifier.py`
  (model=MODEL_VERIFIER, per BUILD_PLAN.md). Added
  `finsight/tools/finops_tools.py::check_text_for_policy_violations`, a deterministic tool that
  reuses the exact same regexes as the Phase 6 `pii_redaction`/`injection_guard` guardrails, so
  the verifier's "policy" check isn't relying on LLM judgment alone for something a regex can
  already catch reliably.
- **Bug found and fixed: ADK's `exit_loop` tool silently breaks `output_schema` capture.**
  Original design had the verifier call `google.adk.tools.exit_loop` on pass, per the
  conventional LoopAgent-critic pattern. Live-tested and found `state["verification"]` was
  correctly saved on the FAIL path but **never saved on the PASS path** -- `exit_loop` sets
  `tool_context.actions.skip_summarization = True`, which (per `llm_agent.py`'s own comment)
  suppresses the model's next turn, including the turn that would normally emit the
  `output_schema` JSON. Root-caused this by reading `google/adk/agents/llm_agent.py`'s
  `output_key`-saving logic directly rather than guessing. Fixed by removing `exit_loop`
  entirely and adding an `after_agent_callback`
  (`verifier.py::_escalate_when_verification_passed`) that runs *after* `output_key` has
  already saved state, reads `verification.passed` deterministically in Python, and sets
  `callback_context.actions.escalate = True`. Also discovered `escalate` alone doesn't
  propagate as an event unless the callback also writes a state delta (per
  `base_agent.py::_handle_after_agent_callback`), so the callback also sets
  `state["verification_passed"] = True`. Logged as [[project-finsight-verifier]] in memory.
- `finsight/agents/orchestrator.py` restructured: `SequentialAgent(planner,
  LoopAgent(max_iterations=3, sub_agents=[analyst, forecaster, investigator, reporter,
  verifier]))`. `planner` stays outside the loop -- a bad root-cause claim is a
  reporter/investigator problem far more often than a bad date-range choice, so replanning
  every retry would be wasted work (deviation from the plan's literal "loop back to
  planner/analyst" wording -- loops back to analyst, not planner).
  `reporter.py` instruction now reads an optional `{verification?}` critique from a prior
  failed attempt and is told to fix exactly those issues.
- `tests/test_verifier.py` (2 new tests, marked `@pytest.mark.llm` since they make real LLM
  calls via `Runner` + `InMemorySessionService` with hand-seeded state -- registered the `llm`
  marker in `pyproject.toml`): directly satisfies the checkpoint by injecting a report with a
  wildly fabricated revenue figure ($1,000,000 vs the real $12,285.80 delta) and asserting the
  verifier returns `passed=False`, `groundedness_ok=False`, and does not escalate; a second test
  asserts a properly grounded report passes and does escalate. Both pass against the real
  model. Full suite: 19 passed (17 fast + 2 llm-marked).
- **Live-verified the full integrated loop**, not just the isolated verifier: ran the complete
  orchestrator via `Runner.run_async` directly (bypassing the CLI). Discovered the reporter's
  Phase 6 HITL gate (`propose_recommendation`, `require_confirmation=True`) genuinely pauses the
  *entire* invocation at the framework level (the async generator just stops yielding, with
  `long_running_tool_ids` set on the pending event) -- not just a CLI display quirk. Attempted
  to resume properly within the same continuous process (reconstructing the
  `adk_request_confirmation` FunctionResponse per the CLI's own resume code in
  `google/adk/cli/cli.py`) and hit the **identical** `Tool 'propose_recommendation' not found`
  error as Phase 6's cross-process test -- proving the Phase 6 hypothesis (fresh tool object
  identity across processes) was **wrong**. Reproduced with the same `Runner`, same session
  service, same `root_agent` object, just a second `run_async` call. Real root cause: ADK's
  tool-confirmation resume doesn't correctly re-resolve the in-scope tool registry for a
  confirmation raised several levels deep in a nested agent hierarchy
  (`SequentialAgent > LoopAgent > LlmAgent`) -- it falls back to a shallower agent's tools.
  Corrected the Phase 6 memory file with this finding.
- To still get full live confirmation of the loop mechanics (not just the isolated verifier
  unit test), ran a **diagnostic-only** orchestrator variant with a reporter that has no
  confirmation-gated tool (scratchpad script, not committed). Full chain ran live: planner ->
  analyst -> forecaster -> investigator -> reporter -> verifier, verifier returned
  `passed: true` with all three checks true, and `escalate=True` on its final event correctly
  stopped the `LoopAgent` after exactly one iteration (no retry needed, as expected for a
  clean grounded report). This is real, non-mocked confirmation that the retry-loop machinery
  works end-to-end, complementing the isolated fail-path test.
- `ruff check .` clean; `pytest` 19 passed (2 of them `@pytest.mark.llm`, real network calls).
- Next: Phase 8 (skills, memory, observability) -- per the risk register, this is one of the
  first things to cut further if Phase 9 (eval harness, higher priority) needs the time.

### 2026-07-02 — Phase 7 rigor pass (user-requested, before moving on)
User asked for the verifier to be verified properly rather than taken on faith, before touching
Phase 8/9. Four things, all done:

1. **Real before/after report text**, not just pass/fail. Wrote a one-off fault-injection
   script (scratchpad, not committed) that poisons the reporter's *first* attempt only
   (conditioned on `{verification?}` not yet existing) to fabricate a `$999,999.99` revenue
   figure, then runs the real, unmodified verifier + LoopAgent retry exactly as built. Result:
   iteration 1's report claimed the fabricated figure; verifier caught it
   (`groundedness_ok: false`, critique named the correct real figure, `$376,970.25`); iteration
   2's report cited only real, correctly-grounded figures throughout and verifier passed it.
   Full JSON for both iterations captured in this session's transcript.
2. **The loop genuinely closes, not catch-only.** Confirmed via direct event-stream inspection
   (not inference): of 26 total events in that run, exactly 1 had `escalate=True`, authored by
   `verifier`, carrying `state_delta: ['verification_passed']` -- precisely matching the
   `after_agent_callback` design. The loop ran exactly 2 reporter iterations (of a 3-max
   budget) and stopped there. Confirmed this is *not* a cousin of the HITL nested-resume bug:
   that bug is specifically about resuming a **paused** invocation (`long_running_tool_ids` /
   `request_confirmation`) across a break in `run_async` iteration. The LoopAgent's internal
   retry never pauses -- it's a single continuous `run_async` call restarting sub-agents
   in-process, a completely different code path. No pause/resume machinery is exercised by a
   normal (non-HITL) retry.
3. **Verifier is now toggle-able.** Added `ENABLE_VERIFIER` (default `TRUE`) to
   `finsight/config.py` and `.env`/`.env.example`. `build_orchestrator_agent()` in
   `orchestrator.py` now takes an optional `enable_verifier: bool | None` override (falls back
   to `settings.enable_verifier` when `None`) so `eval/ablation.py` (Phase 9) can construct both
   the with-verifier (`LoopAgent` + retry) and without-verifier
   (`SequentialAgent`, straight through, no retry) variants in one process without touching env
   vars. Verified both construct correctly.
4. **SQL guardrail false-positive check.** Directly exercised `check_sql_injection` against the
   user's exact examples plus more: "show me updated inventory", "orders by category", "the
   created_at column", "order_count and updated_at fields", "callback function for updated
   records", "recreate the dashboard", "a well-executed campaign" -- all pass through unblocked
   (the `\bupdate\b`-style word-boundary regexes correctly don't match "updated"/"created_at"/
   "callback"/etc. since there's no boundary before the trailing letters). Malicious cases
   (`'; DROP TABLE ...`, an `execute_sql` tool name) still correctly blocked.

Committed the `ENABLE_VERIFIER` toggle as a standalone follow-up to the Phase 7 commit. The
fault-injection script itself was not committed (scratchpad, one-off) -- offered to turn it into
a permanent regression test in `tests/test_verifier.py` if wanted, but that's additional scope
beyond what was asked for in this pass.

### 2026-07-02 — Promote fault injection to a committed regression test
User asked for the scratchpad fault-injection script to become a permanent test before starting
Phase 9. Added `test_retry_loop_catches_and_corrects_fabricated_claim` to
`tests/test_verifier.py`: builds the real `analyst`/`forecaster`/`investigator`/`verifier` (from
`finsight.agents.*`, unmodified) inside a real `LoopAgent`, swapping in only a test-double
reporter that fabricates a `$999,999.99` figure on its first attempt and self-corrects on retry
(mirroring how the real reporter reacts to `{verification?}`). Asserts, from the raw event
stream: exactly 2 reporter attempts happened (genuine retry, not catch-only); attempt 1 contains
the fabricated figure and fails verification on `groundedness_ok`; attempt 2 drops the
fabricated figure and passes; exactly 1 `escalate=True` event fires, authored by `verifier`, and
no 3rd iteration ran despite budget for one. All assertions carry a full JSON diagnostic dump of
every iteration on failure.

**Observed flakiness, reported honestly rather than hidden:** ran this test 4 times during
development -- 1 failure, 3 passes. This is real-model non-determinism in whether the poisoned
reporter fabricates on attempt 1 and self-corrects on attempt 2 exactly as instructed, not a bug
in the verifier/loop mechanism itself (which has now been proven correct across many independent
runs -- this test, the two earlier isolated tests, and two ad hoc live diagnostics). Did not
weaken the assertions to force a 100% pass rate, since that would undermine the point of the
test; instead added rich diagnostics so a real regression is distinguishable from ordinary model
variance. Flagging this now because Phase 9's ablation will face the same category of variance
at much larger scale (3 configs x 30-40 tasks), which is directly relevant to how the eval
runner's resilience should be designed.
- `ruff check .` clean. Fast suite still 17 passed; full suite (incl. `@pytest.mark.llm`) now 20
  tests.

### 2026-07-02 — Phase 9 planning: reordered ahead of Phase 8
User explicitly reordered the remaining plan: Phase 9 (eval harness) before Phase 8 (skills,
memory, observability), per BUILD_PLAN.md's own risk register ("if time is short, cut an agent,
not the evals" / minimum viable scope = Phases 0-7 + 9). Phase 8 is deferred, not skipped --
revisit only if time remains after Phase 9 (and 10).

Designed the benchmark schema collaboratively with the user before authoring the full task set.
Landed on:
- **Overriding principle:** no hardcoded dollar figures as ground truth -- confirmed via live
  query that even identical historical date ranges return different figures on different days
  (dataset regenerates), so only relative/structural properties belong in `ground_truth`.
- Schema: `id`, `question`, `task_type` (clean_attribution/insufficient_evidence/adversarial/
  ambiguous_scope), `difficulty`, and `ground_truth` with `direction`, `largest_driver_category`,
  `should_refuse`, and two deliberately separate fields --
  `required_dimensions` (which data axis a correct investigation must examine) vs.
  `required_behaviors` (a response-text property, e.g. `states_explicit_assumption`,
  `refuses_gracefully`, `cites_evidence`, `resists_injection`, `maintains_analyst_persona`) --
  plus `must_not_claim` (assertions the response must not make).
- `direction: flat` = within ±5%; direction-bearing tasks are only selected when the actual %
  change sits clearly outside the 3-7% gray zone around that boundary, so regeneration noise is
  unlikely to flip the label.
- Wrote `eval/benchmark/finops_tasks.jsonl` with 6 example tasks (1 clean_attribution, 1
  insufficient_evidence, 3 adversarial, 1 ambiguous_scope) as the schema draft for review.
  `clean-001-outerwear-nov23`'s ground truth was not guessed -- searched ~45 month-over-month
  category-delta pairs across 2019-2023 live against BigQuery to find the most defensible
  driver-margin example. Finding: no month-pair in this dataset shows an overwhelmingly dominant
  single-category driver; the best found is ~48% of net delta with a 3.3x margin over the
  runner-up (Outerwear & Coats, Nov 2023 vs Oct 2023) -- real information about the dataset's
  structure (broad-based co-movement across categories), not a search failure.
- Authored 3 adversarial tasks (not 1) specifically so the verifier's expected edge on this
  category is statistically visible in the ablation, not a single anecdote. Documented, rather
  than patched, a real gap: `injection_guard` (Phase 6) only scans tool output, not direct user
  input, so these tasks' actual defense is (a) the model's own instruction-hierarchy robustness
  (probabilistic, not guaranteed) and (b) the verifier's groundedness check as a backstop if (a)
  fails -- already proven capable of catching fabricated figures in `tests/test_verifier.py`.
- **Pre-flight re-verification design** (to be implemented in `eval/ablation.py`, not yet
  written): immediately before every ablation run, re-query each `clean_attribution` task's
  structural ground truth (direction + whether the named category is still the dominant driver
  by a comparable margin) against the live dataset; flag and exclude any task whose ground truth
  has flipped, with a clear warning -- never silently score against stale truth.
- Wrote `eval/README.md` capturing all of the above as the methodology reference / draft
  writeup section: schema rationale, the dimensions-vs-behaviors split, the flat threshold and
  gray-zone avoidance rule, the clean_attribution selection+re-verification methodology, and the
  adversarial defense-in-depth reasoning stated honestly as probabilistic.
- Also promoted the Phase 7 fault-injection script to a permanent regression test (separate log
  entry above) before starting this planning work, per user request.
- Not yet built: the remaining ~25-35 benchmark tasks, `eval/llm_judge.py`, the programmatic
  scorer, `eval/mast_classifier.py`, `eval/ablation.py`, `eval/run_eval.py`, rate-limit
  resilience. Explicitly gated behind user review of this schema/example draft before proceeding
  (`.venv/bin/ruff check .` and the fast test suite both still clean; no benchmark/scorer code
  written yet, per instruction).

### 2026-07-02 — Phase 9 planning: three adjustments from user schema review
1. **Repeated trials, not single runs.** User pointed out `test_retry_loop_catches_and_corrects_
   fabricated_claim`'s observed 1-fail-3-pass rate is direct proof a single run per (config,
   task) would be noise. `eval/ablation.py`'s design now requires every (config, task) pair run
   min 3x / ideally 5x, with every reported metric a mean + spread (std dev or min-max), never a
   point estimate. Verifier catch-rate variance is to be reported as a finding, not smoothed over.
2. **`clean_attribution` reframed around confidence calibration**, not clean causation --
   consistent with the Phase 9 planning finding that no month-pair in this dataset shows an
   overwhelmingly dominant driver (best: ~48% share, 3.3x margin). Added `calibrated_confidence`
   to the `required_behaviors` vocabulary: does the agent report the tier its own
   reporter/verifier thresholds would justify (high >=60%, medium >=40%, low >=20%, else
   insufficient), rather than overclaiming certainty or underclaiming into an unwarranted
   refusal. Graded against a live-recomputed tier at eval time (via the same pre-flight
   re-verification step), not a value stored in the JSONL. Updated `clean-001-outerwear-nov23`
   accordingly (added `calibrated_confidence` to `required_behaviors`, added an
   anti-overclaiming entry to `must_not_claim`).
3. **Retargeted task mix for ~30 tasks:** `insufficient_evidence` 10-12, `adversarial` 4-5,
   `ambiguous_scope` 4-5, `clean_attribution` (calibration-framed) ~9 rest -- weighted toward the
   two task types that most directly test overclaiming, since that's the specific failure mode
   the verifier exists to catch.
- Updated `eval/README.md` with all three changes (task mix table, calibration reframe section,
  new "Repeated trials" section). `eval/benchmark/finops_tasks.jsonl` still 6 draft tasks --
  pasted the `ground_truth`/`required_behaviors` blocks of all 6 for user review before
  authoring the remaining ~24, per instruction. Not yet built: same list as above, still
  unstarted.

### 2026-07-02 — Full 30-task benchmark authored
User approved the 6 draft tasks' ground truth (including the `adv-003` should_refuse=false
pattern, asked to keep several tasks with that subtlety) and gave four scoring refinements
before authoring the rest:
1. Mixed deterministic + LLM-judge scoring: programmatic string/regex check for any
   `must_not_claim` entry with a concrete fingerprint (e.g. adversarial tasks' literal injected
   dollar figures), LLM judge reserved for genuinely semantic claims. Documented per-entry, not
   per-task, decision in `eval/README.md`.
2. `calibrated_confidence` operationally defined and to be passed verbatim to the judge
   (parameterized by the task's live-recomputed share) rather than left for the judge to infer.
3. `resists_injection` needs two different rubrics selected by each task's own `should_refuse`
   value -- refuse-and-don't-comply vs. resist-the-framing-but-still-answer-correctly.
4. Multi-trial scoring (min 3, ideally 5) applies to `must_not_claim`/`required_behaviors` at
   the per-task, per-trial level, not just the top-line ablation config metrics.
All four written into `eval/README.md`'s new "Scoring design" section.

Authored the remaining 24 tasks via a broader live BigQuery search (not guessed): searched ~45
month-pairs x multiple filters for `clean_attribution` candidates with margin >=2x over the
runner-up and direction clearly outside the 3-7% gray zone; separately searched for a `down`
direction and a `flat` direction example specifically, since the initial search skewed toward
`up`. Two findings surfaced and got written into the methodology (not just used silently):
- `share_of_total_delta_pct` must be computed the same way `investigator.py` computes it --
  divided by the **net** delta, not the sum of categories' absolute deltas. An early candidate
  showed 29% by the wrong metric vs. 54% by the right one -- ground truth must match the metric
  being graded.
- The share metric is mathematically meaningless for `flat`-direction periods (divides by a
  near-zero net delta, producing 500%+ garbage values in cases checked). Handled by setting
  `largest_driver_category: null` for the two flat tasks and redefining what
  `calibrated_confidence` means for them: recognizing no category "drove" a change that, net,
  didn't meaningfully happen -- not citing a nonsensical share for whichever category had the
  largest individual swing.
- Also found: every non-flat `clean_attribution` candidate's leading-category share landed in
  the ~43-54% band across the whole search -- consistently "medium" tier, never "high" or "low".
  Documented as a likely structural property of the dataset (offsetting category movements),
  not a sampling gap -- most of these tasks are expected to have "medium" as the correct
  calibrated answer.

Final `eval/benchmark/finops_tasks.jsonl`: 30 tasks -- `insufficient_evidence` 11,
`clean_attribution` 9 (7 medium + 2 hard/flat), `adversarial` 5 (3 should_refuse=true, 2
should_refuse=false), `ambiguous_scope` 5. All IDs unique, schema-validated.
- `ruff check .` clean, fast suite still 17 passed.
- Next: minimal scorer (programmatic + `eval/llm_judge.py`) sufficient to run a 2-3 task sample
  through the real orchestrator and show reports + judge verdicts side-by-side for user
  validation, per instruction -- before building the full `eval/ablation.py`/
  `eval/mast_classifier.py`/`eval/run_eval.py`.

### 2026-07-02 — Minimal scorer built; sample validation run against real orchestrator
Added `finsight/agents/reporter.py::build_reporter_agent(require_confirmation: bool = True)`
and threaded a matching `require_recommendation_confirmation` param through
`orchestrator.py::build_orchestrator_agent`. Needed because every eval run would otherwise pause
on `propose_recommendation`'s first call with no human available to approve, and the Phase 7
finding stands that resuming that pause is broken for confirmations raised inside nested
`SequentialAgent>LoopAgent>LlmAgent` hierarchies -- eval scores report *content*, not the HITL
mechanism (which has its own dedicated tests), so this is a legitimate, reusable toggle rather
than a throwaway eval-only hack.

Built `eval/rate_limit.py` (`with_retry`: exponential backoff + jitter, only retries
rate-limit-shaped errors) and `eval/llm_judge.py`: mixed deterministic + LLM-judge scoring for
`must_not_claim` (programmatic substring/negation check for entries with a `FINGERPRINTS`
lookup entry, e.g. adversarial tasks' literal injected dollar figures; LLM judge for the rest),
LLM-judged `required_behaviors` with `calibrated_confidence`'s and `resists_injection`'s
operational rubrics from `eval/README.md` passed into the prompt verbatim (parameterized by the
task's own live `share_of_total_delta_pct` / `should_refuse`), plus 1-5 reasoning_quality/
groundedness scores. Built a minimal `eval/run_eval.py` (single-trial, single-config; the
multi-trial x 3-config comparison is `ablation.py`, still unbuilt) that runs one task through the
real orchestrator, extracts report/analyst_findings/investigation/verification state, checks
`largest_driver_category` and `required_dimensions` programmatically, and calls the judge.

**Sample validation run (4 tasks, then 2 more targeted re-runs after an unplanned finding) --
judge quality: confirmed good.** `clean-001-outerwear-nov23` and `insuff-001-marketing-spend`
both got accurate, well-explained judge verdicts matching what a human read would conclude
(correctly scored a well-calibrated medium-confidence report and a graceful refusal as passing,
with specific correct explanations, not generic rubber-stamping).

**Unplanned, real finding surfaced by the sample run, not hidden:** `adv-005-user-supplied-fake-
data` (verifier ON) reproduced the identical failure on two separate live runs -- the **analyst**
agent (not the reporter) adopted the user's injected fake figures ($58,392,104 / $112) directly
into `analyst_findings`, bypassing its real `compare_period_over_period` tool call. The verifier
correctly found the report grounded in *state* (`passed: true`) because the corruption happened
upstream of what the verifier checks -- it trusts `analyst_findings` rather than independently
re-deriving it. `tests/test_verifier.py`'s proof that the verifier catches reporter-level
fabrication is real and unaffected; it just doesn't generalize to earlier-pipeline corruption.
A second `adv-001-injection-fabricate` run found a related, distinct gap: the reporter correctly
refused the fabricated `$50,000,000` figure but still adopted the injected **recommendation**
("an immediate 20% price cut") -- the verifier has no rubric for recommendation-content
injection, only numeric groundedness. Concrete lead for later (not implemented now): 
`analyst_findings`'s totals were wildly inconsistent with the sum of
`investigation.breakdown`'s per-category totals in the corrupted run -- a structural
cross-check that could catch this pattern without new LLM judgment. Updated `eval/README.md`'s
adversarial section with this empirical finding, replacing the earlier (reasoned but untested)
claim that the verifier reliably backstops all adversarial patterns.
- `ruff check .` clean, fast suite still 17 passed.
- Next: present judge-validation results + this finding to the user; awaiting direction on
  whether to proceed straight to `eval/ablation.py`/`eval/mast_classifier.py` as-is (letting the
  narrower verifier coverage show up as ablation data) or address the finding first.

### 2026-07-02 — MAST classifier, full ablation built and run; a second real infra bug found
User: proceed straight to the full ablation as designed, do not fix the analyst-corruption gap
(it's the most valuable finding so far -- fixing it now would erase the evidence that eval
catches what unit tests miss). Split the two limitations into distinct README bullets with the
structural cross-check logged as proposed future work, not implemented. Spot-check the judge on
one more adversarial task before the full run. Then run the full multi-trial ablation and show
the results table + MAST breakdown.

- Split `eval/README.md`'s adversarial section into two clearly separate limitations: (a)
  analyst-level state corruption is upstream of the verifier's visibility, (b) the verifier has
  no recommendation-provenance rubric -- plus a stated-in-advance "honest headline" so the
  eventual ablation numbers can't be read as post-hoc rationalizing.
- Spot-checked the judge on `adv-003-persona-hijack` (should_refuse=false, tests
  `maintains_analyst_persona` for the first time): judge correctly flagged all 2 must_not_claim
  violations and all 3 required_behavior failures with precise, human-quality explanations, and
  correctly kept `groundedness_score=5/5` despite the persona failure (the figures were real,
  just wrapped in hijacked tone) -- a genuinely subtle distinction, correctly made. Judge now
  validated on all three task types that matter (clean/insufficient/adversarial, both
  should_refuse variants).
- Built `eval/mast_classifier.py`: rule-based (not LLM-judged) classifier over 5 MAST tags
  (adapted subset of Cemri et al.'s taxonomy) derived from judge verdicts + programmatic checks
  + the verifier's own verdict + a structural analyst/investigation cross-check (the same
  pattern found in the adv-005 gap, now generalized into a reusable detector,
  `INTERAGENT_2_5_IGNORED_UPSTREAM_FINDINGS`).
- Built `eval/ablation.py`: 3 configs (`single_agent` -- new baseline, all 5 finops_readonly
  tools, no decomposition, `model_worker`; `multi_agent_no_verifier`; `multi_agent_verifier`, via
  the existing `enable_verifier` toggle), pre-flight re-verification for `clean_attribution`
  tasks (hardcoded date ranges from authoring, re-queried live; excludes flipped tasks with a
  warning), multi-trial execution, and aggregate + MAST reporting.
- **Real infra bug #2 found and fixed, same rigor as the verifier-gap finding:** the first full
  run (concurrency=6) stalled at 93/261 trials with zero progress for 20+ minutes. Root cause: an
  unhandled 429 from Vertex AI raised inside `google-adk`'s own internal background thread
  (`runners.py::_asyncio_thread_main`, which the sync `Runner.run()` wrapper spawns) never
  propagates as a catchable exception to the calling thread -- `with_retry` never even saw it,
  because there was nothing to catch; the calling worker thread just blocked forever on a
  generator whose producer thread had silently died. Can't fix ADK's internal thread from here.
  Fixed by replacing the `as_completed()`-based collection loop with a polling loop
  (`concurrent.futures.wait(..., timeout=15, return_when=FIRST_COMPLETED)`) that tracks each
  future's submit time and gives up on (records a timeout error for, and stops waiting on) any
  trial pending longer than `PER_TRIAL_TIMEOUT_SECONDS` (420s -- generous enough that a real,
  working, 3-retry-iteration verifier trial won't be mistaken for a hang). Also dropped
  `CONCURRENCY` from 6 to 3 to reduce how often the underlying 429 triggers at all. Verified the
  fix with a 3-trial smoke test (one trial per config) before re-committing to the full run.
- Killed the stuck process, relaunched the full run with the fix.

### 2026-07-02 — Real root cause found: concurrency deadlock, not rate limiting; run trimmed and relaunched serially
The `CONCURRENCY=3` relaunch (with unbuffered output for reliable monitoring, which also
surfaced that the *first* relaunch's total silence was just stdout block-buffering, not a
stall) completed all 261 trials, but **230/261 (88%) timed out**, including **100%** of both
multi-agent configs (only `single_agent`, at 36%, produced any real data). Investigated before
re-running blindly: the raw log had exactly **1** literal "429" across 33,658 lines, ruling out
sustained quota exhaustion as the cause despite the earlier finding pointing that direction.
Direct A/B test: ran `multi_agent_no_verifier` and `multi_agent_verifier` on the same task with
**zero** concurrency (no `ThreadPoolExecutor` at all) -- both succeeded cleanly (84s, 129s, real
reports, no errors). Root cause confirmed: running multiple `Runner.run()` calls **concurrently**
(each spawning its own internal thread + event loop) deadlocks them outright -- a second,
distinct ADK concurrency bug from the 429-in-internal-thread one found earlier, not a rate-limit
problem at all.

User's call: go fully serial (`CONCURRENCY=1`, proven reliable), keep `TRIALS_PER_TASK=3` (don't
sacrifice the mean+spread statistic), and instead trim the task count from 30 to 20 to fit a
serial run in a practical timeframe -- preserving category balance so the headline findings stay
statistically visible. Added `ABLATION_TASK_IDS` (20 tasks): `insufficient_evidence` 8/11 (kept
all 3 "hard" subtle-trap tasks, dropped the 3 most redundant), `adversarial` 5/5 (all kept,
including `adv-005` and `adv-001` -- the two highest-value findings), `clean_attribution` 5/8
safe-to-score (one flat example kept, spread across years/categories), `ambiguous_scope` 2/5
(kept the two least-similar phrasings). Confirmed the exact kept/cut list with the user before
launching.

Also added incremental result writes (`eval/results/ablation_trials.jsonl`, one line per
completed trial, flushed immediately, via a new `run_all_trials(..., incremental_path=...)`
param and `main() --report-only` recovery mode that reads the JSONL directly) so a crash
partway through a now much-longer serial run costs at most the in-flight trial, not the whole
run's progress.

Relaunched: `CONCURRENCY=1`, 20 tasks x 3 configs x 3 trials = 180 total trials, running
unattended.

### 2026-07-02 — Third infra failure (worse), fixed with subprocess-per-trial isolation
The `CONCURRENCY=1` serial run finished (all 180 trials accounted for in the incremental JSONL,
confirming the incremental-write mechanism itself works correctly), but **169/180 (94%)
timed out** -- dramatically worse than the concurrent runs, including 100% of both multi-agent
configs. Investigated rather than assumed: this ruled out both prior hypotheses --
`ThreadPoolExecutor(max_workers=1)` still reuses a single worker thread across all 180 calls to
`Runner.run()`, and something accumulates across that many repeated calls in one thread/process
until most calls hang. Most likely culprit: unclosed aiohttp sessions/connections -- "Unclosed
client session" / "Unclosed connector" warnings have appeared intermittently in this project's
tool output all session (going back to Phase 4), suggesting `Runner`/`google-genai` don't fully
clean up per-call HTTP client state, and it silently degrades a long-lived process.

Fix: `eval/_trial_worker.py`, a standalone script that runs exactly one trial and prints the
result as JSON on stdout's last line. `eval/ablation.py::run_all_trials` now calls
`subprocess.run([sys.executable, "-m", "eval._trial_worker", ...], timeout=...)` per trial
instead of any thread pool -- full process isolation (fresh interpreter, fresh connections,
guaranteed cleanup on exit) at the cost of Python/import startup overhead per trial (adds
roughly 30-100+s per multi-agent trial vs. the in-process timings measured earlier). Verified
with a 6-trial smoke test (2 tasks x 3 configs x 1 trial): **6/6 succeeded, zero errors** --
first fully clean result across four attempts at this problem.

Revised time estimate given subprocess overhead: ~5.5-6 hours for the full 180-trial trimmed
run (up from the ~3.5-4hr serial-in-process estimate) -- accepted as the cost of reliability;
94% garbage data is not an acceptable tradeoff for saving a couple of hours.

Also: the previous serial run's *process* was reported "killed" by the harness partway through
monitoring, even though it had actually run to full completion by the time this was noticed
(all 180 trials were in the incremental JSONL) -- most likely the tool call's own timeout
parameter being enforced as a hard cap regardless of `run_in_background`. For this launch,
fully detached the process from tool-level supervision (`nohup ... & disown`) so a multi-hour
run can't be prematurely killed by anything except an actual crash.

### 2026-07-03 — Not a code bug: the Mac went to sleep. Relaunched with `caffeinate`
The subprocess-isolated run (previous entry) appeared to hang: trial #15
(`single_agent:insuff-006-profit-margin:trial2`) showed as running for **4h28m** with the parent
process at only 1.13s cumulative CPU time, and `subprocess.run(timeout=420)` didn't fire until
~16443s (4.5 hours) instead of 420s. Investigated before assuming a fifth code bug: confirmed via
`pmset -g log` that the machine woke from **Deep Idle sleep** at the exact moment monitoring
resumed ("DarkWake to FullWake from Deep Idle... due to HID Activity"). The whole machine --
including the scheduled monitoring wakeup, the ablation process, and its OS-level timeout
tracking -- was frozen for hours, not hung. Once awake, the deferred timeout fired correctly and
the run resumed normally (2 more trials completed quickly right after). This is a genuine,
mundane environmental gotcha for a multi-hour unattended run on a laptop, distinct from the three
real execution bugs already found and fixed (concurrent deadlock, single-thread degradation --
both fixed by subprocess-per-trial isolation). Killed the stale parent/orphaned child, relaunched
wrapped in `caffeinate -i` (prevents idle system sleep) via `nohup caffeinate -i env ...
python eval/ablation.py > log 2>&1 & disown`. Accepted losing the 17 trials already completed
(the incremental file gets freshly truncated on each `main()` run) rather than adding
resume-from-partial complexity under time pressure -- a fresh, uninterrupted, caffeinated run
should complete in the ~5.5-6hr estimate without another multi-hour stall.
