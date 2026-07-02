"""Standalone subprocess worker: runs exactly one ablation trial and prints the result as JSON
on the last line of stdout.

Used by eval/ablation.py via subprocess.run(..., timeout=...) instead of a thread pool. Repeated
Runner.run() calls from a reused thread (even a single-worker ThreadPoolExecutor, fully serial)
were found to hang at scale across a long run (169/180 trials timed out) despite working fine in
short isolated tests -- most likely accumulated unclosed aiohttp sessions/connections across many
calls in the same process (recurring "Unclosed client session"/"Unclosed connector" warnings have
appeared throughout this project whenever many ADK/genai calls happen in one process). A fresh
subprocess per trial guarantees fully clean state -- new interpreter, new connections, no
accumulation possible -- at the cost of Python/import startup overhead per trial.
"""

from __future__ import annotations

import json
import sys

from eval.ablation import run_single_trial
from eval.run_eval import load_tasks


def main() -> None:
    config_name, task_id, trial_idx_str = sys.argv[1], sys.argv[2], sys.argv[3]
    trial_idx = int(trial_idx_str)

    tasks_by_id = {t["id"]: t for t in load_tasks()}
    task = tasks_by_id[task_id]

    stdin_payload = sys.stdin.read().strip()
    if stdin_payload:
        extra = json.loads(stdin_payload)
        if extra.get("_live_share_pct") is not None:
            task = dict(task)
            task["_live_share_pct"] = extra["_live_share_pct"]

    result = run_single_trial(config_name, task, trial_idx)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
