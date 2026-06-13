# SP14 Master Launch Prompt — build the engine, then remediate to convergence

**To launch:** start a fresh **Claude Opus 4.8** session inside
`/home/jakub/projects/repo-audit-skills`, approvals disabled (unattended), and paste the
**short launch key** below as the goal. It sends the orchestrator to read this file (the
full protocol underneath the key), the plan, and the spec, then execute both phases. The
detailed protocol lives in this same file under "Full goal & run protocol" so the paste
stays tiny.

## Short launch key (paste this — ~1.5k chars)

```
You are the ORCHESTRATOR (Claude Opus 4.8, UNATTENDED, approvals disabled) for SP14 in
/home/jakub/projects/repo-audit-skills. Approvals are off; run to a terminal without check-ins.

BEFORE acting, READ IN FULL and then follow as binding instructions:
  1) docs/superpowers/SP14-LAUNCH-PROMPT.md  (this key's "Full goal & run protocol" section)
  2) docs/superpowers/plans/2026-06-13-sp14-massively-parallel-redundancy-remediation.md
  3) docs/superpowers/specs/2026-06-13-sp14-massively-parallel-redundancy-remediation-design.md
The PLAN is the single authority; where anything conflicts, the plan wins.

GOAL (two phases, one session): PHASE A — build + ship the MPRR engine (plan Part I,
Tasks 1-10) via superpowers:subagent-driven-development (one worker per task, strict TDD),
then gates + CI green, release + reinstall into ~/.claude/skills -> ~/.agents/skills.
PHASE B — run the redundancy-remediation loop (plan Part II) until CONVERGENCE: a full
re-audit finds NO new redundancy issue to resolve (every finding remediated, documented-
residue, or deferred-hard). Strict-shrink-or-strike; HARD CAP 12 iterations. DONE when all
active repos converge + DoD met + CI green; else BLOCKED with a complete ledger.

NON-NEGOTIABLE (full detail in file #1): you are HANDS-OFF — never edit/read source
yourself; all edits run in worker sessions in git worktrees; a worker's "green" is never
evidence (re-run every gate yourself). Merges are file-disjoint and MUST be conflict-free
— a merge conflict is a HARD STOP, not a manual resolve. Enforce the 3-tier gate ladder.
KPIs are mined, never typed. Never suppress a real finding or game a gate. Append the
ledger docs/self-audit/2026-06-sp14-mprr-loop.md every iteration.
```

---

## Full goal & run protocol (the key points here — read before acting)

**Entry (re-verify; ledgers are truth, not these numbers):** SP13 is terminal — repo-A
`96007fd`/v0.6.0, repo-B `8f27083`, repo-P `ac58303`. The three mains are clean + CI-green
with no live worker; bootstrap probe green. Repos: repo-A `~/projects/repo-audit-skills`,
repo-B `~/projects/repo-audit-refactor-optimize`, repo-P `~/projects/perf-benchmark-skill`;
installed root `~/.claude/skills` → `~/.agents/skills`.

**Your hands are workers (L-3):** you NEVER edit or read source files. Every edit happens
in a worker session inside a git worktree (`/tmp/sp14/<repo>-<iter>-<slug>`). PRIMARY route
= native Opus subagents (Agent tool, `run_in_background=true`, `isolation="worktree"`);
ALTERNATIVE = opencode-worker-bridge; an infra failure switches that one packet to the
other route (one-way, logged). You read ONLY `status.json` + gate tails (≤40 lines) +
findings/KPI JSON; you re-run every gate yourself; a worker's self-reported "green" is
NEVER evidence. About to open a source file → dispatch a worker instead. Keep ≤4 worker
sessions globally during Phase A; in Phase B the engine's ceiling N governs concurrency.

### Phase A — build + ship the engine (plan Part I, Tasks 1-10)
Use `superpowers:subagent-driven-development`: one fresh worker per plan task, strict TDD
(write failing test → see it fail → minimal code → see it pass → commit), two-stage review
between tasks. Engine modules land in repo-B as `scripts/mprr_*.py` with mirror
`tests/test_mprr_*.py`, following the repo's flat layout + `sys.path` test idiom. Gate after
every task: the task's tests pass. Gate after Task 10:
- repo-B `pytest -q` fully green; ruff lint + format + type gates green;
- fresh-clone simulation green; push; CI watch green (one bounded fix-forward on red);
- release + reinstall the changed repo-B skill into `~/.claude/skills` → `~/.agents/skills`;
- readback + bootstrap probe green.

Do NOT begin Phase B until Phase A is shipped, reinstalled, and probe-green. Record Phase A
completion + ship evidence in the ledger.

### Phase B — remediate to convergence (plan Part II)
THE ENGINE IS THE BRAIN; YOU ARE THE PUMP. Active targets = the family repos PLUS one
foreign Python repo (pick a repo under `~/projects` that is NOT repo-A/B/P and has a green
test suite; record the choice). Per iteration, per ACTIVE repo:
1. Run the redundancy lanes (`duplication-audit`, `dead-code-audit`, `test-redundancy-triage`)
   → `findings.json` + `triage.json`.
2. `python scripts/mprr_run.py reaudit --findings findings.json --triage triage.json` →
   residual count (exit code 0 == this repo CONVERGED for this iteration).
3. Else SATURATE: `mprr_run.py plan --run-dir RD --findings ... --triage ... --ceiling N`
   emits file-DISJOINT packets (clean merges by construction). Dispatch them as workers. As
   EACH worker returns, immediately `mprr_run.py integrate --run-dir RD --packet-id P
   --evidence E.json --diff-files <worker diff paths> --repo R --branch B`, then call `plan`
   again to refill freed slots. Keep the pool full at ceiling N.
4. `integrate` enforces the GATE LADDER and asserts every merge is conflict-free:
   - **mechanical** (dead-code / unused-imports): tests green + lane re-audit shows it gone;
   - **refactor** (duplicate EXTRACT/MERGE): scoped mutation ≥ 0.80 + tests + re-audit gone;
   - **test_removal** (redundant-test DELETE/MERGE): coverage parity + mutation parity at
     HIGH confidence ONLY (else deferred-hard, never merged).
   A reported merge conflict = `InvariantViolation` = HARD STOP + escalate (partitioner/
   worker bug), never a manual resolve. A worker diff touching an undeclared file = discard.
5. On pool drain: local full gate + fresh-clone sim → ONE batched push → CI watch; reinstall
   if leaf behavior changed; mine KPIs (`mprr_events` → `mine_mprr_kpis`): merge-conflict-rate
   MUST be 0.

Start N=8; raise N only while mined `pool_utilization` stays high AND merge-conflict-rate
stays 0. The SP13 X1.3 **142-MERGE triage backlog** MUST be acted on (merged-or-deferred-hard)
with coverage+mutation-parity evidence.

### Convergence — the campaign goal
Keep running until it holds for ALL active repos: a full re-audit finds NO new redundancy
issue to resolve — every finding is remediated, or documented residue (SP12-justified
intrinsic clone / module-MI CLI idiom), or deferred-hard (a fix that cannot reach its gate).
L-1: each iteration every ACTIVE repo must shrink its residual count by ≥1 or take a strike;
two consecutive strikes → that repo TERMINAL with documented residue (verification visits
only). HARD CAP = 12 iterations after Phase A. Never suppress a real finding to force
convergence; never game the gate ladder.

### Terminals (L-9)
DONE = all active repos converged/terminal, every DoD item met, repo-B released+reinstalled,
CI green. BLOCKED = cap hit / two strikes / second CI red on a repo / an invariant violation
— with a complete ledger. Both are honest; report which.

### Binding lessons (carried)
Fresh-clone sim before ANY push; never trust a piped exit code — read the gate JSON; the
disjoint-file invariant is load-bearing, so a nonzero merge-conflict-rate is a STOP not a
retry; KPIs are MINED from artifacts, never typed (R5); the engine never edits leaf
finding-emission logic (R6); growth allowances are reasoned + release-expiring, dependency
growth never allowed (L-2).

### Ledger
`docs/self-audit/2026-06-sp14-mprr-loop.md`, appended once per Phase-A task batch and once
per Phase-B iteration: installed versions; Phase A ship evidence; per iteration residual
counts before/after per repo, packets dispatched/merged/discarded/deferred-hard, worker run
dirs, the MINED MPRR KPI row (pool utilization, peak/mean concurrency, merge-conflict-rate=0,
rows/hr), ship evidence, growth-allowance table, and TERMINAL declarations. Finish only when
the DoD's falsifiable checks pass (DONE) or a BLOCKED terminal is reached.

---

## Operator notes (outside the goal)
- **N (pool ceiling)** starts at 8; the orchestrator raises it from the mined
  `pool_utilization` KPI. Edit the `--ceiling` value to change the start.
- **Foreign repo (DoD #4):** the protocol tells the orchestrator to pick one under
  `~/projects`; pin a specific repo here if you prefer.
- The short launch key is the only thing you paste; everything else is read from this file
  and the plan/spec, so the launch stays small.
