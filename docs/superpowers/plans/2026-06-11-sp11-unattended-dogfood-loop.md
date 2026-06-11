# SP11: Unattended Dogfood Loop — burn the baselines to zero

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
>
> **For the SP11 orchestrators:** this plan is the single authority for scope, contracts, and DoD. SP11 runs under the /goal runtime (goal-main-orchestrator → goal-branch-orchestrator); branch prompts derive from this plan via goal-preflight (`docs/superpowers/SP11-GOAL-BRIEF.md`). All orchestrator sessions are Codex gpt-5.5 running UNATTENDED (approvals disabled). Mechanical work is delegated through opencode-worker-bridge (file-backed packets, C-7). A worker's green is NOT evidence — orchestrators re-run every gate themselves and read real output.

**Goal:** run the SP10-proven steady-state dogfood loop unattended and iteratively — probe → wave → triage → mutation-gated batches → ratchet → convergence ×2 → machine ship gate — until every ratcheted baseline across repo-A/B/P is zero (each finding fixed at source or config-gated-and-counted), or until the loop terminates BLOCKED with complete evidence (a valid outcome — see Terminal states). The machine ship gate replaces SP10's human T6 gate.

**Architecture:** one /goal main orchestrator (gpt-5.5, unattended); branch lanes B0–B5 with rolling scheduling; workers via opencode-worker-bridge; structural attempts in throwaway worktrees so a discard never touches main; per-iteration ship through C-6.

**Authorization (2026-06-11, explicit, given by the human in conversation):** gpt-5.5 agents run without human approval. Pushes, tags, releases, and reinstalls proceed automatically once C-6 machine gates pass. The stale-skill purge (deferred since SP9 pending authorization) is authorized as Task B5.1 under its allowlist constraints. The C-8 STOP conditions are the only halt points.

**Repos (verified 2026-06-11, post-SP10 ship):**

- repo-A `/home/jakub/projects/repo-audit-skills` — main `56834cd`, v0.5.1, CI `27360552572` green; 9 gates green. Baselines: selfaudit **92** (27 `duplicate_tokens` + 25 `function_nloc` + 22 `cyclomatic_complexity` + 16 `parameter_count` + 2 `maintainability_index`); security **49** (26 B603 + 17 B404 + 4 B607 + 2 B105); docs/dependency/hygiene/coverage all `[]`.
  - Debt concentration: `skills/test-redundancy-triage/scripts/triage_redundancy.py` (3110 lines, **35** rows), `skills/test-audit-pipeline/scripts/audit_pipeline.py` (781 lines, **12**), `skills/test-quality-assurance/scripts/audit_test_quality.py` (963 lines, **12**) — 59 of 92 rows in three files.
- repo-B `/home/jakub/projects/repo-audit-refactor-optimize` — main `7c23276` = tag v0.4.1, CI green; 101 tests; wave baseline **9** = 3 `maintainability_index` + 1 `parameter_count` + 3 `churn_complexity_product` + 2 `temporal_coupling_ratio`.
- repo-P `/home/jakub/projects/perf-benchmark-skill` — main `ac89675`, v0.3.0, CI green; 154 tests; wave baseline **55 normalized ids / 67 raw** = 20 `cyclomatic_complexity` + 12 `function_nloc` + 5 `maintainability_index` + 3 `parameter_count` + 21 security (13 B603 + 3 B105 + 2 B404 + 2 B607 + 1 B324) + 6 hotspot (3 `temporal_coupling_ratio` + 2 `churn_complexity_product` + 1 `author_concentration`).
- Installed `~/.claude/skills` → `~/.agents/skills`: 16 leaves @ 0.5.1, repo-audit-refactor-optimize 0.4.1, perf-benchmark 0.3.0, perf-optimization 0.2.0; bootstrap probe green (`restart_required=false`, `stop_before_discovery=false`).

## Out of scope (SP12 candidates, do not start)

Multi-language leaves; second perf-benchmark target (`bench_parse_massif` surface exhausted, 3 consecutive honest no-wins); opencode-worker-bridge feature changes (consume as-is); goal-skill changes; hetzner delegation.

## Empirical pre-flight (verified 2026-06-11; re-verify rows 1–4 before editing)

1. **Security class shape:** 47/49 repo-A security rows are the trusted-internal-subprocess triple — B404 (`import subprocess`), B603 (`subprocess.run` without shell), B607 (partial executable path) — on family scripts that shell out to pinned tools (`git`, `jscpd`, `bandit`, `lizard`, `radon`, …). Leaf CLI today: `skills/security-audit/scripts/security_audit.py` with `--format/--root/--out-dir/--config` where `--config` is JSON threshold overrides (`:55`). repo-P has the same triple (17 rows) plus 3 B105 (hardcoded-string heuristic) and 1 B324 (weak hash).
2. **Mutation tooling exists:** test-effectiveness-audit wraps `mutmut==3.6.0`, sandboxed copy, per-module kill rates (`skills/test-effectiveness-audit/scripts/test_effectiveness_audit.py`). This is the C-3 mutation gate instrument.
3. **helpers.py collision:** ≥10 skills ship `tests/helpers.py`; repo-A has no root pytest config; `python3 -m pytest skills -q` from the root collides on duplicate module identity while every per-skill suite is green. `npm run check` (9 gates) never runs cross-skill pytest, so the class is unsurfaced. Fix = per-suite aggregator gate (B0.1), not import surgery.
4. **CI runtime deprecation is in ALL THREE repos, not just repo-P:** repo-A `.github/workflows/check.yml` pins `checkout@v4` + `setup-python@v5` + `setup-node@v4` with `node-version: '20'`; repo-B pins `checkout@v4` + `setup-python@v5`; repo-P pins `checkout@v4` + `setup-python@v5`. Bump all three to current majors (`checkout@v5`, `setup-python@v6`, repo-A also `setup-node` current major + `node-version: '22'`). Acceptance is falsifiable per repo: a CI run with zero deprecation annotations.
5. **Hotspot semantics (row inventory verified 2026-06-11):** hotspot rows are git-history-derived. The leaf ALREADY supports anchoring and windowing: `--rev` (analyse from a fixed revision, `hotspot_audit.py:185`) and a max-commits history window (`read_history(root, rev, max_commits)`, `:79`). The baseline rows split into three classes:
   - *Declared-intentional coupling pairs* — repo-B `SKILL.md<->references/pipeline.md` and `skill_bootstrap_manifest.json<->tests/test_check_skill_requirements.py`; repo-P `README.md<->SKILL.md`, `README.md<->scripts/perf_benchmark_pipeline.py`, `SKILL.md<->scripts/perf_benchmark_pipeline.py`. Docs-with-source and manifest-with-guard-test co-change is by design → C-1 policy class (B1.3), counted, never silent.
   - *Single-maintainer author concentration* — repo-P `perf_benchmark_pipeline.py` → C-1 policy class (B1.3).
   - *Churn×complexity on source/test files* — repo-B `check_skill_requirements.py`, `skill_bootstrap_manifest.json`, `tests/test_check_skill_requirements.py`; repo-P `reporting.py`, `perf_benchmark_pipeline.py`. These are REAL signals: they dissolve only when the complexity factor drops (B3.2/B4.3 refactors) or the churn ages past the `max_commits` window — NEVER via a suppression class.
   - *Refactor-induced churn growth rule:* the refactoring activity itself raises churn on exactly the files being fixed. During a lane, every wave/gate hotspot invocation pins `--rev` to the lane-start anchor SHA recorded in the baseline metadata; the anchor advances only at the lane-completion ship, where any newly surfaced rows are triaged fixed-first before the final ratchet. Growth at re-anchor that traces solely to the lane's own accepted refactor commits is recorded in the ledger and re-anchored away by the next lane-completion run, not treated as C-4 unfixable growth.
6. **Binding lessons (SP9/SP10):** fresh-clone sim before ANY push (`git clone <repo> /tmp/x && <gates>`); never trust a piped exit code — grep the gate JSON; merge commits can carry content no branch run saw (`git log -S` needs `-m`); duplication baseline rows are line-pinned — any edit to a clone file makes stale + new rows, so re-baseline in the SAME commit as the edit.
7. **Installed-root reality:** `~/.agents/skills` mixes this family with foreign families (superpowers:*, goal-*, scite-search, ml-*, m10/m15, …). The purge (B5.1) must be allowlist-driven from family source manifests and must never touch non-family dirs.

## Contracts (FROZEN)

- **C-1 precision discipline:** every FP-class fix is config-gated, suppressions are COUNTED in the leaf report (never silent), regression tests cover both directions (FP suppressed; true positive still fires), SKILL.md Limits documents the rule.
- **C-2 versions (lane-end only):** version bump + tag + GitHub release + reinstall happen ONLY at lane-completion ships — B1.4 (repo-A 0.5.2), B3.3 (repo-B 0.4.2), B4.5 (repo-P 0.3.1), and the final DoD ship (repo-A 0.6.0; package.json + all 16 SKILL.mds + check_release expectations + installer + CHANGELOG every time). Intermediate iteration ships push source to main with CI watch but NO bump, NO tag, NO reinstall — this keeps installed leaves stable under the parallel lanes and avoids release spam. Baseline/docs ratchets alone never bump.
- **C-3 structural batches:** ≤2 per repo per iteration, hotspot-ranked, single-signal, attempted in a throwaway worktree (`git worktree add /tmp/sp11-attempt-<n>`), merged only if every gate stays green. **Mutation gate (scoped):** a batch that CHANGES behavior-bearing logic (function splits, logic simplification) requires test-effectiveness-audit kill rate ≥ 80% on the touched module(s) first; below that, land a unit-suite batch that raises it. Pure mechanical moves (relocating unedited functions, extracting verbatim duplicate blocks) may instead proceed under golden-suite green + byte-identical CLI output on a fixed fixture corpus. Mutation runs are scoped to the touched module(s) with a 30-minute budget per run; an overrun is recorded and the scope tightened — never waived silently. Discards are recorded in the ledger, never retried identically.
- **C-4 ratchet discipline:** baselines shrink-only; equality-ratcheted; tracked-docs deltas are fixed-first before any ratchet; unfixable growth = STOP (C-8) — except hotspot re-anchor growth, which follows the pre-flight 5 rule.
- **C-5 convergence:** after each iteration's changes, two consecutive identical full runs per touched repo (repo-A: all npm gates + wave; B/P: suite + `check_wave_baseline.py`), zero deltas, hotspot lane pinned to the lane anchor (pre-flight 5).
- **C-6 machine ship gate (supersedes SP10's human T6 per the authorization above):** two grades, strictly ordered.
  - *Iteration ship:* all local gates green → C-5 convergence → fresh-clone simulation green → push main → watch CI to completion. No bump/tag/reinstall.
  - *Lane-completion ship:* iteration ship + C-2 bump → tag + GitHub release → reinstall (node installer for repo-A; directory sync for B/perf skills) → installed readback + bootstrap probe green → hotspot re-anchor (pre-flight 5).
  - CI red after a push: ONE bounded fix-forward attempt; a second red on the same lane = STOP.
- **C-7 worker packets:** file-backed only — the JSON artifacts under the worker run dir are the source of truth, never chat memory; one goal, ≤2 files, full content inlined when ≤200 lines (else grep-anchored excerpts), the failing test included, exact run command + expected output, ≤8k tokens; TDD. Orchestrators re-run all gates themselves. **Route:** opencode-worker-bridge when the goal-config smoke shows a green opencode route (B0.2 proves it); otherwise the goal runtime's native worker ladder is allowed, under the SAME file-backed packet-artifact requirements. Multi-file structural batches exceed packet limits by design — those are executed by the branch orchestrator itself in the throwaway worktree, with workers handling ≤2-file sub-changes.
- **C-8 termination (two legitimate terminals):** the loop ends DONE when the DoD is met, or ends BLOCKED on: (a) two consecutive iterations with zero total baseline shrink across all active lanes; (b) unfixable baseline growth; (c) a second CI red on one lane; (d) any gate that cannot go green without violating C-1..C-7. BLOCKED = finish the ledger + final report for the completed work, push nothing further, and report the goal as blocked-with-evidence. BLOCKED after exhausting honest moves is a valid unattended outcome, not a failure to be retried.
- **C-9 evidence ledger (sharded, single-writer):** each lane appends per iteration to its OWN repo — B0/B1/B2/B5 to repo-A `docs/self-audit/2026-06-sp11-ledger-A.md`, B3 to repo-B `docs/sp11-ledger-B.md`, B4 to repo-P `docs/sp11-ledger-P.md` — recording baseline counts before/after, batches accepted/discarded with worktree evidence, worker run-dir paths, kill-rate readings, ship evidence (SHAs, CI run ids). Repo-A is written ONLY by its owning lane (B2 during Group 2). B5.3 merges the shards into the final report `docs/self-audit/2026-06-sp11-unattended-loop.md`.

## Definition of Done (falsifiable)

1. repo-A: `npm run check` green with **10** gates (the 9 existing + new `check:pytest`), selfaudit baseline `[]`, security baseline `[]`, docs/dependency/hygiene/coverage `[]`; fresh-clone sim green; CI green at final main with zero deprecation annotations; release tagged per C-2.
2. repo-B: wave baseline `[]`; full suite green; CI green with zero deprecation annotations; release tagged if source shipped.
3. repo-P: wave baseline `[]`; suite green; CI green with zero deprecation annotations; release tagged if source shipped.
4. Suppression honesty: every config-gated class (trusted-subprocess, coupling-allow-pairs, single-maintainer) is counted in leaf report output, covered by both-direction regression tests, and documented in SKILL.md Limits.
5. Installed readback: family skill sets exactly match source manifests (post-purge), at final versions; bootstrap probe exit 0, `restart_required=false`, `stop_before_discovery=false`.
6. The C-9 ledger shards and merged final report document every iteration, every discarded attempt, and the final ship evidence.

**Terminal states.** DONE = every row above met. BLOCKED = a C-8 condition fired with the ledger and final report complete for all work shipped to that point; this is a legitimate unattended outcome reported as blocked-with-evidence. The function-level complexity tail (47 CC/nloc rows in repo-A) may have an honest asymptote above zero — if so, the run ends BLOCKED there rather than gaming thresholds or suppressing real findings.

---

## Branch B0 — enablement (repo-A, serial; everything else depends on it)

### Task B0.1: full-pytest aggregator gate (surfaces the helpers.py class)

**Files:** Create `scripts/check_full_pytest.py`; Modify `package.json:11` (chain) + `:20` (new script entry); Modify `.gitignore` (snapshot entry — family convention, all six existing gate snapshots are gitignored at `.gitignore:14-19`).

- [ ] **Step 1: Reproduce the unsurfaced failure.** Run `python3 -m pytest skills -q` from repo-A root. Expected: collection error mentioning duplicate/mismatched `helpers` module (import file mismatch). Record exact output in the ledger.
- [ ] **Step 2: Write the gate (per-suite isolation, no import surgery):**

```python
#!/usr/bin/env python3
"""Gate: run every pytest suite in isolation; aggregate results.

Surfaces cross-skill failures that per-skill runs and npm gates miss,
without cross-suite module collisions (each suite is its own rootdir).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "scripts" / "full_pytest_snapshot.json"


def suite_dirs() -> list[Path]:
    dirs = [ROOT / "tests"] if (ROOT / "tests").is_dir() else []
    dirs += sorted(p for p in ROOT.glob("skills/*/tests") if p.is_dir())
    return dirs


def main() -> int:
    results = []
    for d in suite_dirs():
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(d), "-q", "--color=no"],
            capture_output=True, text=True, cwd=d.parent, check=False,
        )
        results.append({
            "suite": str(d.relative_to(ROOT)),
            "returncode": proc.returncode,
            "tail": proc.stdout.strip().splitlines()[-1:] or proc.stderr.strip().splitlines()[-1:],
        })
    SNAPSHOT.write_text(json.dumps(results, indent=2) + "\n")
    failed = [r for r in results if r["returncode"] != 0]
    print(f"full-pytest: {len(results) - len(failed)}/{len(results)} suites green")
    for r in failed:
        print(f"FAIL {r['suite']}: {r['tail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run `python3 scripts/check_full_pytest.py`.** Expected: `full-pytest: N/N suites green`, exit 0 (per-skill suites are green today). If any suite is red, fix it before wiring — that is exactly the class this gate exists to surface.
- [ ] **Step 4: Wire into npm and gitignore:** add `"check:pytest": "python3 scripts/check_full_pytest.py"`, append `&& npm run check:pytest` to the `check` chain, and add `scripts/full_pytest_snapshot.json` to `.gitignore` next to the other snapshot entries (a tracked snapshot would dirty the tree on every gate run and break C-5 convergence). Run `npm run check`; grep the output for 10 gate passes (never trust a piped exit code — pre-flight 6).
- [ ] **Step 5: Commit** `feat(gates): full-pytest aggregator gate (10th gate)`.

### Task B0.2: opencode-worker-bridge smoke (prove the delegation path before unattended use)

- [ ] Dispatch ONE trivial worker packet through opencode-worker-bridge (goal: run `python3 -m pytest skills/complexity-audit/tests -q` and report the tail). Validate per the bridge contract: run dir exists, JSON artifacts present, `run_status` consistent with artifacts. Record the run dir in the ledger. If the bridge cannot produce file-backed evidence, STOP (C-8d) — unattended delegation without evidence is not allowed.

### Task B0.3: mutation-signal census on the three concentration files (may run concurrent with B1)

- [ ] Run test-effectiveness-audit (sandboxed) against `test-redundancy-triage`, `test-audit-pipeline`, `test-quality-assurance` modules, scoped per module under the C-3 30-minute-per-run budget. Record per-module kill rates in the ledger. Modules ≥ 80% are immediately C-3 eligible; modules below get a unit-suite batch first (B2 recipe step 2). No source changes in this task. This census is read-only and only B2 consumes it — schedule it concurrent with B1, not blocking it.

### Task B0.4: repo-A CI runtime bump (workflow-only; rides the B1.4 ship)

- [ ] Bump `.github/workflows/check.yml`: `actions/checkout@v5`, `actions/setup-python@v6`, `actions/setup-node` current major with `node-version: '22'` (pre-flight 4). No gate logic changes. Acceptance: the B1.4 CI run completes with zero deprecation annotations.

## Branch B1 — precision round: security + hotspot leaves (repo-A source, ships before B2–B4 consume)

### Task B1.1: security-audit trusted-subprocess policy (C-1, TDD both directions)

**Files:** Modify `skills/security-audit/scripts/security_audit.py` + `_bandit.py` + `_reporting.py`; Test `skills/security-audit/tests/test_trusted_subprocess.py` (new); Modify `skills/security-audit/SKILL.md` (Limits).

- [ ] RED — five tests on tmp fixtures: (a) policy absent → B603 fires on a fixture script calling `subprocess.run(["git", ...])`; (b) policy enabled with `rules: ["B404","B603","B607"]` + matching `path_globs` → finding suppressed AND counted in report JSON under `suppressed_findings` with class `trusted_subprocess`; (c) B105 on the same fixture still fires under the policy (rule not in list); (d) a file outside `path_globs` still fires B603; (e) markdown output renders the suppression count line.
- [ ] GREEN — extend the existing `--config` JSON with:

```json
{
  "trusted_subprocess": {
    "enabled": true,
    "rules": ["B404", "B603", "B607"],
    "path_globs": ["scripts/**", "skills/*/scripts/**", "shared/**"]
  }
}
```

Default: absent/disabled — the leaf's general posture is unchanged for foreign repos. Suppressed rows carry `{"class": "trusted_subprocess", "rule": ..., "path": ...}` and are counted in both JSON and md output.
- [ ] SKILL.md Limits row documenting the policy and its counted-suppression guarantee. Leaf suite green. Commit.

### Task B1.2: repo-A security baseline 49 → 0

- [ ] Enable the policy in `scripts/check_security_audit.py`'s leaf invocation config (47 rows dissolve). Fix the 2 B105 rows at source (restructure the flagged string constants so the heuristic no longer matches — no `# nosec`). Ratchet `scripts/security_baseline.json` 49 → 0 in the same commit. `npm run check` 10/10 green.

### Task B1.3: hotspot-audit declared-coupling policy (C-1, TDD both directions)

**Files:** Modify `skills/hotspot-audit/scripts/hotspot_audit.py`; Test `skills/hotspot-audit/tests/test_family_policy.py` (new); Modify `skills/hotspot-audit/SKILL.md` (Limits).

No anchoring/windowing work needed here — `--rev` and the max-commits window already exist (pre-flight 5); the wave gates just start passing the lane anchor. The new policy covers ONLY the two declared classes; churn×complexity rows are explicitly NOT suppressible (pre-flight 5).

- [ ] RED — five tests on synthetic git fixtures: (a) `coupling_allow_pairs: [["SKILL.md", "references/**"]]` → that temporal-coupling finding suppressed AND counted under class `declared_coupling`; (b) coupling between two files matching NO declared pair still fires under the same config; (c) `single_maintainer: true` → author-concentration suppressed and counted; (d) policy absent → all fire; (e) a `churn_complexity_product` finding is unaffected by both keys (no suppression path exists for it).
- [ ] GREEN — config keys `coupling_allow_pairs: [[globA, globB], ...]` (a pair is suppressed only when each side matches one glob of a declared pair) and `single_maintainer: bool`, default off, counted suppressions in JSON + md, SKILL.md Limits. Leaf suite green. Commit.

### Task B1.4: ship the precision round (C-6 lane-completion ship)

- [ ] repo-A version bump per C-2 (0.5.1 → 0.5.2: package.json, 16 SKILL.mds, check_release, installer, CHANGELOG) including B0.4's workflow bump, convergence ×2, fresh-clone sim, push, CI watch (verify zero deprecation annotations — B0.4 acceptance), tag + release, reinstall, readback. B2–B4 may only start after this readback is green.

## Branch B2 — repo-A structural burn-down loop (iterative; selfaudit 92 → 0)

Iteration recipe — repeat until the selfaudit baseline is `[]` or C-8 stops the loop:

- [ ] **1. Triage:** rank remaining baseline rows; prefer the concentration files (`triage_redundancy.py` 35, `audit_pipeline.py` 12, `audit_test_quality.py` 12 = 59/92), then duplication clusters, then the long tail.
- [ ] **2. Mutation gate (C-3, scoped):** behavior-changing batches require kill rate ≥ 80% on the touched module(s) (B0.3 census or a scoped re-run, 30-minute budget); below that, dispatch a unit-suite worker batch first — tests target exactly the functions about to be changed. Mechanical-move batches use the C-3 golden-suite + byte-identical-CLI-output equivalence instead.
- [ ] **3. Structural batch in a throwaway worktree (single-signal). Know what dissolves what:** the 63 function-level rows (25 nloc + 22 CC + 16 params) follow the function wherever it lives — moving code between files relocates them, it does NOT remove them. Dissolution paths: duplication rows (27) → extract the duplicate blocks into `shared/` helpers (then sync vendored copies — `check_vendored_common.py` guards this); parameter rows (16) → config dataclasses; nloc/CC rows (47) → split or simplify the FUNCTION itself; module-MI rows (2) → file-level decomposition (the only class file splits fix). Every NEW module must clear the coverage gate (baseline `[]`, equality-ratcheted) — tests land in the same batch. Leaf suites + all 10 gates must stay green in the worktree before merge. Duplication re-baseline in the SAME commit as any clone-file edit (pre-flight 6).
- [ ] **4. Ratchet** the selfaudit baseline shrink-only; record before/after counts in the ledger shard.
- [ ] **5. Ship the iteration (C-5 + C-6 iteration ship):** convergence ×2 → fresh-clone sim → push → CI watch. No bump, no reinstall (C-2). When the lane's baseline reaches `[]` — or C-8 ends it — run the C-6 lane-completion ship.

Expected trajectory (record actuals in the ledger shard): the 27 duplication rows and 16 parameter rows are the mechanically reachable bulk; the 47 nloc/CC rows require genuine function-level simplification and may have an honest asymptote above zero — two consecutive zero-shrink iterations end the lane BLOCKED (C-8a), which is a legitimate terminal per the DoD.

## Branch B3 — repo-B lane (wave 9 → 0)

- [ ] **B3.1:** pin the wave hotspot lane to the lane-start anchor (`--rev`, pre-flight 5) and adopt the B1.3 policy: declare the two intentional pairs (`SKILL.md<->references/pipeline.md`, `skill_bootstrap_manifest.json<->tests/test_check_skill_requirements.py`) → 2 temporal rows dissolve, counted. The 3 churn×complexity rows (`check_skill_requirements.py`, `skill_bootstrap_manifest.json`, `tests/test_check_skill_requirements.py`) are NOT policy-suppressible — they dissolve only via B3.2 complexity reduction or window aging at re-anchor. Fixed-first, then ratchet.
- [ ] **B3.2:** refactor the 3 library module-MI rows (helper modules) and the 1 parameter-count row (config-object signature), C-3 recipe with throwaway worktrees and the scoped mutation gate; 101-test suite green throughout. `check_skill_requirements.py` (MI 50.3) is also a churn-row file — its complexity reduction is what gives that churn row a dissolution path.
- [ ] **B3.3 (C-6 lane-completion ship):** also bump repo-B's workflow to `checkout@v5` + `setup-python@v6` (pre-flight 4); re-anchor the hotspot lane and triage any surfaced rows fixed-first; ratchet wave baseline toward `[]`; convergence ×2; ship 0.4.2 (source shipped in B3.2); CI watch verifies zero deprecation annotations. If churn rows survive re-anchor with no honest dissolution path, the lane ends BLOCKED with the residue documented in the ledger shard.

## Branch B4 — repo-P lane (wave 55 → 0)

- [ ] **B4.1 mechanical batch (standalone C-6 iteration ship):** bump `.github/workflows/check.yml` to `actions/checkout@v5` + `actions/setup-python@v6`. Workflow-only change — gates trivially green; push it as its own iteration ship (no bump) precisely so the resulting CI run can be checked for zero deprecation annotations now, not at B4.5.
- [ ] **B4.2 security rows:** adopt the B1.1 trusted-subprocess policy in the wave security lane (17 rows dissolve, counted); fix 3×B105 at source (restructure flagged constants) and 1×B324 (replace weak hash with `hashlib.sha256` or `usedforsecurity=False` where digest identity must be preserved — pick whichever keeps behavior, record which).
- [ ] **B4.3 complexity burn-down loop:** B2's iteration recipe against the benchmark pipeline (20 CC + 12 nloc + 5 MI + 3 params), scoped mutation gate, ≤2 batches per iteration, 154-test suite green throughout — same function-level caveat as B2 step 3: only the 5 MI rows dissolve via file splits; the rest need function-level work.
- [ ] **B4.4 hotspot rows:** pin the lane anchor; declare the three intentional pairs (`README.md<->SKILL.md`, `README.md<->scripts/perf_benchmark_pipeline.py`, `SKILL.md<->scripts/perf_benchmark_pipeline.py`) and `single_maintainer: true` (author row on `perf_benchmark_pipeline.py`) → 4 rows dissolve, counted. The 2 churn×complexity rows (`reporting.py`, `perf_benchmark_pipeline.py`) dissolve only via B4.3 complexity reduction or window aging at re-anchor.
- [ ] **B4.5 (C-6 lane-completion ship):** re-anchor the hotspot lane, triage surfaced rows fixed-first; ratchet wave baseline toward `[]`; convergence ×2; ship 0.3.1. Surviving churn rows with no honest path = lane ends BLOCKED with documented residue.

## Branch B5 — hygiene, purge, final ship (serial, last)

### Task B5.1: stale-skill purge (authorized; allowlist-driven)

- [ ] Deterministic eligibility, no pattern-matching judgment calls. Build two sets from the three family repos: CURRENT = the union of skill names in today's source manifests (repo-A installer list of 16 leaves, `repo-audit-refactor-optimize`, `perf-benchmark`, `perf-optimization`); HISTORICAL = the union of every skill name that has EVER appeared in those manifests or as a `skills/*/SKILL.md` name across the full git history of the three repos (`git log --all --diff-filter=A --name-only`). An installed dir is purge-eligible IFF its name ∈ HISTORICAL and ∉ CURRENT. Anything not in HISTORICAL is foreign (superpowers:*, goal-*, scite-search, ml-*, m10/m15, humanize*, hypothesis-testing, `maintenance`, configure-*, …) and is NEVER touched, no exceptions, no judgment. Write the full eligibility table (installed dir → CURRENT/HISTORICAL membership → decision) to the ledger shard BEFORE removing anything; remove eligible dirs; re-run the bootstrap readback probe; expected exit 0.

### Task B5.2: final reinstall + readback

- [ ] Reinstall all family skills at final versions (node installer for repo-A; directory sync for the rest). Readback: 16 leaves @ final repo-A version, orchestrator @ final repo-B version, perf skills @ final versions; bootstrap probe green.

### Task B5.3: final report + close

- [ ] Merge the three C-9 ledger shards into `docs/self-audit/2026-06-sp11-unattended-loop.md`: iteration table (per-repo baseline trajectory), accepted/discarded batch ledger, suppression-class counts, purge table, ship evidence (SHAs, tags, CI ids, readback). This is the final lane-completion ship: repo-A 0.6.0 per C-2. Verify every DoD row; report DONE if all met, else BLOCKED with the unmet rows and their documented residue — both are valid terminals, neither is silently retried.

## Scheduling

- Group 1: B0.1 → B0.2 → B1 serial (the gate and the delegation proof precede everything; leaf precision must ship and be reinstalled before consumers ratchet against it). B0.3 (read-only census) and B0.4 (workflow-only) run concurrent with B1; B0.4 lands in the B1.4 ship.
- Group 2 (parallel, rolling): B2, B3, B4 — disjoint repos with single-writer discipline: B2 is the ONLY writer of repo-A (including its ledger shard); B3 writes only repo-B; B4 writes only repo-P. B3/B4 consume the leaf behavior frozen at B1.4's reinstall; per C-2 no reinstall happens during Group 2 iterations (lane-completion only), so installed leaves stay stable under all three lanes. B2's repo-A refactors are behavior-preserving, so no contract churn across lanes.
- Group 3 (serial, last): B5 — runs after all Group 2 lanes have terminated (DONE or BLOCKED).
