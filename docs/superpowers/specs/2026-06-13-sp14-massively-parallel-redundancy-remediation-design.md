# SP14 design — Massively-Parallel Redundancy Remediation (MPRR)

> Status: design approved (brainstorming), pre-plan. Successor to SP13
> (`docs/self-audit/2026-06-sp13-runtime-self-improvement-loop.md`, DONE 2026-06-13).
> Next step: `superpowers:writing-plans` → SP14 implementation/launch plan + freeze prompt.

## 1. Why this run exists

SP13 closed honest-TERMINAL on a **frozen** finding universe (repo-A v0.6.0, repo-B
`8f27083`, repo-P `ac58303`; all clean, CI-green). Re-running the same convergence
loop yields `[]` — there is no burn-down left in the frozen universe. SP14 therefore
**opens a new universe**: instead of *finding* redundancy and stopping at advisory
output, the loop now **acts** on redundancy findings and does so **massively in
parallel**.

Two properties the user fixed as non-negotiable:

- **Repo-agnostic** — the skillset must work well on *any* repo it is pointed at,
  and must dogfood cleanly on the family itself. (Not "run on many repos at once" —
  that is an across-repo concern explicitly out of scope; see §9.)
- **Conflict-free fan-out** — parallelism is dispatched over findings that **do not
  conflict with each other**, so every merge is trivial by construction.

The deferred SP13 candidate "auto-applying patches without a worker verify step" is
pulled *in* — but the worker verify step is **preserved** as the trust mechanism
(§5), not dropped.

## 2. Scope

**In scope — the "redundancy" lane set:**
- duplicate-code `EXTRACT` (cross-file) / `MERGE` (same-file) — `duplication-audit`
- dead-code `DELETE` — `dead-code-audit`
- unused-imports `F401` / redefinitions `F811` / unused-locals `F841` — `dead-code-audit` (ruff)
- redundant-test `DELETE` / `MERGE` — `test-redundancy-triage`, **including the
  parked 142-MERGE triage backlog surfaced in SP13 X1.3**

**Out of scope (SP14):** non-redundancy lanes (complexity, structure, coverage,
security, hotspot), multi-language remediation (stay Python-oriented per the user),
region/hunk-level and symbol-level conflict models (§9), across-repo fan-out (§9).

The engine is **generic over "any conflict-free finding with a declared file-set"**;
SP14 only wires the redundancy lanes. Other lanes are a later wiring exercise, not a
re-architecture.

## 3. Locked decisions (from brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Parallelism axis | **Within-repo conflict-free fan-out**, repo-agnostic | User: repo-agnostic = "works well on any repo + dogfoods itself"; fan-out unit = non-conflicting findings |
| Conflict rule | **File-level** (two findings conflict iff they share a file) | Merges conflict-free by construction; most redundancy findings are single-file; semantic breakage caught by the gate |
| Autonomy | **Fully unattended, gate-gated** | The gates are the trust; the only model that scales to "massively parallel" |
| Scheduler | **Continuous saturating pool (Approach 2)**; wave-mode is its degenerate `N = wave-width` fallback | Saturated pool + immediate conflict-free merges + amortized CI = genuine massive throughput |
| Home | Engine in **repo-B** (`repo-audit-refactor-optimize`); audit leaves stay in **repo-A**; orchestration docs in **repo-A** `docs/superpowers/` | repo-B is already the remediation orchestrator; repo-A is the single doc authority |

## 4. Architecture

### 4.1 Where code lives
- **repo-A** (`repo-audit-skills`): the redundancy audit leaves
  (`duplication-audit`, `dead-code-audit`, `test-redundancy-triage`) — already exist,
  emit the shared finding schema, **unchanged** except any additive normalization
  field. Orchestration docs (this spec, the plan, the ledger) live here.
- **repo-B** (`repo-audit-refactor-optimize`): the **new MPRR engine** (components
  §4.2). repo-B is already "diagnosis → remediation → optimization orchestration."
- **repo-P** (`perf-benchmark-skill`): dogfood target only.

All new code is **Python ≥3.11 stdlib-only**, deterministic, repo-agnostic (R1: ship
a non-Python fixture + a degenerate fixture).

### 4.2 Components (8)
1. **Finding ingest / normalizer** — reads the lanes' JSON findings →
   `{id, lane, files[], line_ranges, remediation_class}` where
   `remediation_class ∈ {mechanical, refactor, test_removal}` (selects the gate, §5).
2. **Conflict-graph partitioner** — file-level conflict graph (node = finding,
   edge = shared file); exposes `eligible(finding, locked_files) = files(finding) ∩
   locked_files == ∅` and a deterministic eligibility iterator.
3. **Saturating scheduler** — holds the pool at ceiling **N**; maintains the live
   `locked_files` set; fills every free slot with the next eligible finding; on a
   worker's verified green, hands its branch to the integrator, releases its locks,
   refills. Emits telemetry every transition.
4. **Remediation packet synthesizer** — per finding, a file-backed worker packet:
   the finding, the exact remediation, the **declared allowed files**, the scoped
   gate command + expected result, TDD; lane-specific templates; scope-matched
   `binding` lessons injected (SP13 L-7), hard cap 5.
5. **Worker route** — PRIMARY native Opus subagent (Agent tool, `run_in_background`,
   `isolation="worktree"`); ALTERNATIVE `opencode-worker-bridge` with identical
   file-backed packets. Worker edits only its declared files, runs the scoped gate,
   writes `status.json` + a branch. Route infra failure → switch that packet once
   (logged, one-way).
6. **Gate verifier + merge integrator** — the orchestrator **re-checks** the worker's
   gate evidence (a worker's self-reported "green" is never evidence); merges the
   disjoint branch into the integration branch (serialized git op, conflict-free by
   construction); runs the local full gate per batch; pushes to CI **once per
   pool-drain** (one batch per iteration), not per-merge — the per-worker local gates
   provide the continuous safety, CI is the amortized iteration-level check.
7. **Convergence controller** — pool drains → re-audit → strict-shrink-or-strike →
   reinstall (if leaf behavior changed) → next iteration / TERMINAL.
8. **Ledger + KPI miner** — SP13 carryover (`mine_iteration_kpis.py`); new mined
   metrics: pool utilization, **merge-conflict-rate (must be 0)**, peak/mean
   concurrency, rows/hr, repair-rate. Mined from artifacts, never typed (SP13 R5).

### 4.3 Data flow (one iteration)
```
install skillset
  → run redundancy lanes on target repo → findings JSON
  → normalize → build file-level conflict graph
  → scheduler loop:
       while findings remain:
         while pool < N and ∃ eligible finding:
           synthesize packet → dispatch worker → lock its files
         on worker completion:
           verify gate evidence
             green → integrator merges disjoint branch (0 conflicts), release locks, record
             red   → discard, record, release locks, one bounded alt-strategy retry → else deferred-hard
  → pool drained → local full gate + fresh-clone sim → batched push + CI watch
  → reinstall changed skills → re-audit → strict-shrink check → repeat or TERMINAL
```

## 5. The load-bearing invariant & the gate ladder

### 5.1 Invariant
**At every instant, all running workers' file-sets are pairwise disjoint.** Enforced
by three checks (the triple):
- **Dispatch eligibility** — lock manager only dispatches a finding whose file-set is
  disjoint from `locked_files`.
- **Integrator assertion** — every merge is asserted conflict-free; a reported textual
  conflict is structurally impossible under the invariant → **hard stop + escalation**
  (it means a partitioner or worker bug).
- **Worker scope check** — the verifier rejects any worker whose diff touches a file
  outside its declared lock (closes the "rogue worker" hole).

Disjoint files guarantee no *textual* conflict; *semantic* breakage (delete symbol in
X used by Y) is caught by the gate ladder below + the post-batch full gate + CI.

### 5.2 Gate ladder (what authorizes an unattended auto-merge)

| `remediation_class` | Findings | Gate |
|---|---|---|
| `mechanical` | dead-code `DELETE`, unused-imports | Golden/byte-pattern check + full test suite green + lane re-audit shows the finding gone. No mutation (deletion cannot add behavior). |
| `refactor` | duplicate `EXTRACT` / `MERGE` | Scoped **mutation ≥80%** on touched modules + tests green + duplication re-audit shows the clone gone. Behavior-preservation is proven, not assumed. |
| `test_removal` | redundant-test `DELETE` / `MERGE` (incl. 142-MERGE backlog) | `test-redundancy-triage` evidence at **high-confidence tier only**: coverage parity (line+branch unchanged) **and** mutation parity (kill-set not weakened). Below high-confidence → deferred, never merged. |

## 6. Failure handling (SP13 L-4/L-5/L-6 carryover)
- Worker gate red → discard, record, release locks; one bounded **alternative-strategy**
  retry; then `deferred-hard` (logged, never retried identically).
- Worker diff outside declared lock → discard + flag (invariant threat).
- Integrator merge conflict → hard stop + escalate (impossible under invariant).
- Batched CI red → one bounded fix-forward; second red on a repo → that repo
  `TERMINAL(BLOCKED)`.
- All remaining findings conflict with running ones → pool simply drains below N; a
  huge cross-file `EXTRACT` serializes — acceptable, logged. No deadlock: eligibility
  is monotonic as locks release.

## 7. Convergence & termination (L-1 discipline)
The **redundancy-finding count** is the convergence metric. Each iteration the target
repo must shrink ≥1 or take a strike; **2 strikes → TERMINAL** with documented
residue (e.g. SP12-justified intrinsic clones; test-merges stuck below high-confidence;
cross-file EXTRACTs whose refactor can't reach mutation ≥80%). Hard cap **12**
iterations. Never game thresholds; never suppress real findings (SP13 L-9).

## 8. Definition of Done (falsifiable)
1. Partitioner is **property-proven conflict-free**: no schedule it emits ever
   co-locks two file-overlapping findings.
2. ≥1 real iteration ran **N ≥ 8** workers concurrently with **merge-conflict-rate =
   0** (mined from artifacts, not asserted in prose).
3. The **142-MERGE triage backlog** is acted on — merged-or-justified — each with
   coverage+mutation-parity evidence.
4. Runs unattended end-to-end on a **family repo AND ≥1 foreign repo** (any
   non-family Python repo, chosen at plan time) — the repo-agnostic proof.
5. Gate ladder enforced per class — a `refactor` with mutation <80% **cannot** merge
   (fixture-proven).
6. KPI miner records pool utilization, merge-conflict-rate (=0), rows/hr; ledger
   appended per iteration per L-10.
7. Family repos reach terminal-with-documented-residue, CI green, **repo-B release
   tagged + reinstalled + readback/probe green**.

## 9. Non-goals / deferred to SP15
- **Region/hunk-level** and **symbol/dependency-level** conflict models (wider fan-out
  within a file; the file-level model is the safe v1).
- **Across-repo fan-out** (engine pointed at many repos concurrently with a global
  resource governor).
- **Multi-language remediation** (stay Python-oriented).
- Wiring non-redundancy lanes (complexity/structure/coverage/security) into the engine.

## 10. Testing strategy
- **Property tests (hypothesis):** for any random finding set, every schedule the
  scheduler emits satisfies the disjoint-lock invariant; the integrator never sees a
  conflict.
- **Fixture repos:** (a) synthetic Python repo with *known* redundancies
  (k dead-code, m duplicates, j redundant tests) + a known-optimal partition → assert
  0-conflict drain + expected concurrency; (b) degenerate fixture (all findings share
  one file → fully serial, still correct); (c) non-Python fixture (R1 repo-agnostic).
- **Dry-run mode:** produces the partition + packets without dispatching, asserted
  against golden — doubles as the propose-only safety valve.
- The remediation itself is verified by the gate ladder, dogfooded on the family.

## 11. Pre-launch checklist (carried from the dogfood-loop convention)
- Three mains clean + CI-green, no live worker.
- Prune stale `/tmp/sp1*` artifacts + stale git worktrees.
- opencode-worker-bridge answers.
- SP14 plan + freeze prompt written and committed in repo-A `docs/superpowers/`.
