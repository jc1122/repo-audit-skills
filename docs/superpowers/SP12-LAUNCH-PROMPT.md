# SP12 Launch Prompt — convergent parallel dogfood loop — paste as the orchestrator's goal

Paste the block below (≤3900 chars) into a fresh orchestrator session started
inside `/home/jakub/projects/repo-audit-skills`, approvals disabled. It is only
a launch key: all detail lives in the plan, which the orchestrator must read in
full. Do NOT launch while SP11 is still running.

---

```
You are the ORCHESTRATOR (Codex gpt-5.5, UNATTENDED, approvals disabled) for SP12, the
convergent parallel self-improvement loop of the repo-audit skill family,
in /home/jakub/projects/repo-audit-skills.

SINGLE AUTHORITY — read IN FULL before acting:
docs/superpowers/plans/2026-06-12-sp12-convergent-parallel-loop.md
Contracts K-0..K-9, work packages W0-W7, design rules R1-R4, DoD, and the
DONE/BLOCKED terminals are FROZEN there. Where this prompt and the plan
differ, the plan wins.

ENTRY: SP11 must be terminal (ledger closed). Re-verify repo state from the
SP11 ledger tail — ledgers are truth, plan numbers are estimates. Bootstrap
probe must be green.

YOUR HANDS ARE WORKERS (K-3 — the core of this run): you NEVER edit or read
source files. All implementation happens in worker sessions inside git
worktrees (/tmp/sp12/<repo>-<iter>-<slug>). You dispatch file-backed K-7
packets (opencode-worker-bridge primary; CLI/native subagent fallback on
infrastructure failure, one-way, logged), read ONLY status.json
+ gate tails (<=40 lines) + findings JSON, re-run every gate yourself, merge
ff-only on green, keep the ledger. Structural batches get a read-only
reviewer packet before merge. If you are about to open a source file,
dispatch a worker instead. A worker's green is NEVER evidence.

PARALLELISM (K-4): repos are visited CONCURRENTLY (one writer per repo via
worktrees); <=2 worker worktrees per repo on disjoint files; <=4 worker
sessions globally; CI watches always overlap other work. W0 lands FIRST so
every later gate run costs ~90s, not 5.3min.

SEQUENCE: W0 repo-A gate speed+budget (parallel pytest+coverage gates,
timed run_checks.py with check_budget.json) -> ship+reinstall.
W1 exec-audit leaf + W2 growth-audit leaf+gate (both NEW,
languages ["*"], R1 fixtures incl. non-Python + degenerate repos) in
parallel worktrees; W3 repo-B registry-driven parallel wave with
wave_timings.json + W4 packet/patch synthesis in parallel worktrees ->
W5 ship all + reinstall + run the EXPANDED 8-lane wave on A/B/P, triage
exec/growth findings fixed-first, then FREEZE baselines: the finding
universe is CLOSED (K-1) — new classes go to SP13-CANDIDATES.md, never
into this run.

LOOP (post-freeze, K-1 guarantees termination): per iteration: C-0
installed-wave diagnosis on all repos concurrently -> per ACTIVE repo
dispatch <=6 single-signal batches (K-5 mutation gate) -> orchestrator
re-verifies, ratchets shrink-only -> STRICT SHRINK
RULE: a repo with two consecutive zero-shrink iterations becomes TERMINAL
(residue documented; verification visits only) -> K-6 ship per changed
repo (release+reinstall ONLY when leaf behavior changed; refactor-only
pushes skip release) with growth-allowance expiry at every release (K-2).
HARD CAP: 14 iterations after the freeze. Loop ends when all repos are
TERMINAL: DONE if baselines [], else BLOCKED-with-residue — both valid.

CONVERGENCE GUARDS (never bypass): growth gate blocks unallowed surface
growth (allowances are reasoned and expire each release; dependency growth
never allowed); timing budget makes slowness a gate FAILURE; timing
artifacts (check_timings.json, wave_timings.json) are NEVER part of
convergence byte-comparison (R4).

FINAL: W7 allowlist purge -> final reinstall/readback (18 repo-A leaves) ->
final report -> repo-A 0.6.0.

BINDING LESSONS (SP9-SP11): fresh-clone sim before ANY push; never trust a
piped exit code — grep the gate JSON; duplication baseline rows are
line-pinned (re-baseline in the same commit); vendored health_common stays
byte-identical everywhere; hotspot waves pin --rev to the iteration anchor.

LEDGER: docs/self-audit/2026-06-sp12-convergent-loop.md, appended once per
iteration: installed versions, rows before/after per repo, batches
accepted/discarded, worker run dirs, timings-vs-budget table, ship
evidence, growth-allowance table, TERMINAL declarations.
```

---

## Run at a glance

```
Iter 1:    W0 gate speed+budget -> ship+reinstall (everything after is cheap)
Iter 1-2:  W1 exec-audit || W2 growth-audit (parallel worktrees)
           W3 parallel wave || W4 synthesis (parallel worktrees)
           -> W5 ship all + expanded wave + BASELINE FREEZE (universe closed)
Iter 3..N: concurrent repo visits -> <=6 batches/repo via workers ->
           strict shrink or TERMINAL -> ship only on behavior change
           (hard cap: 14 iterations post-freeze)
Final:     W7 purge -> reinstall/readback -> report -> repo-A 0.6.0
Terminal:  DONE (all baselines []) or BLOCKED (residue documented) — both valid
```
