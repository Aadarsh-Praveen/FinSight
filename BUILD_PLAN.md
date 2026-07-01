# FinSight — Build Plan for Claude Code

> **What this file is.** This is the master implementation plan for **FinSight**, a multi-agent
> FinOps (cloud-spend intelligence) analyst built on **Google ADK 2.0**, **Gemini**, **BigQuery via
> MCP Toolbox**, and deployed to **Cloud Run**. It is written to be read and executed by **Claude
> Code** in the terminal, phase by phase.
>
> **How to use it (Claude Code).** Work through the phases in order. Do not skip ahead. At the end of
> every phase there is a **✅ Checkpoint** — stop, run the stated verification command, and confirm it
> passes before starting the next phase. If a step depends on a human action (billing, OAuth, secrets),
> it is tagged **🧑 HUMAN STEP** — pause and tell the user to do it, then wait.
>
> **Golden rules for the agent building this:**
> 1. Prefer small, verifiable commits per phase. Never write the whole app in one shot.
> 2. Never hardcode secrets, project IDs, or dataset names — read them from environment variables.
> 3. Every agent-callable database tool must be **read-only**. Enforce this in config, not just prompt.
> 4. Keep the evaluation harness a first-class citizen. If time is short, cut an agent, not the evals.
> 5. After each phase, update `PROGRESS.md` with what was done and what's next.

---

## 0. Project facts & assumptions (read first)

- **Framework:** Google ADK **2.0** (Python). ADK 2.0 introduced a graph-based `Workflow` runtime and
  a `Task` API for agent-to-agent delegation. It requires **Python 3.10+**. Pin the version in
  `requirements.txt` (`google-adk~=2.0`). If any API in this plan conflicts with the installed
  version, **trust the installed library's docstrings/`--help` over this file** and note the deviation
  in `PROGRESS.md`.
- **Models:** `gemini-2.5-flash` for routing and worker sub-agents; `gemini-2.5-pro` for the
  verifier and final report writer. Make the model IDs configurable via env vars so they can be
  swapped if needed.
- **Data access:** BigQuery, exposed to agents through the **MCP Toolbox for Databases** (open-source
  binary). Use a custom `tools.yaml` with **parameterized, read-only** SQL tools rather than raw
  `execute_sql`, so the agent cannot run arbitrary or destructive queries.
- **Dataset:** Start with the BigQuery public dataset **`bigquery-public-data.thelook_ecommerce`**,
  framed as *revenue/sales anomaly investigation*. This removes the need to source private billing
  data and works on the free tier. A synthetic FOCUS-format cloud-billing dataset is an optional
  later upgrade (see Phase 9, stretch).
- **Deploy target:** Cloud Run.
- **Deadline:** Build to **June 30, 2026** as the internal target. (The user's document lists July 6;
  reputable press listed June 30. Treat June 30 as the safe deadline unless the official Kaggle page
  says otherwise.) **🧑 HUMAN STEP:** confirm the real deadline on the official competition page.

---

## 1. What the user (human) must do — the checklist

These are the things Claude Code **cannot** do for you. Do them in roughly this order. Each is
referenced later by the phase that needs it.

### Accounts & access
1. **Google Cloud account with billing enabled.** New accounts get free credits. You need this for
   BigQuery + Cloud Run. → needed by Phase 2.
2. **Create a GCP project** (e.g. `finsight-hackathon`) and note the **Project ID**. → Phase 2.
3. **Google AI Studio API key** (free, no card) for local Gemini prototyping, OR plan to use Vertex
   AI auth. Keep the key out of git. → Phase 3.
4. **Kaggle account** + join the competition; skim the official rules, deadline, and submission
   format. → Phase 10.

### Local machine prerequisites (tell Claude Code your OS so it installs the right binary)
5. **Python 3.10+** installed. Verify: `python --version`.
6. **`gcloud` CLI** installed and authenticated:
   - `gcloud auth login`
   - `gcloud auth application-default login`  ← this is the credential the MCP Toolbox uses (ADC)
   - `gcloud config set project YOUR_PROJECT_ID`
7. **Git** installed and a GitHub repo created (public, for the submission code link).
8. **Docker** installed (for containerized Cloud Run deploy later). → Phase 8.

### Decisions to make (answer these so the agent doesn't guess)
9. **Your OS/arch** (Linux amd64 / macOS arm64 / macOS amd64 / Windows) — determines the Toolbox
   binary download.
10. **Region** for Cloud Run + BigQuery jobs (e.g. `us-central1`). Keep BigQuery `location` consistent.
11. **Project name / GitHub repo URL** you want to use.

### Things you'll record as you go (put them in `.env`, never in git)
- `GOOGLE_CLOUD_PROJECT` — your GCP project ID
- `GOOGLE_CLOUD_LOCATION` — e.g. `us-central1`
- `GOOGLE_GENAI_USE_VERTEXAI` — `TRUE` (use Vertex) or `FALSE` (use AI Studio key)
- `GOOGLE_API_KEY` — only if using AI Studio
- `BIGQUERY_PROJECT` — usually same as `GOOGLE_CLOUD_PROJECT`
- `MODEL_ROUTER`, `MODEL_WORKER`, `MODEL_VERIFIER` — the Gemini model IDs

> **🧑 HUMAN STEP recap:** Items 1–4, 6, and 9–11 are blocking. Do 1–3 and 6 before Phase 2/3.

---

## 2. Target project structure

Claude Code should scaffold **exactly** this structure in Phase 3 and keep it consistent. This layout
separates agents, tools, evaluation, and deployment cleanly — it reads as production-grade to anyone
reviewing the repo (recruiters, judges).

```
finsight/
├── README.md                      # Top-level: what it is, architecture diagram, quickstart, results
├── BUILD_PLAN.md                  # This file
├── PROGRESS.md                    # Living log the agent updates each phase
├── .env.example                   # Template of required env vars (committed)
├── .env                           # Real secrets (git-ignored, NEVER committed)
├── .gitignore
├── requirements.txt               # Pinned deps
├── pyproject.toml                 # Optional: packaging/lint config
├── Dockerfile                     # Cloud Run container
├── .dockerignore
│
├── finsight/                      # Main Python package (the ADK app)
│   ├── __init__.py
│   ├── config.py                  # Loads env vars, model IDs, dataset names (no secrets in code)
│   ├── agent.py                   # root_agent definition (ADK entrypoint: `adk run finsight`)
│   │
│   ├── agents/                    # One module per specialized sub-agent
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Root router: plans, delegates, manages state, termination
│   │   ├── planner.py             # Decomposes the question into an analysis plan
│   │   ├── analyst.py             # NL->SQL over BigQuery via MCP Toolbox (read-only tools)
│   │   ├── forecaster.py          # Calls BigQuery AI.FORECAST (TimesFM) for expected vs actual
│   │   ├── investigator.py        # Correlates the delta with drivers; names likely root cause
│   │   ├── verifier.py            # Critic: groundedness / sufficiency / policy check before output
│   │   └── reporter.py            # Writes final structured, cited recommendation
│   │
│   ├── tools/                     # Tool wiring (MCP client, custom function tools)
│   │   ├── __init__.py
│   │   ├── mcp_bigquery.py        # Loads MCP Toolbox toolset into ADK
│   │   └── finops_tools.py        # Any custom Python function-tools (math, formatting)
│   │
│   ├── skills/                    # Agent "skills" = FinOps playbooks (progressive disclosure)
│   │   ├── rightsizing/SKILL.md
│   │   ├── commitments/SKILL.md
│   │   └── anomaly_triage/SKILL.md
│   │
│   ├── guardrails/                # Security callbacks / plugins
│   │   ├── __init__.py
│   │   ├── sql_readonly.py        # Blocks non-SELECT / DDL / DML
│   │   ├── pii_redaction.py       # Redacts sensitive fields from inputs/outputs
│   │   └── injection_guard.py     # Basic prompt-injection heuristics (OWASP LLM01)
│   │
│   └── memory/
│       └── session.py             # Session + long-term memory config (org context, past runs)
│
├── mcp-toolbox/                   # MCP Toolbox server config (lives beside the app)
│   ├── tools.yaml                 # Parameterized, READ-ONLY BigQuery tools
│   └── README.md                  # How to download + run the toolbox binary
│
├── eval/                          # ⭐ The differentiator — treat as first-class
│   ├── __init__.py
│   ├── benchmark/
│   │   └── finops_tasks.jsonl     # 30-50 tasks: question + ground-truth root cause / answer
│   ├── run_eval.py                # Runs agent over benchmark, scores success + trajectory
│   ├── llm_judge.py               # Rubric-based LLM-as-judge scorer
│   ├── mast_classifier.py         # Classifies failures into MAST taxonomy categories
│   ├── ablation.py                # single-agent vs multi-agent vs multi-agent+verifier
│   └── results/                   # Generated: metrics tables, charts (git-ignored or committed)
│
├── tests/                         # Unit/integration tests (pytest)
│   ├── test_guardrails.py
│   ├── test_tools.py
│   └── test_agents_smoke.py
│
├── deployment/
│   ├── deploy_cloud_run.sh        # gcloud run deploy wrapper
│   └── cloudbuild.yaml            # Optional CI build
│
├── notebooks/                     # Optional scratch / EDA (keep out of the main path)
│   └── explore_dataset.ipynb
│
└── .github/
    └── workflows/
        └── ci.yml                 # Lint + tests on push (GitHub Actions)
```

**Why this structure signals quality:** clear separation of `agents/`, `tools/`, `guardrails/`,
`memory/`, and especially a top-level `eval/` package tells a reviewer you think about reliability and
testing, not just demos.

---

## 3. Phase-by-phase build

> Each phase = a focused unit of work with a checkpoint. Update `PROGRESS.md` after each.

### Phase 0 — Repo bootstrap & hygiene
**Goal:** empty but professional repo that runs `pytest` (with zero tests) and lints clean.

Steps:
1. `git init`; create the folder tree from section 2 with empty `__init__.py` files and placeholder
   modules containing docstrings + `TODO`s.
2. Write `.gitignore` (ignore `.env`, `__pycache__/`, `*.pyc`, `eval/results/`, the toolbox binary,
   `.venv/`, service-account JSON).
3. Write `.env.example` listing every variable from section 1 (no real values).
4. Create a virtualenv; write `requirements.txt` with pinned deps:
   `google-adk~=2.0`, `toolbox-core`, `google-cloud-bigquery`, `google-genai`, `pydantic`,
   `python-dotenv`, `pytest`, `ruff`. Install them.
5. Write `README.md` skeleton (title, one-line pitch, architecture placeholder, quickstart, results
   placeholder).
6. Write `PROGRESS.md` with a phase table.

**✅ Checkpoint:** `pip install -r requirements.txt` succeeds; `python -c "import google.adk"` works;
`ruff check .` passes; `pytest` runs (0 tests OK). Commit: `chore: bootstrap repo`.

---

### Phase 1 — Config & environment plumbing
**Goal:** one place that loads all settings; app fails loudly if a required var is missing.

Steps:
1. Implement `finsight/config.py`: load `.env` via `python-dotenv`; expose a typed `Settings`
   (pydantic) with project, location, model IDs, dataset name, toolbox URL. Validate required fields.
2. Add a `finsight/config.py` self-check (`python -m finsight.config`) that prints the resolved,
   non-secret settings so the human can eyeball them.

**🧑 HUMAN STEP:** copy `.env.example` → `.env` and fill in real values (see section 1).

**✅ Checkpoint:** `python -m finsight.config` prints correct project/region/models and raises a clear
error if a required var is missing. Commit: `feat: config loader`.

---

### Phase 2 — Google Cloud + BigQuery readiness
**Goal:** confirm the environment can actually query BigQuery before any agent code depends on it.

Steps (mostly human, agent writes helper scripts):
1. **🧑 HUMAN STEP:** enable APIs:
   `gcloud services enable bigquery.googleapis.com run.googleapis.com aiplatform.googleapis.com`
2. **🧑 HUMAN STEP:** confirm ADC: `gcloud auth application-default login`.
3. Agent writes `scripts/check_bigquery.py` that runs a tiny query against
   `bigquery-public-data.thelook_ecommerce.orders` (e.g. `SELECT COUNT(*)`), printing the row count.
4. Run it to prove connectivity + auth.

**✅ Checkpoint:** `python scripts/check_bigquery.py` returns a count without auth errors. Commit:
`chore: verify bigquery connectivity`.

---

### Phase 3 — MCP Toolbox: read-only BigQuery tools
**Goal:** a running MCP Toolbox server exposing **parameterized, read-only** tools over the dataset.

Steps:
1. Agent writes `mcp-toolbox/tools.yaml` defining:
   - a `sources` entry `type: bigquery` with the project + location,
   - several **`bigquery-sql`** tools with fixed SQL + typed parameters, e.g.
     `get_revenue_by_period`, `get_orders_by_category`, `get_daily_sales`,
     `compare_period_over_period`. **No raw `execute_sql` exposed to the agent by default.**
   - a `toolset` grouping them (e.g. `finops_readonly`).
2. Agent writes `mcp-toolbox/README.md` with the exact binary download command for the user's OS
   (ask the user their OS; use the `v0.28.0`+ Toolbox from
   `https://storage.googleapis.com/genai-toolbox/<VERSION>/<OS>/toolbox`) and the run command
   (`./toolbox --tools-file mcp-toolbox/tools.yaml`, default port 5000).
3. **🧑 HUMAN STEP:** download the binary (agent can't fetch it — network), `chmod +x toolbox`, and
   run it in a separate terminal.
4. Verify tools load: check the server log lists the expected tools, or use MCP Inspector.

**✅ Checkpoint:** toolbox server logs `Initialized N tools` for your toolset; a manual tool call
(via Inspector or curl) returns rows. Commit: `feat: mcp toolbox read-only bigquery tools`.

> **Security note for the agent:** the read-only guarantee comes from the fixed SQL in `tools.yaml`.
> Do **not** add an arbitrary-SQL tool to the default toolset. If NL2SQL flexibility is needed later,
> gate it behind the `sql_readonly` guardrail (Phase 6) and keep it out of the demo path.

---

### Phase 4 — First single agent (vertical slice)
**Goal:** one working `analyst` agent that answers a plain-English question using the MCP tools. This
is the smallest end-to-end slice; prove it before multiplying agents.

Steps:
1. `finsight/tools/mcp_bigquery.py`: use `toolbox-core` `ToolboxSyncClient` to `load_toolset()` and
   expose it to ADK.
2. `finsight/agents/analyst.py`: an ADK `Agent` (model = worker) with the toolset and an instruction
   to answer sales/revenue questions by choosing the right tool and summarizing results.
3. `finsight/agent.py`: temporarily set `root_agent = analyst` so `adk run` / `adk web` works.
4. Test: `adk web finsight` (or `adk run finsight`), ask "What were total sales last month by
   category?" and confirm a grounded answer.

**✅ Checkpoint:** the agent returns a correct, data-grounded answer via the MCP tool (not
hallucinated). Commit: `feat: analyst agent vertical slice`.

---

### Phase 5 — Full multi-agent workflow
**Goal:** the real architecture — orchestrator + planner + analyst + forecaster + investigator +
reporter — wired as an ADK graph.

Steps:
1. Implement each agent module in `finsight/agents/` with a tight, single-responsibility instruction:
   - **planner:** turn the question into an ordered plan (which tools, which periods).
   - **analyst:** execute data pulls (existing).
   - **forecaster:** call BigQuery `AI.FORECAST` for expected values; compute expected-vs-actual delta.
     (Add a `forecast_*` tool to `tools.yaml` or a custom function-tool.)
   - **investigator:** given the delta, break it down by dimension (category/region/time) to name the
     likely driver.
   - **reporter:** synthesize a structured brief (summary, evidence, root cause, recommendation).
2. **orchestrator:** compose them using an ADK **`Workflow`** (graph) — sequential where order
   matters (plan → pull → forecast → investigate → report), with the ability to loop back if the
   verifier (Phase 7) rejects. Manage shared state so agents pass structured data, not prose.
3. Set `root_agent = orchestrator` in `finsight/agent.py`.

**✅ Checkpoint:** end-to-end run on "Why did revenue change vs the prior period?" produces a
structured report citing real figures from BigQuery. Commit: `feat: multi-agent workflow`.

---

### Phase 6 — Guardrails & security
**Goal:** demonstrable safety controls (a required course concept, and a strong resume signal).

Steps:
1. `guardrails/sql_readonly.py`: a callback/plugin that inspects any SQL before execution and blocks
   anything that isn't a single `SELECT` (no `INSERT/UPDATE/DELETE/DROP/CREATE/MERGE`, no multiple
   statements). Wire it as an ADK before-tool callback.
2. `guardrails/pii_redaction.py`: redact obvious PII (emails, names) from tool outputs before they
   reach the model/report where not needed.
3. `guardrails/injection_guard.py`: heuristic scan of retrieved text / user input for injection
   patterns ("ignore previous instructions", tool-name spoofing). Log and neutralize.
4. Add **human-in-the-loop**: before the report proposes any "action" (e.g., a change
   recommendation), require a confirmation step (ADK HITL pattern).

**✅ Checkpoint:** `tests/test_guardrails.py` proves a malicious SQL string is blocked and a PII field
is redacted. Commit: `feat: security guardrails`.

---

### Phase 7 — Verifier agent (the reliability lever)
**Goal:** a critic agent that checks the report before it's shown; this is also the variable in the
research ablation.

Steps:
1. `agents/verifier.py` (model = verifier / `gemini-2.5-pro`): given the draft report + the evidence
   pulled, score **groundedness** (is every claim supported by retrieved data?), **sufficiency** (was
   there enough context?), and **policy** (read-only respected, no PII leak). Output a structured
   pass/fail + reasons.
2. In the orchestrator graph, route: verifier **fail** → loop back to planner/analyst with the
   critique (bounded retries); **pass** → reporter finalizes.

**✅ Checkpoint:** injecting a deliberately unsupported claim causes the verifier to fail and trigger
a retry. Commit: `feat: verifier agent + retry loop`.

---

### Phase 8 — Skills, memory, and observability
**Goal:** the remaining course concepts.

Steps:
1. **Skills:** write the three `SKILL.md` playbooks (`rightsizing`, `commitments`, `anomaly_triage`)
   using progressive disclosure (short metadata + detailed instructions + resources). Load them via
   ADK's skill mechanism so agents pull the relevant playbook on demand.
2. **Memory:** configure session + long-term memory in `memory/session.py` so the app remembers org
   context (e.g., category→owner map) and prior investigations across runs.
3. **Observability:** enable ADK's OpenTelemetry export to **Cloud Trace**; add the BigQuery
   analytics logging plugin (or a simple structured logger) so every agent event/tool call is
   recorded with latency + token counts.

**✅ Checkpoint:** a run produces a trace viewable in Cloud Trace; the agent cites a playbook rule;
a second run recalls context from the first. Commit: `feat: skills, memory, observability`.

---

### Phase 9 — ⭐ Evaluation harness + benchmark + ablation (DO NOT SKIP)
**Goal:** the single most resume-differentiating deliverable. This is what turns "a demo" into
"an evaluated system."

Steps:
1. `eval/benchmark/finops_tasks.jsonl`: author **30–50 tasks**. Each row:
   `{"id", "question", "ground_truth_root_cause", "expected_answer_keypoints", "dimension"}`.
   Cover clean cases, ambiguous cases, and traps (questions with insufficient data → correct answer is
   "insufficient evidence").
2. `eval/llm_judge.py`: rubric-based LLM-as-judge (score correctness, groundedness, completeness 1–5).
3. `eval/mast_classifier.py`: given a failed trajectory, classify the failure into MAST categories
   (specification/design, inter-agent misalignment, verification). Cite the MAST taxonomy in comments.
4. `eval/run_eval.py`: run the full agent over the benchmark, log task success + trajectory + latency,
   write a metrics table to `eval/results/`.
5. `eval/ablation.py`: run three configurations — **(a) single agent, (b) multi-agent without
   verifier, (c) multi-agent with verifier** — over the same benchmark; produce a comparison table and
   a MAST failure-mode breakdown chart. The headline result to look for: *does the verifier reduce
   verification/specification failures and raise root-cause accuracy?*

**✅ Checkpoint:** `python eval/run_eval.py` produces a metrics table; `python eval/ablation.py`
produces a comparison across the 3 configs + a chart. Commit: `feat: eval harness, benchmark, ablation`.

> If the schedule slips, this phase takes priority over Phase 8 extras and over adding more agents.

---

### Phase 10 — Deploy, CI, and submission packaging
**Goal:** production polish + everything the Kaggle writeup needs.

Steps:
1. `Dockerfile` + `.dockerignore` for the ADK app; `deployment/deploy_cloud_run.sh` wrapping
   `gcloud run deploy`. **🧑 HUMAN STEP:** run the deploy (needs your gcloud auth/billing).
2. `.github/workflows/ci.yml`: run `ruff` + `pytest` on push.
3. Finalize `README.md`: pitch, architecture diagram, quickstart, **results table from Phase 9**,
   concept-to-feature mapping table, and screenshots (Cloud Trace, eval chart).
4. Prepare the **Kaggle writeup** and **demo video script** (see section 4).

**✅ Checkpoint:** the Cloud Run URL responds; CI is green; README shows real results. Commit:
`docs: submission-ready readme + deploy`.

---

## 4. Submission assets (what wins points)

### Kaggle writeup — structure
1. **Problem & business value** (2–3 sentences; cite the ~29% cloud-waste stat / FinOps context).
2. **What it does** — one concrete walkthrough (a real question → the traced investigation → report).
3. **Architecture** — the diagram + the multi-agent graph explanation.
4. **Course concepts demonstrated** — a table mapping each of the 6–7 concepts to where it lives in
   the code.
5. **Evaluation & results** — the benchmark, the ablation table, the MAST breakdown. **Lead with
   numbers.**
6. **What's novel** — the evaluated verifier ablation on a purpose-built FinOps benchmark.
7. **Links** — GitHub repo, Cloud Run demo, video.

### Demo video (aim ~3 minutes)
- 0:00–0:20 problem hook (cloud waste).
- 0:20–1:20 **live** investigation: ask a question, show agents handing off, show the final cited
  report.
- 1:20–2:00 show the **Cloud Trace** trajectory and the **guardrail** blocking a bad SQL / injection.
- 2:00–2:45 show the **eval dashboard**: benchmark score + verifier ablation + MAST chart.
- 2:45–3:00 recap concepts covered + business impact.

### Resume bullets (fill in with YOUR measured numbers after Phase 9)
- **Data Scientist:** "Built a multi-agent FinOps analyst (Gemini + Google ADK 2.0) with a TimesFM
  forecasting agent and a 40-task evaluation benchmark; a verifier-agent ablation improved root-cause
  accuracy from __%→__% and cut unsupported claims __%→__%."
- **Data Analyst:** "Shipped a natural-language-to-SQL multi-agent analytics co-pilot over BigQuery
  (MCP Toolbox) that turns business questions into traced, citation-backed investigations."
- **AI Engineer:** "Designed and deployed a 6-agent ADK graph to Cloud Run with MCP tool servers,
  OpenTelemetry/Cloud Trace observability, read-only-SQL + prompt-injection guardrails, and
  human-in-the-loop approval."
- **ML Engineer:** "Productionized a multi-agent LLM system with CI/CD, trajectory-level evaluation,
  LLM-as-judge regression tests, and autoscaling Cloud Run deployment."
- **Research Scientist:** "Created a reproducible enterprise agent-evaluation benchmark and applied
  the MAST failure taxonomy to quantify how a verifier agent reduces specification/verification
  failures; open-sourced the harness and dataset."

---

## 5. Risk register & fallbacks
- **ADK 2.0 API drift vs this plan:** trust the installed package's docstrings; note deviations in
  `PROGRESS.md`.
- **MCP Toolbox binary/network issues:** if the toolbox is troublesome, fall back to ADK's built-in
  first-party BigQuery toolset for the demo, but keep `tools.yaml` in the repo to show the MCP concept.
- **`AI.FORECAST` availability/quota:** if forecasting is flaky, compute expected values with a simple
  period-over-period / moving-average baseline in a custom tool; keep the "forecaster agent" role.
- **Time crunch:** minimum viable winning scope = Phases 0–7 + Phase 9 (evals). Phase 8 extras and the
  synthetic-billing dataset are stretch.
- **Dataset realism:** the ecommerce dataset is fine; if you want true "FinOps," generate a small
  synthetic FOCUS-format billing table in BigQuery as a stretch and re-point `tools.yaml`.

---

## 6. Definition of done
- [ ] `adk run finsight` executes a full multi-agent investigation end-to-end.
- [ ] Read-only SQL + PII + injection guardrails proven by tests.
- [ ] Verifier agent loop working.
- [ ] Skills, memory, and Cloud Trace observability demonstrated.
- [ ] Benchmark (30–50 tasks) + eval harness + 3-way ablation with a results table and MAST chart.
- [ ] Deployed to Cloud Run; CI green.
- [ ] README with architecture + real results; Kaggle writeup + video done; repo public.
- [ ] Deadline confirmed and met.
