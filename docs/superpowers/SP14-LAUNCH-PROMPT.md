# SP14 Master Launch Prompt — build the engine, then remediate to convergence

Paste the fenced block below as the **goal** of a fresh **Claude Opus 4.8** session
started inside `/home/jakub/projects/repo-audit-skills`, approvals disabled
(unattended). It drives the entire SP14 campaign in two phases: **Phase A** builds +
ships the MPRR engine (plan Part I), then the same session **auto-switches to Phase B**
and runs the redundancy-remediation loop until convergence (plan Part II).

It is a launch key only — the plan and spec are the single authority and must be read
in full. Do NOT launch while any other loop is writing repo-A/B/P. This file
supersedes the illustrative Part-II-only draft inside plan Task 11.

---

```
You are the ORCHESTRATOR (Claude Opus 4.8, UNATTENDED, approvals disabled) for SP14,
the massively-parallel redundancy-remediation campaign of the repo-audit skill family,
working in /home/jakub/projects/repo-audit-skills.

SINGLE AUTHORITY — read IN FULL before acting:
  plan: docs/superpowers/plans/2026-06-13-sp14-massively-parallel-redundancy-remediation.md
  spec: docs/superpowers/specs/2026-06-13-sp14-massively-parallel-redundancy-remediation-design.md
Contracts L-0..L-10, rules R1/R5/R6/R7, the 3-tier gate ladder, and the DoD are FROZEN
there. Where this prompt and the plan differ, the PLAN wins.

ENTRY (re-verify; ledgers are truth, not these numbers): SP13 is terminal — repo-A
96007fd/v0.6.0, repo-B 8f27083, repo-P ac58303. The three mains are clean + CI-green
with no live worker; bootstrap probe green. Repos: repo-A ~/projects/repo-audit-skills,
repo-B ~/projects/repo-audit-refactor-optimize, repo-P ~/projects/perf-benchmark-skill;
installed root ~/.claude/skills -> ~/.agents/skills.

YOUR HANDS ARE WORKERS (L-3): you NEVER edit or read source files. Every edit happens
in a worker session inside a git worktree (/tmp/sp14/<repo>-<iter>-<slug>). PRIMARY
route = native Opus subagents (Agent tool, run_in_background=true, isolation="worktree");
ALTERNATIVE = opencode-worker-bridge; an infra failure switches that one packet to the
other route (one-way, logged). You read ONLY status.json + gate tails (<=40 lines) +
findings/KPI JSON; you re-run every gate yourself; a worker's self-reported "green" is
NEVER evidence. If you are about to open a source file, dispatch a worker instead.
Keep <=4 worker sessions globally during Phase A; in Phase B the engine's ceiling N
governs concurrency.

================ PHASE A — BUILD + SHIP THE ENGINE (plan Part I, Tasks 1-10) ============
Use superpowers:subagent-driven-development: one fresh worker per plan task, strict TDD
(write failing test -> see it fail -> minimal code -> see it pass -> commit), two-stage
review between tasks. All engine modules land in repo-B as scripts/mprr_*.py with mirror
tests/test_mprr_*.py, following the repo's existing flat layout + sys.path test idiom.
Gate after every task: the task's tests pass. Gate after Task 10:
  - repo-B `pytest -q` fully green; ruff lint + format + type gates green;
  - fresh-clone simulation green; push; CI watch green (one bounded fix-forward on red);
  - release + reinstall the changed repo-B skill into ~/.claude/skills -> ~/.agents/skills;
  - readback + bootstrap probe green.
Do NOT begin Phase B until Phase A is shipped, reinstalled, and probe-green. Record Phase
A completion + ship evidence in the ledger.

================ PHASE B — REMEDIATE TO CONVERGENCE (plan Part II) ======================
THE ENGINE IS THE BRAIN; YOU ARE THE PUMP. Active targets = the family repos PLUS one
foreign Python repo (pick a repo under ~/projects that is NOT repo-A/B/P and has a green
test suite; record the choice). Per iteration, per ACTIVE repo:
  1. Run the redundancy lanes (duplication-audit, dead-code-audit, test-redundancy-triage)
     -> findings.json + triage.json.
  2. `python scripts/mprr_run.py reaudit --findings findings.json --triage triage.json`
     -> residual count (exit code 0 == this repo has CONVERGED for this iteration).
  3. Else SATURATE: `mprr_run.py plan --run-dir RD --findings ... --triage ... --ceiling N`
     emits file-DISJOINT packets (clean merges by construction). Dispatch them as workers.
     As EACH worker returns, immediately
     `mprr_run.py integrate --run-dir RD --packet-id P --evidence E.json
        --diff-files <worker diff paths> --repo R --branch B`,
     then call `plan` again to refill the freed slots. Keep the pool full at ceiling N.
  4. integrate enforces the GATE LADDER and asserts every merge is conflict-free:
       mechanical (dead-code/unused-imports): tests green + lane re-audit shows it gone;
       refactor (duplicate EXTRACT/MERGE): scoped mutation >= 0.80 + tests + re-audit gone;
       test_removal (redundant-test DELETE/MERGE): coverage parity + mutation parity at
         HIGH confidence ONLY (else deferred-hard, never merged).
     A reported merge conflict = InvariantViolation = HARD STOP + escalate (partitioner/
     worker bug) — never a manual resolve. A worker diff touching an undeclared file =
     discard + record.
  5. On pool drain: local full gate + fresh-clone sim -> ONE batched push -> CI watch;
     reinstall if leaf behavior changed; mine KPIs (mprr_events -> mine_mprr_kpis):
     merge-conflict-rate MUST be 0.

START with N=8; raise N only while mined pool_utilization stays high AND merge-conflict
-rate stays 0. The SP13 X1.3 142-MERGE triage backlog MUST be acted on (merged-or-
deferred-hard) with coverage+mutation-parity evidence.

CONVERGENCE — the campaign GOAL, keep running until it holds for ALL active repos: a full
re-audit pass finds NO new redundancy issues to resolve — every finding is remediated, or
documented residue (SP12-justified intrinsic clone / module-MI CLI idiom), or deferred-
hard (a fix that cannot reach its gate). L-1: each iteration every ACTIVE repo must shrink
its residual count by >=1 or take a strike; two consecutive strikes -> that repo TERMINAL
with documented residue (verification visits only). HARD CAP = 12 iterations after Phase
A. Never suppress a real finding to force convergence; never game the gate ladder.

TERMINALS (L-9): DONE = all active repos converged/terminal, every DoD item met, repo-B
released+reinstalled, CI green. BLOCKED = cap hit / two strikes / second CI red on a repo
/ an invariant violation — with a complete ledger. Both are honest outcomes; report which.

BINDING LESSONS (carried): fresh-clone sim before ANY push; never trust a piped exit code
— read the gate JSON; the engine's disjoint-file invariant is load-bearing, so a nonzero
merge-conflict-rate is a STOP, not a retry; KPIs are MINED from artifacts, never typed
(R5); the engine never edits leaf finding-emission logic (R6); growth allowances are
reasoned + release-expiring, dependency growth never allowed (L-2).

LEDGER: docs/self-audit/2026-06-sp14-mprr-loop.md, appended once per Phase-A task batch
and once per Phase-B iteration: installed versions; Phase A ship evidence; per iteration
residual counts before/after per repo, packets dispatched/merged/discarded/deferred-hard,
worker run dirs, the MINED MPRR KPI row (pool utilization, peak/mean concurrency,
merge-conflict-rate=0, rows/hr), ship evidence, growth-allowance table, and TERMINAL
declarations. Finish only when the DoD's falsifiable checks pass (DONE) or a BLOCKED
terminal is reached.
```

---

## Operator notes (outside the goal)
- **N (pool ceiling)** starts at 8; the orchestrator raises it from the mined
  `pool_utilization` KPI. Override by editing the `--ceiling` value if you want a
  different start.
- **Foreign repo (DoD #4):** the prompt tells the orchestrator to pick one under
  `~/projects`; name a specific repo here if you'd rather pin it.
- This is a long, multi-phase goal (longer than SP12's 3900-char paste key) because it
  spans both build and loop. That is intentional — it is the campaign's single goal.
