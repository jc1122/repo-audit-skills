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
pre-authorized) for SP13, the COMBINED SP12 continuation + runtime self-improvement loop of the
repo-audit skill family, in
/home/jakub/projects/repo-audit-skills.

SINGLE AUTHORITY (read IN FULL first):
docs/superpowers/plans/2026-06-13-sp13-runtime-self-improvement-loop.md
Contracts L-0..L-10, packages X0-X5, rules R1-R7, DoD, terminals FROZEN there;
plan wins on any conflict.

ENTRY (continuation, not relaunch): re-verify the mains + residue from the SP12
ledger tail (terminal record: repo-A 260, repo-B 13, repo-P 25 = 298 rows).
Confirm all three mains clean + CI-green, no SP12 worker writing, probe green.
Inherit the 298 rows as backlog, EXPAND with the meta-findings X1 surfaces, then
RE-FREEZE at X3.

YOUR HANDS ARE WORKERS (L-3): you NEVER edit or read source. Dispatch, re-run gates yourself, merge. Conserve context: subagents return SUMMARIES; read status.json + gate tails (<=40 lines) + findings/KPI JSON, never
transcripts or source. A worker's green is NEVER evidence — re-run every gate.

WORKER ROUTES (L-4/L-7, CONCURRENT): PRIMARY = native Opus subagents via the
Agent tool (run_in_background=true, isolation="worktree"), <=4 concurrent, disjoint files,
file-backed packets. ALTERNATIVE = opencode-worker-bridge workers (same packets). One writer per repo; repos
concurrent; CI watches overlap other work. Infra failure -> switch that packet
to the other route (one-way, logged); a gate-failing CHANGE is a discard/retry,
not a route switch.

THE POINT: the loop improves its own PROCESS, not just source. X0 FIRST.
- X0 TELEMETRY+MEMORY (keystone): mine_iteration_kpis.py DERIVES rows/hour,
  repair-rate, phase durations, CI wait from git/run-dir/baseline/CI artifacts
  (mined, never typed — R5). Two-tier lessons.jsonl: enter `candidate`, promote
  to `binding` only with evidence it prevented a repeat; synthesizer injects
  scope-matched binding lessons (cap 5) per packet (L-7); a lesson firing >=3x
  MUST escalate prose->tooling (R7).
- X1 SELF-APPLICATION: instruction-lint (every command in a SKILL.md
  exists + answers --help; required sections present) as a gate; budgeted
  advisory behavioral evals; each iteration dogfoods ONE not-yet-applied family
  skill on the family — FIRST test-redundancy-triage on repo-A's 220-test triage
  suite (the gate wall-clock floor; DELETE rows are speed batches).
- X2 CONTROL: allocate_batches.py = every ACTIVE repo >=1 batch + surplus to
  best trailing rows/hour (L-5a, logged); amendment-proposals/NNN.md surfaces a
  contract-blocked improvement (max 3/run) for operator review, never
  self-applied (L-8).

SEQUENCE: X0 ship+reinstall; X1 || X2; X3 ship all + expanded wave on A/B/P +
triage meta-findings fixed-first + RE-FREEZE (universe closed, L-1; new classes
-> SP14-CANDIDATES.md).

LOOP (post-freeze, L-1 guarantees termination; cap 12): C-0 wave -> allocator
-> self-application target -> <=6 single-signal batches/repo via the
lesson-injecting synthesizer to concurrent workers -> re-verify, ratchet
shrink-only -> on a worker repair increment a lesson, at fires>=3 escalate it to
tooling -> STRICT SHRINK: two zero-shrink iterations -> repo TERMINAL -> L-6
ship per changed repo (release+reinstall only on leaf-behavior change),
allowance expiry each release -> ledger append WITH the mined KPI row.

R6: post-freeze process batches touch orchestration/instructions ONLY, never
leaf finding logic. Timing artifacts NEVER enter convergence comparison (R4).

FINAL: X5 purge -> reinstall/readback -> report headlined by the KPI trend ->
repo-A next-minor release.

BINDING LESSONS: seed lessons.jsonl with the plan's SP9-SP12 binding lessons.
LEDGER per L-10 (docs/self-audit/2026-06-sp13-...md), per iteration: standard
rows PLUS the mined KPI row, lessons added/promoted/escalated, allocation
rationale, self-application result.
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
