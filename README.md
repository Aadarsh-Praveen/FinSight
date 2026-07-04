# FinSight

A multi-agent FinOps analyst that turns a plain-language question about a revenue or spend change
into a cited, verified investigation — built on Google ADK 2.0, Gemini, and BigQuery via MCP
Toolbox.

## The headline result

The evaluation's most important finding is that **multi-agent decomposition is a task-dependent
tradeoff, not a uniform win**: it beats a single-agent baseline on well-structured analytical
questions, but loses on the aggregate and on adversarial robustness.

| task type | single_agent | multi_agent_no_verifier | multi_agent_verifier |
|---|---|---|---|
| clean attribution (n=12/config) | 83.3% ± 38.9% | **100.0% ± 0.0%** | 91.7% ± 28.9% |
| full aggregate (n=44-45/config) | **68.2%** | 64.4% | 62.2% |
| adversarial only (n=15/config) | **40.0%** | 33.3% | 26.7% |

The verifier agent also has a real, statistically-grounded blind spot — it catches reporter-level
fabrication (33%→67% on the task it's built for) but is blind to state corruption further upstream
in the pipeline (`3.3 incorrect_verification` on 17/45, 37.8%, of its trials in the MAST failure
taxonomy). Full results, methodology, and every number's source run: **[`FINDINGS.md`](FINDINGS.md)**.
Writeup prose: **[`KAGGLE_WRITEUP.md`](KAGGLE_WRITEUP.md)**.

## Architecture

```
                         ┌─────────────┐
   user question ──────▶ │   planner   │
                         └──────┬──────┘
                                │  InvestigationPlan
                                ▼
                    ┌────────────────────────────────┐
                    │   LoopAgent (max 3 iterations)  │
                    │                                  │
                    │  analyst → forecaster →          │
                    │  investigator → reporter →        │
                    │  verifier                         │
                    │       │                            │
                    │       └── fail: retry loop ────┐   │
                    │       └── pass: escalate ───────┼──▶│ exit
                    └────────────────────────────────┘
```

- **planner** — turns the question into a structured `InvestigationPlan`.
- **analyst** — pulls real period-over-period totals from BigQuery (`compare_period_over_period`,
  read-only, parameterized SQL via MCP Toolbox — no arbitrary query execution).
- **forecaster** — a deterministic trailing-average baseline (deliberately not
  BigQuery `AI.FORECAST`/TimesFM, for reproducibility in the eval harness — see
  `finsight/agents/forecaster.py`).
- **investigator** — breaks the change down by category, independently computing the driver and
  its share of the net change.
- **reporter** — writes the final `FinOpsReport`, every figure traceable to a tool call; any
  recommendation is held behind a human-in-the-loop confirmation.
- **verifier** — an independent groundedness check (`after_agent_callback`, not the `exit_loop`
  tool — that combination was found to silently break structured-output capture on the pass path)
  that can send the loop back to the reporter, up to 3 retries, before ever returning a report.

Every agent-to-agent hand-off is a pydantic `output_schema` (`finsight/agents/schemas.py`), not
free text. Guardrails (`finsight/guardrails/`) enforce read-only SQL, PII redaction, and a
tool-output injection guard as ADK callbacks, not just prompt instructions — and their actual
effectiveness is measured, not assumed, against 5 direct-injection adversarial benchmark tasks.

## Quickstart

Requires Python 3.11+, a GCP project with BigQuery + Vertex AI (or an AI Studio API key), and the
[MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox) binary.

```bash
# 1. Install dependencies
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env   # fill in GOOGLE_CLOUD_PROJECT, model IDs, etc.

# 3. Start the MCP Toolbox server (separate terminal, from mcp-toolbox/)
cd mcp-toolbox && ./toolbox --config tools.yaml   # serves on http://127.0.0.1:5000

# 4. Run an investigation
adk run finsight "Why did revenue increase from November 2019 to December 2019?"
# or the web UI:
adk web finsight
```

Run the fast test suite (guardrails + verifier unit tests, no live LLM calls):

```bash
pytest -q -m "not live"
```

Run the eval harness (requires live BigQuery + Gemini access):

```bash
python eval/ablation.py                          # the full ablation
python eval/ablation.py --task-ids=id1,id2,...    # a custom task subset
```

## Project status

Phases 0-9 are done (core multi-agent pipeline, guardrails, verifier, skills/memory/observability,
evaluation harness/benchmark/ablation). Phase 10 (Cloud Run deploy, CI) is in progress. See
`PROGRESS.md` for the full phase-by-phase build log and `BUILD_PLAN.md` for the original
implementation plan.
