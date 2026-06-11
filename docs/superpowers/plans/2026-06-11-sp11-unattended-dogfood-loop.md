# SP11: Unattended Dogfood Loop — burn the baselines to zero

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
>
> **For the SP11 orchestrators:** this plan is the single authority for scope, contracts, and DoD. SP11 runs under the /goal runtime (goal-main-orchestrator → goal-branch-orchestrator); branch prompts derive from this plan via goal-preflight (`docs/superpowers/SP11-GOAL-BRIEF.md`). All orchestrator sessions are Codex gpt-5.5 running UNATTENDED (approvals disabled). Mechanical work is delegated through opencode-worker-bridge (file-backed packets, C-7). A worker's green is NOT evidence — orchestrators re-run every gate themselves and read real output.

**Goal:** run the SP10-proven steady-state dogfood loop unattended and iteratively — probe → wave → triage → mutation-gated batches → ratchet → convergence ×2 → machine ship gate → reinstall + readback — until every ratcheted baseline across repo-A/B/P is zero (each finding fixed at source or config-gated-and-counted), with the machine ship gate replacing SP10's human T6 gate.

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
4. **repo-P CI annotation:** `.github/workflows/check.yml:13-14` pins `actions/checkout@v4` + `actions/setup-python@v5` (Node 20 runtime deprecation). Bump to `actions/checkout@v5` + `actions/setup-python@v6`.
5. **Hotspot semantics:** hotspot rows are git-history-derived and cannot be refactored away. The repo-B/P rows are two classes: temporal coupling among release-metadata files (CHANGELOG/package metadata/SKILL.md move together BY DESIGN of C-2) and single-maintainer author concentration. Both are systematic FP classes for this family → C-1 precision fix in the hotspot leaf (B1.4), never silent suppression.
6. **Binding lessons (SP9/SP10):** fresh-clone sim before ANY push (`git clone <repo> /tmp/x && <gates>`); never trust a piped exit code — grep the gate JSON; merge commits can carry content no branch run saw (`git log -S` needs `-m`); duplication baseline rows are line-pinned — any edit to a clone file makes stale + new rows, so re-baseline in the SAME commit as the edit.
7. **Installed-root reality:** `~/.agents/skills` mixes this family with foreign families (superpowers:*, goal-*, scite-search, ml-*, m10/m15, …). The purge (B5.1) must be allowlist-driven from family source manifests and must never touch non-family dirs.

## Contracts (FROZEN)

- **C-1 precision discipline:** every FP-class fix is config-gated, suppressions are COUNTED in the leaf report (never silent), regression tests cover both directions (FP suppressed; true positive still fires), SKILL.md Limits documents the rule.
- **C-2 versions:** every C-6 ship that contains source changes bumps the shipping repo — repo-A patch-increments 0.5.x per iteration (package.json + all 16 SKILL.mds + check_release expectations + installer + CHANGELOG, every time) and the final DoD ship lands as 0.6.0; repo-B 0.4.x; repo-P 0.3.x. Baseline/docs ratchets alone do not bump.
- **C-3 structural batches:** ≤2 per repo per iteration, hotspot-ranked, single-signal, attempted in a throwaway worktree (`git worktree add /tmp/sp11-attempt-<n>`), merged only if every gate stays green. **Mutation gate:** a module may be decomposed only when test-effectiveness-audit shows kill rate ≥ 80% on the module(s) being touched; below that, first land a unit-suite batch that raises it. Discards are recorded in the ledger, never retried identically.
- **C-4 ratchet discipline:** baselines shrink-only; equality-ratcheted; tracked-docs deltas are fixed-first before any ratchet; any unfixable growth = STOP (C-8).
- **C-5 convergence:** after each iteration's changes, two consecutive identical full runs per touched repo (repo-A: all npm gates + wave; B/P: suite + `check_wave_baseline.py`), zero deltas.
- **C-6 machine ship gate (supersedes SP10's human T6 per the authorization above):** per changed repo, strictly in order — all local gates green → C-5 convergence → fresh-clone simulation green → push main → watch CI to completion → tags + releases if C-2 bumped → reinstall (node installer for repo-A; directory sync for B/perf skills) → installed readback + bootstrap probe green. CI red after a push: ONE bounded fix-forward attempt; a second red on the same lane = STOP.
- **C-7 worker packets (opencode-worker-bridge):** file-backed only — the JSON artifacts under the worker run dir are the source of truth, never chat memory; one goal, ≤2 files, full content inlined when ≤200 lines (else grep-anchored excerpts), the failing test included, exact run command + expected output, ≤8k tokens; TDD. Orchestrators re-run all gates themselves.
- **C-8 termination:** the loop ends when the DoD is met, or STOPs on: (a) two consecutive iterations with zero total baseline shrink across all repos; (b) unfixable baseline growth; (c) a second CI red on one lane; (d) any gate that cannot go green without violating C-1..C-7. STOP = finish the ledger + final report for the completed work; push nothing further.
- **C-9 evidence ledger:** `docs/self-audit/2026-06-sp11-unattended-loop.md` is appended every iteration: baseline counts before/after per repo, batches accepted/discarded with worktree evidence, worker run-dir paths, kill-rate readings, ship evidence (SHAs, CI run ids).

## Definition of Done (falsifiable)

1. repo-A: `npm run check` green with **10** gates (the 9 existing + new `check:pytest`), selfaudit baseline `[]`, security baseline `[]`, docs/dependency/hygiene/coverage `[]`; fresh-clone sim green; CI green at final main; release tagged per C-2.
2. repo-B: wave baseline `[]`; full suite green; CI green; release tagged if source shipped.
3. repo-P: wave baseline `[]`; suite green; CI run completes with **zero** deprecation annotations; release tagged if source shipped.
4. Suppression honesty: every config-gated class (trusted-subprocess, release-coupling, single-maintainer) is counted in leaf report output, covered by both-direction regression tests, and documented in SKILL.md Limits.
5. Installed readback: family skill sets exactly match source manifests (post-purge), at final versions; bootstrap probe exit 0, `restart_required=false`, `stop_before_discovery=false`.
6. The C-9 ledger documents every iteration, every discarded attempt, and the final ship evidence.

---

## Branch B0 — enablement (repo-A, serial; everything else depends on it)

### Task B0.1: full-pytest aggregator gate (surfaces the helpers.py class)

**Files:** Create `scripts/check_full_pytest.py`; Modify `package.json:11` (chain) + `:20` (new script entry).

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
- [ ] **Step 4: Wire into npm:** add `"check:pytest": "python3 scripts/check_full_pytest.py"` and append `&& npm run check:pytest` to the `check` chain. Run `npm run check`; grep the output for 10 gate passes (never trust a piped exit code — pre-flight 6).
- [ ] **Step 5: Commit** `feat(gates): full-pytest aggregator gate (10th gate)`.

### Task B0.2: opencode-worker-bridge smoke (prove the delegation path before unattended use)

- [ ] Dispatch ONE trivial worker packet through opencode-worker-bridge (goal: run `python3 -m pytest skills/complexity-audit/tests -q` and report the tail). Validate per the bridge contract: run dir exists, JSON artifacts present, `run_status` consistent with artifacts. Record the run dir in the ledger. If the bridge cannot produce file-backed evidence, STOP (C-8d) — unattended delegation without evidence is not allowed.

### Task B0.3: mutation-signal census on the three concentration files

- [ ] Run test-effectiveness-audit (sandboxed) against `test-redundancy-triage`, `test-audit-pipeline`, `test-quality-assurance` modules. Record per-module kill rates in the ledger. Modules ≥ 80% are immediately C-3 eligible; modules below get a unit-suite batch first (B2 recipe step 2). No source changes in this task.

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

### Task B1.3: hotspot-audit family-pattern policy (C-1, TDD both directions)

**Files:** Modify `skills/hotspot-audit/scripts/hotspot_audit.py`; Test `skills/hotspot-audit/tests/test_family_policy.py` (new); Modify `skills/hotspot-audit/SKILL.md` (Limits).

- [ ] RED — four tests on synthetic git fixtures: (a) `release_coupling_globs` matching CHANGELOG+metadata files → temporal-coupling finding suppressed AND counted; (b) coupling between two source files still fires under the same config; (c) `single_maintainer: true` → author-concentration suppressed and counted; (d) policy absent → both fire.
- [ ] GREEN — config keys `release_coupling_globs: [...]` and `single_maintainer: bool`, default off, counted suppressions, SKILL.md Limits. Leaf suite green. Commit.

### Task B1.4: ship the precision round (C-6)

- [ ] repo-A version bump per C-2 (0.5.1 → 0.5.2: package.json, 16 SKILL.mds, check_release, installer, CHANGELOG), convergence ×2, fresh-clone sim, push, CI watch, tag + release, reinstall, readback. B2–B4 may only start after this readback is green.

## Branch B2 — repo-A structural burn-down loop (iterative; selfaudit 92 → 0)

Iteration recipe — repeat until the selfaudit baseline is `[]` or C-8 stops the loop:

- [ ] **1. Triage:** rank remaining baseline rows; prefer the concentration files (`triage_redundancy.py` 35, `audit_pipeline.py` 12, `audit_test_quality.py` 12 = 59/92), then duplication clusters, then the long tail.
- [ ] **2. Mutation gate (C-3):** if the target module's kill rate < 80% (B0.3 census or re-run), dispatch a unit-suite worker batch first — tests target exactly the functions about to be extracted/split; re-run test-effectiveness-audit; proceed only at ≥ 80%.
- [ ] **3. Structural batch in a throwaway worktree:** single-signal — split `triage_redundancy.py` by phase responsibility into sibling modules; extract cross-file duplicate token blocks into `shared/` helpers (then sync vendored copies — `check_vendored_common.py` guards this); reduce parameter counts via config dataclasses. All behavior-preserving; leaf suites + all 10 gates must stay green in the worktree before merge. Duplication re-baseline in the SAME commit as any clone-file edit (pre-flight 6).
- [ ] **4. Ratchet** the selfaudit baseline shrink-only; record before/after counts in the ledger.
- [ ] **5. Ship the iteration (C-5 + C-6):** convergence ×2 → fresh-clone sim → push → CI watch → reinstall + readback. Version bumps per C-2 only when source shipped (it did, in any accepted batch).

Expected trajectory (record actuals in the ledger): 92 → ~57 once the three concentration files are decomposed, then a long tail of 33 across leaf scripts. Two consecutive zero-shrink iterations = STOP (C-8a).

## Branch B3 — repo-B lane (wave 9 → 0)

- [ ] **B3.1:** adopt the B1.3 hotspot policy in the wave runner's hotspot lane config (release-coupling + single-maintainer rows dissolve: up to 5 rows). Fixed-first, then ratchet.
- [ ] **B3.2:** refactor the 3 library module-MI rows (helper modules) and the 1 parameter-count row (config-object signature), C-3 recipe with throwaway worktrees and the mutation gate; 101-test suite green throughout.
- [ ] **B3.3:** ratchet wave baseline → `[]`; convergence ×2; C-6 ship (0.4.2 if source shipped — it did in B3.2).

## Branch B4 — repo-P lane (wave 55 → 0)

- [ ] **B4.1 mechanical batch:** bump `.github/workflows/check.yml` to `actions/checkout@v5` + `actions/setup-python@v6`; verify with a CI run showing zero deprecation annotations.
- [ ] **B4.2 security rows:** adopt the B1.1 trusted-subprocess policy in the wave security lane (17 rows dissolve); fix 3×B105 at source (restructure flagged constants) and 1×B324 (replace weak hash with `hashlib.sha256` or `usedforsecurity=False` where digest identity must be preserved — pick whichever keeps behavior, record which).
- [ ] **B4.3 complexity burn-down loop:** B2's iteration recipe against the benchmark pipeline (20 CC + 12 nloc + 5 MI + 3 params), mutation-gated, ≤2 batches per iteration, 154-test suite green throughout.
- [ ] **B4.4 hotspot rows:** B1.3 policy adoption (6 rows).
- [ ] **B4.5:** ratchet wave baseline → `[]`; convergence ×2; C-6 ship (0.3.1).

## Branch B5 — hygiene, purge, final ship (serial, last)

### Task B5.1: stale-skill purge (authorized; allowlist-driven)

- [ ] Build the expected family sets from source manifests only: repo-A installer list (16 leaves), `repo-audit-refactor-optimize`, `perf-benchmark`, `perf-optimization`. Enumerate installed dirs under the resolved skills root. A dir is purge-eligible ONLY if its `SKILL.md` name matches a family naming pattern AND it is absent from every source manifest. Write the eligibility table to the ledger BEFORE removing anything; remove eligible dirs; never touch non-family dirs (superpowers:*, goal-*, scite-search, ml-*, m10/m15, humanize*, hypothesis-testing, …). Re-run the bootstrap readback probe; expected exit 0.

### Task B5.2: final reinstall + readback

- [ ] Reinstall all family skills at final versions (node installer for repo-A; directory sync for the rest). Readback: 16 leaves @ final repo-A version, orchestrator @ final repo-B version, perf skills @ final versions; bootstrap probe green.

### Task B5.3: final report + close

- [ ] Complete `docs/self-audit/2026-06-sp11-unattended-loop.md`: iteration table (per-repo baseline trajectory to 0), accepted/discarded batch ledger, suppression-class counts, purge table, ship evidence (SHAs, tags, CI ids, readback). Commit and push via C-6. Verify every DoD row; any unmet row = the goal is NOT done.

## Scheduling

- Group 1 (serial): B0 → B1 (leaf precision must ship and be reinstalled before consumers ratchet against it).
- Group 2 (parallel, rolling): B2, B3, B4 — disjoint repos; B3/B4 consume only the leaf behavior frozen at B1.4, and B2's later repo-A refactors are behavior-preserving, so no contract churn across lanes.
- Group 3 (serial, last): B5.
