# SP13: Runtime Self-Improvement Loop (combined SP12+SP13 continuation, Opus-driven) — the loop learns from its own process

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
>
> **For the SP13 orchestrator:** this plan is the single authority. ONE **Claude Opus 4.8** orchestrator session runs UNATTENDED (permissions pre-authorized) and NEVER edits or reads source itself (inherits SP12 K-3: worker-only hands). It CONTINUES from SP12's final main — no ceremonial relaunch — inheriting the SP12 residue as backlog. All implementation happens in **concurrent worker sessions** (native Opus subagents via the Agent tool with `run_in_background` + worktree isolation, and/or opencode-worker-bridge workers) inside git worktrees. The orchestrator dispatches packets, reads evidence artifacts (status.json, gate tails, findings/KPI JSON — never transcripts or source), re-runs gates itself, merges green work, keeps the ledger. A worker's green is NEVER evidence.

**Goal:** make the loop improve its own *process*, not only its *source* — by mining its own runtime telemetry, remembering and auto-escalating its own lessons, testing its own instruction layer (SKILL.md/playbooks), reallocating effort by measured yield, and proposing its own bounded plan amendments — then burning down the SP12 residue plus the new meta-findings under the same strict convergence guarantee.

**Architecture:** three additions on top of the SP12 family. (1) **Loop telemetry + memory** (the keystone): a KPI miner that derives per-phase/per-repo metrics from artifacts the loop already produces, and a two-tier lessons ledger whose entries are injected into future worker packets and escalate prose→code after repeated firing. (2) **Self-application harness**: a deterministic instruction-lint plus budgeted behavioral evals, with a standing rule that each iteration dogfoods one not-yet-self-applied family skill on the family. (3) **Adaptive control**: a guaranteed-minimum + best-yield batch allocator and a bounded amendment-proposal protocol so the loop can surface contract-blocked improvements instead of failing silently.

**Tech Stack:** Python 3.11+ stdlib only for new code (family rule); git; the existing pinned tools; opencode-worker-bridge / codex-cli-branch-workers / native subagents for workers; the GitHub CLI/API for CI evidence.

---

## Lineage and entry state (RE-VERIFY AT LAUNCH)

- Predecessor: SP12 (`docs/superpowers/plans/2026-06-12-sp12-convergent-parallel-loop.md`, ledger `docs/self-audit/2026-06-sp12-convergent-loop.md`). SP12 shipped W0 gate parallelization + timing budget, the `exec-audit` and `growth-audit` leaves, the registry-driven parallel wave, and burned down baselines under K-1. This combined run **continues from SP12's final main** rather than relaunching.
- **Entry (continuation):** SP12 has written its final summary and all three mains are clean + CI-green with no live SP12 worker. Re-verify the current mains and the inherited open residue from the SP12 ledger tail (terminal record: repo-A 260, repo-B 13, repo-P 25 = 298 rows; final versions repo-A v0.5.21, repo-B v0.4.6, repo-P v0.3.8 — re-read; ledgers are truth). Confirm SP12's writers have stopped before starting; never run two loops against the same repos. Bootstrap probe green.
- Repos: repo-A `~/projects/repo-audit-skills` (≥18 leaves at SP12 final version), repo-B `~/projects/repo-audit-refactor-optimize`, repo-P `~/projects/perf-benchmark-skill`. Installed root `~/.claude/skills` → `~/.agents/skills`.
- SP13 inherits the SP12 residue as its starting backlog AND expands it with the meta-findings the X1 harness surfaces (instruction-lint, self-application). The X4 burn-down absorbs any unfinished SP12 burn-down directly. The X3 re-freeze closes that expanded universe.

## Why this run exists (evidence from SP11+SP12, verified)

1. Every process improvement to date (SP11's speed diagnosis, SP12's parallelization and convergence guards) was noticed and designed by humans, never by the loop. The loop improves source; humans improve process. SP13 closes that gap.
2. The `npm ci`-in-worktree lesson bit the SP12 W0.1 workers, then bit the release-prep worker again hours later in the same run (SP12 ledger, "Issues fixed during release-prep"). A learning loop pays a recurring lesson **once**.
3. The 631-line repo-B instruction layer (SKILL.md + references/) and every leaf SKILL.md drive worker behavior but have only name/version + CLI-flag checks. The loop has never improved an instruction based on observed worker behavior, because nothing measures whether such a change helps.
4. The triage test suite is 220 tests (2.3× the next largest) and is the wall-clock floor of every gate run; the family owns `test-redundancy-triage` and has never pointed it at itself.

## Design rules (inherited from SP12 + SP13 additions)

- **R1 repo-agnostic** (inherited): new leaves/lanes declare `languages: ["*"]`, read only universal artifacts, ship a non-Python + a degenerate fixture.
- **R2 admission** (inherited): every new skill/gate/config/metric states in its docs the signal it makes visible, why no existing component hosts it, and its sunset criterion. This plan's additions carry those statements.
- **R3 surface budget** (inherited): every growth-metric increase needs a reasoned, release-expiring allowance. SP13's own additions are pre-allowanced in X0.
- **R4 determinism vs timing** (inherited): timing/telemetry artifacts are NEVER part of convergence byte-comparison.
- **R5 mined-not-reported (NEW):** loop telemetry is *derived from artifacts*, never typed by the orchestrator. No KPI may originate from orchestrator prose; if it can't be mined from git/run-dirs/CI, it isn't a KPI.
- **R6 process-vs-findings separation (NEW):** post-freeze process batches (telemetry, lessons, allocation, instruction fixes) may touch orchestration/tooling/instructions only — never leaf finding-emission logic — so convergence byte-comparison of findings stays meaningful.
- **R7 lesson honesty (NEW):** a lesson enters as `candidate` and is promoted to `binding` only with recorded evidence it prevented a repeat; a lesson that fires ≥3 times must be escalated from prose to tooling (a setup script, a gate, a fixture) — memory that never becomes automation is debt.

## Contracts (FROZEN)

- **L-0 recursion** (= SP12 K-0): every iteration starts from the installed skillset; installed wave findings + inherited residue + meta-findings are the backlog; ship → reinstall → next iteration runs the improved skill.
- **L-1 convergence guarantee** (= SP12 K-1, extended): after the X3 freeze the finding universe is CLOSED — no new finding classes/lanes/metrics/eval cases (candidates go to `docs/superpowers/SP14-CANDIDATES.md`). Baselines shrink-only, equality-ratcheted. Each iteration every ACTIVE repo must shrink ≥1 row or take a strike; two strikes → TERMINAL (residue documented; verification visits only). Hard cap: 12 iterations post-freeze. Finite frozen set + strict decrease ⇒ termination.
- **L-2 surface budget** (= SP12 K-2): growth gate blocks unallowed growth; allowances reasoned + release-expiring; dependency growth never allowed. The lessons ledger and KPI files count as docs/tooling LOC and are budgeted like everything else (R7's escalation rule is the pressure valve).
- **L-3 worker-only + context conservation** (= SP12 K-3): the Opus orchestrator never edits/reads source; it consumes only status.json, gate tails (≤40 lines), findings/KPI JSON, and the ledger text it writes — never worker transcripts or source bodies. About to read source → dispatch a worker. Context conservation is load-bearing for an Opus orchestrator: subagents return SUMMARIES, and the orchestrator's own context holds packet IDs, counts, gate tails, and ledger text only.
- **L-4 parallelism + worker routes** (= SP12 K-4, re-modeled for Opus): repos visited concurrently (one writer per repo via worktrees); ≤2 worktrees/repo on disjoint files; **≤4 concurrent worker sessions globally**; CI watches always overlapped, never busy-waited. **PRIMARY route = native Opus subagents** dispatched via the Agent tool with `run_in_background=true` and `isolation="worktree"` (or an explicit `/tmp/sp13/<repo>-<iter>-<slug>` worktree), file-backed packets. **ALTERNATIVE route = opencode-worker-bridge** concurrent workers with identical file-backed L-7 packets, used when more parallelism than the subagent budget is wanted. Infra failure on one route → switch the affected packet to the other route (one-way for that packet, logged). A gate-failing CHANGE is a normal discard/retry, NOT a route switch.
- **L-5 batch discipline** (= SP12 K-5): single-signal throwaway-worktree batches; mutation gate ≥80% scoped for behavior-changing batches; golden+byte-identical for mechanical moves; discards recorded, never retried identically. **Allocation (NEW, L-5a):** every ACTIVE repo gets ≥1 batch per iteration (guaranteed minimum, defeats starvation); remaining budget (≤6/repo cap) goes to the repo with the best trailing rows/hour from `iteration_kpis.jsonl`; the ledger records a one-line allocation rationale citing the mined yield.
- **L-6 ship gate** (= SP12 K-6): per changed repo — gates green → convergence ×2 → fresh-clone sim → push → CI watch → release+reinstall only when leaf behavior changed → readback + probe → hotspot re-anchor. One bounded fix-forward on CI red; second red on a repo = that repo TERMINAL(BLOCKED).
- **L-7 worker packets** (= SP12 K-7, extended): file-backed, one goal, ≤2 files, failing test included, exact command+expected, ≤8k tokens, TDD. Identical packet shape on both routes (native Opus subagent or opencode) — the JSON artifacts under the run dir are the source of truth, never chat memory. **Lesson injection (NEW):** the packet synthesizer attaches scope-matched `binding` lessons (hard cap 5, one sentence + command each) to every packet it builds. Reviewer packets are read-only and return `{verdict, reasons[]}`.
- **L-8 amendment protocol (NEW):** when the loop hits a contract-blocked improvement it writes `docs/superpowers/amendment-proposals/NNN.md` (schema in X4.3), continues other work, and does NOT self-apply the amendment — it is operator-reviewed async. Max 3 proposals per run; over-proposing is itself a flagged anti-pattern in the ledger.
- **L-9 termination** (= SP12 K-8): DONE = DoD met; BLOCKED = cap/zero-shrink/second-CI-red/contract-impossible, with complete ledger + report. Both valid; never game thresholds; never suppress real findings.
- **L-10 ledger** (= SP12 K-9, extended): `docs/self-audit/2026-06-sp13-runtime-self-improvement-loop.md`, appended once per iteration: installed versions, rows before/after per repo, batches accepted/discarded, worker run dirs, **the mined KPI row for the iteration**, **lessons added/promoted/escalated**, **allocation rationale**, **self-application target + result**, ship evidence, growth-allowance table, TERMINAL declarations.

## Definition of Done (falsifiable)

1. `iteration_kpis.jsonl` exists in repo-A, is appended every iteration by the miner (not the orchestrator — R5), and the ledger's per-iteration KPI row is copied from it verbatim.
2. `lessons.jsonl` exists with ≥1 `binding` lesson; the packet synthesizer demonstrably injected ≥1 lesson into ≥1 real packet (worker run-dir shows it); ≥1 lesson reached R7 automation-escalation (a committed setup script/gate/fixture) OR the ledger records that no lesson fired ≥3 times.
3. Instruction-lint gate is live in repo-A (every command quoted in a SKILL.md exists and answers `--help`; required sections present), green, with the R1 fixture pair passing.
4. ≥1 behavioral-eval case runs (pinned model, budgeted, advisory) and its artifact is recorded; the self-application checklist shows each iteration dogfooded one previously-unapplied family skill on the family, with results.
5. The L-5a allocator ran every iteration with a recorded rationale; no ACTIVE repo went an iteration with zero batches unless TERMINAL.
6. Inherited SP12 residue + meta-findings: all baselines `[]` or each repo TERMINAL with documented residue; fresh-clone green; CI green zero deprecations; final repo-A release tagged.
7. Growth allowances empty of expired entries; ledger complete per L-10; ≤3 amendment proposals, each operator-dispositioned.

---

## Work package X0 — loop telemetry + memory (the keystone; lands FIRST, everything else proves itself through it)

### Task X0.1: KPI miner (repo-B; mined, never reported — R5)

**Files:**
- Create: `repo-B scripts/mine_iteration_kpis.py`
- Create: `repo-A scripts/iteration_kpis.jsonl` (append-only; tracked — it IS the evidence, unlike timing telemetry)
- Test: `repo-B tests/test_mine_iteration_kpis.py`

Admission (R2): signal = loop process efficiency over time; no existing component measures the loop's own runtime — gates time themselves but nothing aggregates per-iteration yield/repair/wait; sunset = if the orchestrator harness grows native run telemetry, read that instead.

- [ ] **Step 1: Failing test** — `tests/test_mine_iteration_kpis.py`:

```python
import json
import scripts.mine_iteration_kpis as m


def test_rows_per_hour_from_counts_and_duration():
    kpi = m.compute_kpi(
        iteration=5,
        rows_before={"repo-a": 40, "repo-b": 7},
        rows_after={"repo-a": 36, "repo-b": 7},
        phase_seconds={"diagnosis": 120.0, "execution": 3480.0, "ship": 600.0},
        worker_runs=[{"repairs": 1}, {"repairs": 0}, {"repairs": 0}],
        ci_wait_seconds=300.0,
    )
    assert kpi["rows_closed"] == 4
    assert round(kpi["rows_per_hour"], 2) == round(4 / (4200 / 3600), 2)
    assert kpi["repair_rate"] == 1 / 3
    assert kpi["ci_wait_seconds"] == 300.0
    assert kpi["iteration"] == 5


def test_regression_flag_only_on_loop_controlled_metrics():
    # CI wait growth must NOT trip the regression flag (external, not loop-controlled).
    prev = {"rows_per_hour": 4.0, "repair_rate": 0.1, "ci_wait_seconds": 100.0}
    cur = {"rows_per_hour": 4.1, "repair_rate": 0.1, "ci_wait_seconds": 9000.0}
    assert m.is_regression(cur, prev) is False
    worse = {"rows_per_hour": 1.0, "repair_rate": 0.5, "ci_wait_seconds": 100.0}
    assert m.is_regression(worse, prev) is True
```

- [ ] **Step 2: Run → FAIL.** `python3 -m pytest tests/test_mine_iteration_kpis.py -q`.
- [ ] **Step 3: Implement `mine_iteration_kpis.py`.** Pure functions `compute_kpi(...)` and `is_regression(cur, prev)` plus a `main()` that DERIVES inputs from artifacts (never args the orchestrator types): `phase_seconds` from git commit timestamps in the iteration window + worker run-dir mtimes; `rows_before/after` from the ratcheted baseline JSONs at the iteration's start/end SHAs; `worker_runs` repairs from counting follow-up commits per packet run-dir; `ci_wait_seconds` from the GitHub CI run created→completed delta via `gh`/API. `is_regression` compares ONLY `rows_per_hour` (down >20%) and `repair_rate` (up >50%); `ci_wait_seconds` and any external wait are recorded but never trip the flag (R5/L-5a integrity). Append one JSON line to `iteration_kpis.jsonl`.
- [ ] **Step 4: Suite green; commit** `feat(kpi): mine per-iteration loop telemetry from run artifacts`.

### Task X0.2: two-tier lessons ledger + injection (repo-B)

**Files:**
- Create: `repo-A docs/self-audit/lessons.jsonl` (append-only, tracked)
- Create/Modify: `repo-B scripts/synthesize_packets.py` (the SP12 W4 synthesizer — add `inject_lessons`)
- Test: `repo-B tests/test_lessons.py`

Admission (R2): signal = recurring operational failure; no existing component carries forward a repair so a worker doesn't rediscover it; sunset = a lesson that escalates to tooling (R7) is deleted from the ledger, replaced by the automation it spawned.

- [ ] **Step 1: Failing tests** — `tests/test_lessons.py`:

```python
import json
import scripts.synthesize_packets as sp


def test_scope_matched_binding_lessons_injected_capped():
    lessons = [
        {"id": "L1", "tier": "binding", "scope": "worktree-setup",
         "text": "run npm ci in fresh worktrees", "command": "npm ci"},
        {"id": "L2", "tier": "candidate", "scope": "worktree-setup",
         "text": "candidate not yet proven", "command": ""},
        {"id": "L3", "tier": "binding", "scope": "release",
         "text": "changelog date must match commit date", "command": ""},
    ]
    packet = {"scope": "worktree-setup", "files": ["a.py"]}
    out = sp.inject_lessons(packet, lessons, cap=5)
    ids = [lz["id"] for lz in out["lessons"]]
    assert ids == ["L1"]            # only binding + scope match; candidate L2 excluded


def test_escalation_flag_after_three_fires():
    lesson = {"id": "L1", "tier": "binding", "fires": 3,
              "escalated": False, "scope": "worktree-setup"}
    assert sp.needs_automation(lesson) is True
    assert sp.needs_automation({**lesson, "fires": 2}) is False
```

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** `inject_lessons(packet, lessons, cap)` (filter `tier=="binding"` AND `scope==packet["scope"]`, sort by `fires` desc, truncate to `cap`, attach under `packet["lessons"]` as `{text, command}` — total added text bounded so L-7's 8k budget holds) and `needs_automation(lesson)` (`tier=="binding" and fires>=3 and not escalated`). The orchestrator's loop: on every worker repair round, append/increment a lesson (new ones enter `tier:"candidate"`); promote candidate→binding only when the ledger records it prevented a repeat; when `needs_automation` is True, the iteration MUST spend one batch turning it into a setup script/gate/fixture and mark `escalated:true` (R7).
- [ ] **Step 4: Suite green; commit** `feat(lessons): two-tier lessons ledger with capped scope-matched injection`.

### Task X0.3: ship X0 (L-6) and seed the first lessons

- [ ] Ship repo-A + repo-B per the ritual. Seed `lessons.jsonl` with the two proven SP11/SP12 lessons as `binding` (they already fired 3+ times): `worktree-setup`/"run `npm ci` in fresh worktrees or jscpd-dependent tests fail" (fires:4, escalated:false → X0.3 MUST also commit a `scripts/worker_worktree_setup.sh` that runs `npm ci`, satisfying R7 immediately and proving the escalation path) and `release`/"changelog heading date must equal the commit date". Record the escalation in the ledger.

## Work package X1 — self-application harness

### Task X1.1: instruction-lint (deterministic, gate-able)

**Files:**
- Create: `repo-A skills/docs-consistency-audit/...` extension OR `scripts/check_instruction_lint.py` (prefer extending docs-consistency-audit's existing CLI-flag checker — it already parses SKILL.md and argparse; add: every fenced command whose first token resolves to a family script must exist and answer `--help`; required sections `## Overview`, `## Limits` present)
- Test: alongside the chosen host; + R1 fixture pair (a non-Python skill skeleton, a degenerate doc with a dead command)

Admission (R2): signal = instruction drift (a SKILL.md telling a worker to run a command that no longer exists / lost a section); docs-consistency-audit checks flags but not command existence or section completeness; sunset = fold fully into docs-consistency-audit once stable.

- [ ] RED: a fixture SKILL.md quoting `python3 scripts/gone.py --help` → one `instruction_dead_command` LINT finding; a valid command → none; a SKILL.md missing `## Limits` → one `instruction_missing_section` finding. GREEN: implement; wire into the wave/gates if hosted as a leaf, else into `run_checks.py`. Commit.

### Task X1.2: behavioral eval (advisory, budgeted, pinned model)

**Files:** `repo-B scripts/run_instruction_eval.py` + one fixture eval case per high-traffic skill (start with `complexity-audit`: given a fixture repo and ONLY the SKILL.md, a pinned-model worker must produce findings JSON with the expected row count ±0).

- [ ] Implement as an advisory check (like mutation testing): pinned model, time/token budget, asserted artifact `eval_<skill>.json` `{expected_rows, actual_rows, pass}`. A drift (actual≠expected) is a `candidate` lesson + an advisory finding, never a hard gate (LLM nondeterminism must not fail a deterministic pipeline). Record in ledger. Commit.

### Task X1.3: self-application checklist (standing rule, no new code)

- [ ] Maintain `docs/self-audit/self-application-checklist.md`: the matrix of {family skill × applied-to-family?}. Each iteration MUST pick one `not-yet-applied` skill and run it on the family, recording results in the ledger. **First target: `test-redundancy-triage` on repo-A's own suites** (the 220-test triage suite is the gate wall-clock floor — DELETE-tier rows become ordinary L-5 speed batches; tests are not findings, so the freeze does not bind them). Subsequent: `test-effectiveness-audit`, `perf-benchmark` on the gate runner, etc.

## Work package X2 — adaptive control wiring

- [ ] **X2.1 allocator (L-5a):** add `scripts/allocate_batches.py` (repo-B): inputs = ACTIVE repos + `iteration_kpis.jsonl` tail; output = `{repo: batch_count}` with every ACTIVE repo ≥1 and surplus to best trailing rows/hour, total ≤6/repo. Test the guaranteed-minimum and surplus rules. The orchestrator calls it each iteration and copies its rationale into the ledger.
- [ ] **X2.2 amendment protocol (L-8):** create `docs/superpowers/amendment-proposals/` with a `TEMPLATE.md` (fields: blocked contract, measured impossibility with evidence, minimal proposed diff, risk, expected gain). No code; this is process. The `goal-plan-amender` skill in the toolbox is the precedent pattern.

## Work package X3 — ship all + expanded diagnosis + FREEZE

- [ ] **X3.1:** ship X0–X2 per L-6 (releases + reinstall where leaf behavior changed: instruction-lint if hosted in a leaf changes diagnosis; KPI/lessons/allocator are orchestration tooling in repo-B and reinstall repo-B).
- [ ] **X3.2:** run the expanded installed wave on all three repos at fresh anchors; triage NEW instruction-lint + self-application findings fixed-first; reconcile against the inherited SP12 residue.
- [ ] **X3.3:** FREEZE: write each repo's baseline (now including any instruction-lint rows that survived triage), commit, declare in the ledger "finding universe closed; L-1 active; hard cap 12 iterations." New classes → `SP14-CANDIDATES.md`.

## Work package X4 — convergent burn-down (post-freeze, with telemetry + memory + allocation live)

Per-iteration procedure (orchestrator follows verbatim; all hands are workers per L-3):

- [ ] **1. C-0 diagnosis:** bootstrap probe + installed wave per repo, concurrently. Backlog = wave findings + inherited residue + meta-findings.
- [ ] **2. Allocate:** run `allocate_batches.py`; record rationale (L-5a).
- [ ] **3. Self-apply:** pick the iteration's checklist target (X1.3); run it; fold any actionable result into the backlog.
- [ ] **4. Dispatch:** per ACTIVE repo, worktree + ranked single-signal batches via `synthesize_packets.py` (which now injects binding lessons, L-7); ≤2 concurrent worktrees/repo, ≤4 workers global.
- [ ] **5. Verify (orchestrator):** re-run gates, grep counts, ff-merge on green, ratchet shrink-only, discard+record otherwise. On any worker repair → append/increment a lesson (X0.2); if a lesson hits `fires>=3` → spend a batch on automation-escalation (R7).
- [ ] **6. Strict-shrink bookkeeping (L-1):** per repo rows before/after; zero shrink → strike; second strike → TERMINAL.
- [ ] **7. Ship (L-6)** per changed repo, overlapping CI watch with the next repo's step 4.
- [ ] **8. Ledger append (L-10):** copy the mined KPI row verbatim; record lessons added/promoted/escalated, allocation rationale, self-application result; if a contract blocked an improvement → write an amendment proposal (L-8), do NOT self-apply.

## Work package X5 — close-out

- [ ] **X5.1:** stale-skill purge, allowlist-driven (= SP12 W7 rule; eligibility table to ledger before any removal).
- [ ] **X5.2:** final reinstall + readback; bootstrap probe green.
- [ ] **X5.3:** final report: per-repo trajectory, KPI trend across all iterations (the loop's own learning curve — the headline SP13 artifact), lessons-→-automation escalations, self-application matrix completion, allocation history, amendment dispositions, growth-allowance audit (must be empty of expired), purge table, ship evidence. Final repo-A release (next minor). Verify every DoD row; report DONE or BLOCKED.

## Convergence argument

After X3 the open-row set is finite and the universe closed (L-1/R6: process batches add no findings). Each iteration every ACTIVE repo strictly shrinks its rows or takes one of two strikes toward TERMINAL; the guaranteed-minimum allocator (L-5a) ensures no repo is starved into a false strike. Surface cannot ratchet up (growth gate + expiring allowances, L-2). The lessons ledger cannot grow without bound (R7 escalates recurring lessons into code and deletes the prose). Therefore all-repos-TERMINAL is reached within `2×|R| + 2×repos` iterations, and the hard cap of 12 binds regardless. DONE and BLOCKED are both well-defined terminals.

## Out of scope (SP14 candidates — write them down, do not start)

Multi-language code-health leaves; auto-applying patches without a worker verify step; cross-repo lesson sharing beyond the family; ML-ranked backlog prioritization; any new finding class/lane after the X3 freeze; running the harness against foreign repos at scale (one R1 validation pass against a foreign repo is allowed as a self-application checklist item, not a work package).
