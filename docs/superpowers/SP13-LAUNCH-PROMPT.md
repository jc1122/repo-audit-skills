# SP13 Launch Prompt — combined SP12+SP13 continuation, Opus-driven — paste as the orchestrator's goal

This run is launched and run by **Claude Opus 4.8** (orchestrator) with
concurrent **Opus native subagents** and/or **opencode** workers. It CONTINUES
from SP12's final main (no ceremonial relaunch) and layers the runtime
self-improvement work on top of the inherited SP12 residue.

Paste the block below into a fresh Claude Opus 4.8 session (Claude Code)
started inside `/home/jakub/projects/repo-audit-skills`, running unattended with
permissions pre-authorized. It is a launch key only: all detail lives in the
plan, which the orchestrator must read in full. Launch only once SP12 has
written its final summary and repo-A/B/P mains have settled (no other writer).

---

```
You are the ORCHESTRATOR (Claude Opus 4.8, UNATTENDED, permissions
pre-authorized) for SP13, the COMBINED continuation of SP12 + the runtime
self-improvement loop of the repo-audit skill family, in
/home/jakub/projects/repo-audit-skills.

SINGLE AUTHORITY — read IN FULL before acting:
docs/superpowers/plans/2026-06-13-sp13-runtime-self-improvement-loop.md
Contracts L-0..L-10, packages X0-X5, rules R1-R7, DoD, terminals are FROZEN
there; where this prompt and the plan differ, the plan wins.

ENTRY (continuation, not relaunch): SP12 has shipped its enablement (gate
speed, exec-audit + growth-audit leaves, parallel wave) and burned down under a
closed universe. Re-verify the current repo-A/B/P mains and the inherited open
residue from the SP12 ledger tail (last recorded ~repo-A 260, repo-B 22,
repo-P 27 = 309 rows — ledgers are truth, re-read them). Confirm all three
mains are clean and CI-green and no SP12 worker is still writing. Bootstrap
probe green. You inherit the SP12 residue as backlog and EXPAND it with the
meta-findings the X1 harness surfaces, then RE-FREEZE at X3.

YOUR HANDS ARE WORKERS (L-3): you NEVER edit or read source. You dispatch,
read evidence artifacts, re-run gates yourself, and merge. Conserve your
context: subagents return SUMMARIES; you read status.json + gate tails (<=40
lines) + findings/KPI JSON, never worker transcripts or source bodies. About
to read source -> dispatch a worker instead. A worker's green is NEVER
evidence — you re-run every gate and read real output.

WORKER ROUTES (L-4/L-7, run CONCURRENTLY for speed):
- PRIMARY = native Opus subagents via the Agent tool, run_in_background=true,
  isolation="worktree" (or an explicit /tmp/sp13/<repo>-<iter>-<slug> git
  worktree), <=4 concurrent, on disjoint file sets, file-backed packets.
- ALTERNATIVE = opencode-worker-bridge concurrent workers (same file-backed
  L-7 packets) when you want more parallelism than your own subagent budget.
- One writer per repo (per-repo worktree); repos visited concurrently; CI
  watches always overlap other work. Infra failure on one route -> switch the
  affected packet to the other route, one-way, logged. A gate-failing CHANGE
  is a normal discard/retry, NOT a route switch.

THE POINT: the loop improves its own PROCESS, not just its source. X0 lands
FIRST; everything proves itself through it.
- X0 TELEMETRY+MEMORY (keystone): mine_iteration_kpis.py DERIVES rows/hour,
  repair-rate, phase durations, CI wait from git timestamps + run-dir mtimes +
  baseline JSONs + CI API (mined, never typed — R5). Two-tier lessons.jsonl:
  enter `candidate`, promote to `binding` only with evidence it prevented a
  repeat; synthesizer injects scope-matched binding lessons (cap 5) per packet
  (L-7); a lesson firing >=3x MUST escalate prose->tooling (R7).
- X1 SELF-APPLICATION: instruction-lint (every command quoted in a SKILL.md
  exists + answers --help; required sections present) deterministic gate;
  budgeted advisory behavioral evals (pinned model); a checklist dogfooding ONE
  not-yet-applied family skill on the family each iteration — FIRST
  test-redundancy-triage on repo-A's 220-test triage suite (the gate wall-clock
  floor; DELETE rows are speed batches, tests aren't findings).
- X2 ADAPTIVE CONTROL: allocate_batches.py = every ACTIVE repo >=1 batch
  (defeats SP11 starvation) + surplus to best trailing rows/hour (L-5a, logged);
  amendment-proposals/NNN.md surfaces a contract-blocked improvement (max 3/run)
  for async operator review, never self-applied (L-8).

SEQUENCE: X0 ship+reinstall; X1 || X2; X3 ship all + expanded wave on A/B/P +
triage meta-findings fixed-first + RE-FREEZE (universe closed, L-1; new classes
-> SP14-CANDIDATES.md).

LOOP (post-freeze, L-1 guarantees termination; hard cap 12): per iteration: C-0
wave (concurrent) -> allocator (log rationale) -> self-application target ->
<=6 single-signal batches/repo via the lesson-injecting synthesizer, dispatched
to concurrent workers -> you re-verify, ratchet shrink-only -> on any worker
repair append/increment a lesson, at fires>=3 spend a batch escalating it to
tooling -> STRICT SHRINK: two zero-shrink iterations -> repo TERMINAL
(verification visits only) -> L-6 ship per changed repo (release+reinstall only
on leaf-behavior change) with allowance expiry each release -> ledger append
WITH the mined KPI row verbatim.

R6 (never violate): post-freeze process batches touch orchestration/tooling/
instructions ONLY, never leaf finding logic. Telemetry/timing artifacts are
NEVER in convergence comparison (R4).

FINAL: X5 allowlist purge -> reinstall/readback -> report headlined by the KPI
trend across iterations (the loop's learning curve) -> repo-A next-minor.

BINDING LESSONS: seed lessons.jsonl with the SP9-SP12 binding lessons listed in
the plan (fresh-clone before push; grep gate JSON never trust exit codes;
line-pinned duplication rows; byte-identical vendored health_common; --rev
anchor; `npm ci` in fresh worktrees; changelog date = commit date).

LEDGER: docs/self-audit/2026-06-sp13-runtime-self-improvement-loop.md per L-10,
once per iteration — standard rows PLUS the mined KPI row verbatim, lessons
added/promoted/escalated, allocation rationale, and self-application result.
```

---

## Run at a glance

```
Continue:  from SP12 final main, inheriting ~309 open rows (re-verify)
Iter 1:    X0 telemetry+memory (KPI miner + two-tier lessons) -> ship+reinstall
Iter 1-2:  X1 instruction-lint + evals + self-application || X2 allocator + amendment
           -> X3 ship all + expanded wave + RE-FREEZE (universe closed)
Iter 3..N: C-0 -> allocate (>=1/repo + best-yield) -> self-apply one skill ->
           lesson-injected batches to <=4 concurrent Opus/opencode workers ->
           strict shrink or TERMINAL -> ship (lesson fires 3x -> prose->tooling)
           (hard cap: 12)
Final:     X5 purge -> reinstall/readback -> report (headline: KPI learning curve)
Terminal:  DONE (all baselines []) or BLOCKED (residue documented) — both valid
```

## Operator notes

- **Models:** orchestrator = Claude Opus 4.8; workers = Opus native subagents
  (parallel, background, worktree-isolated) and/or opencode concurrent workers.
  This replaces SP11/SP12's Codex gpt-5.5 orchestrator + opencode-DeepSeek
  workers. The file-backed evidence discipline is unchanged.
- **Concurrency is the speed lever:** dispatch up to 4 disjoint worker packets
  at once across repos; never busy-wait on CI — overlap it with the next
  packet. The orchestrator stays small by reading artifacts, not transcripts.
- **Pre-launch checklist (same as SP11->SP12):** SP12 summary written; all
  three mains clean + CI-green; no live SP12 worker; `/tmp/sp12` + stale
  worktrees pruned; bridge smoke if using the opencode route; these SP13 docs
  committed.
