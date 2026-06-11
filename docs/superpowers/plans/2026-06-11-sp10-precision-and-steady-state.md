# SP10: Precision Round + Steady-State Dogfood — single orchestrator, worker pool

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
>
> **For the SP10 orchestrator:** this plan is the single authority. ONE Codex gpt-5.5 session owns all three repos SERIALLY — no concurrent tracks, no shared-write risk. Coordinate ONLY for code work: workers = native Codex Spark subagents (100k context; packets per C-7). A worker's green is NOT evidence — re-run every gate yourself and read real output. Commit per task. NOTHING is pushed before T6's explicit human authorization.

**Goal:** the last two systematic false-positive classes die at the leaf level (filesystem-vs-tracked doc resolution; module-MI on CLI entrypoints), repo-A ships v0.5.1, and the **steady-state single-agent dogfood loop** runs end-to-end on all three repos — probe → wave → triage → worker batches → ratchet → convergence ×2 → human-gated ship. This is the maintenance workflow the family will use from now on; SP10 proves it.

**Architecture:** single orchestrator session, Spark worker pool cap 4 (mechanical batches only), serial phases T0→T6. Structural attempts are made in throwaway worktrees so a discard never touches main.

**Repos (verified 2026-06-11, post-SP9 ship):**
- repo-A `/home/jakub/projects/repo-audit-skills` — main `1eaa8c1`, tag v0.5.0 @ `b442066`, CI green ×3; 9 gates green (local + fresh clone + CI); baselines: selfaudit **106**, security 49, hygiene/docs/dependency `[]`, coverage `[]` (0==0, 17 suites); collect-only 695.
- repo-B `/home/jakub/projects/repo-audit-refactor-optimize` — main `0146002`, v0.4.0, CI green; 100 passed; wave baseline **13** = 7 module-MI + 1 param_count + 5 hotspot.
- repo-P `/home/jakub/projects/perf-benchmark-skill` — main `e821681`, v0.3.0, CI green; 154 passed; wave baseline **59 ids / 74 raw** (complexity 44 — of which module-MI 9 — security, hotspot).
- Installed `~/.claude/skills`: 16 leaves @ 0.5.0, orchestrator 0.4.0, perf-benchmark 0.3.0, perf-optimization 0.2.0; readback probe green.

## Out of scope (SP11 candidates, do not start)
Multi-language leaves; second perf benchmark target (3 consecutive honest no-wins on `bench_parse_massif` — surface exhausted); per-file unit suites to unlock mutation signal on repo-A hotspots; stale-skill purge (needs separate authorization); opencode bridge changes (unused here).

---

## Empirical pre-flight (verified 2026-06-11; re-verify rows 1–3 before editing)

1. **Docs leaf resolution point:** `skills/docs-consistency-audit/scripts/docs_consistency_audit.py:319` — `if not (root_path / span).exists():` inside `_check_dead_paths` (placeholder skip at :304, `_PLACEHOLDER` at :35). Filesystem resolution accepts gitignored artifacts → the SP9 ship failure class (local green / fresh-clone red). `tests/test_fresh_clone_doc_tokens.py` guards repo-A's own docs only; the leaf fix kills the class for every repo.
2. **Complexity leaf MI point:** `skills/complexity-audit/scripts/complexity_audit.py:127` `_radon_mi_findings`; emits SIMPLIFY/`maintainability_index`/`<module>` when `mi < thresholds["mi_low"]` (severity via `mi_medium`); `DEFAULT_THRESHOLDS` at :18, `load_thresholds` at :206.
3. **Entrypoint census (`grep -c '__main__'`):** repo-B: check_skill_requirements/check_release/run_diagnosis_wave/validate_run_report = 1 each; _bootstrap_report/_lane_resolve/_skill_probe = 0. Known MI values: check_skill_requirements 50.3; repo-A `docs_consistency_audit.py` 23.5 (the SP7 INT-5 freeze inside the 106 baseline).
4. **Expected baseline shrink (record actuals in T5):** repo-A selfaudit 106→105 (INT-5 MI freeze dissolves); repo-B wave 13→≈9 (4 CLI module-MI dissolve if MI ≥ floor; 3 library-module MI + 1 param stay — they are real debt, not FPs); repo-P: up to 9 module-MI candidates among 44 (entrypoint share unknown — record).
5. **Tracked-only risk:** repo-B/P docs lanes are currently 0 findings under filesystem resolution; tracked-only may surface refs to untracked-but-present files. These are environment-dependent by definition: FIX (basename/placeholder rewording per the SP9 pattern), never freeze.
6. **SP9 ship lessons (binding):** fresh-clone sim before ANY push (`git clone <repo> /tmp/x && <gates>`); merge commits can carry content no branch run saw; `git log -S` misses merge commits without `-m`; never trust a piped exit code — grep the gate JSON.

## Contracts (FROZEN)

- **C-1 precision discipline:** each fix is config-gated, suppressions are COUNTED in the leaf report (never silent), regression tests cover both directions (FP suppressed; true positive still fires), SKILL.md Limits documents the rule.
- **C-2 versions:** repo-A → **v0.5.1** (package.json + all 16 SKILL.mds + check_release expectations + installer + CHANGELOG). repo-B → 0.4.1 and repo-P → 0.3.1 ONLY if T5 lands source changes there (baseline/docs ratchets alone do not bump).
- **C-3 bounded structural remediation (T5):** ≤2 structural batches per repo, hotspot-ranked, single-signal, attempted in a throwaway worktree (`git worktree add /tmp/sp10-attempt-<n>`), merged only if every gate stays green — otherwise discarded with the attempt recorded (the SP4-R3 evidence ledger continues).
- **C-4 ratchet discipline:** baselines shrink-only after T3; tracked-only docs deltas are fixed-first BEFORE any ratchet; any unfixable growth = STOP and report.
- **C-5 convergence:** after all T5 changes, two consecutive identical full runs per repo (repo-A: 9 gates + wave; B/P: suite + `check_wave_baseline.py`), zero deltas.
- **C-6 ship gate (T6):** fresh-clone sim per changed repo, then STOP for explicit human authorization; push + tags + releases + CI watch + reinstall + readback only after it.
- **C-7 worker packets:** one goal, ≤2 files, full content inlined when ≤200 lines (else grep-anchored excerpts), the failing test included, exact run command + expected output, ≤8k tokens. TDD; orchestrator re-runs gates itself.

---

## Task T0 — pre-flight evidence
- [ ] Verify the three SHAs/versions/suites/baseline counts above + installed versions; `npm run check` → 9 pass (grep the gate JSON). Any drift: record, proceed only if gates green. Commit nothing yet (plan is already committed).

## Task T1 — docs-consistency: tracked-path resolution (default in git repos)
**Files:** Modify `skills/docs-consistency-audit/scripts/docs_consistency_audit.py` (`_check_dead_paths` around :319; `build_parser`); Test `skills/docs-consistency-audit/tests/test_tracked_only.py` (new).
- [ ] RED — five in-process tests on tmp fixture repos (use `git init` + commit in fixtures): (a) tracked md referencing an UNTRACKED-but-present file → `doc_path_missing` fires (new default); (b) same fixture with `--filesystem-paths` → no finding; (c) reference to a tracked file → no finding in either mode; (d) directory token `pkg/` with tracked `pkg/x.py` → resolves; (e) non-git fixture root → filesystem fallback, untracked-present file resolves, report notes the fallback.
- [ ] GREEN — kernel:
```python
def _tracked_paths(root: Path) -> set[str] | None:
    proc = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return None
    return {p for p in proc.stdout.split("\0") if p}

def _resolves(span: str, root_path: Path, tracked: set[str] | None) -> bool:
    if tracked is None:
        return (root_path / span).exists()
    clean = span.rstrip("/")
    return clean in tracked or any(t.startswith(clean + "/") for t in tracked)
```
`_tracked_paths` computed ONCE per run; `--filesystem-paths` flag forces `tracked=None`; report gains `"path_resolution": "tracked" | "filesystem"`. Placeholder + generated-output skips unchanged and checked first.
- [ ] SKILL.md: flag + Limits ("docs must reference tracked reality; generated artifacts by basename or placeholder"). Gates: leaf suite green from root and leaf dir; `npm run check` green (all repo-A doc tokens are tracked — expect zero churn); collect-only zero errors.
- [ ] Commit: `feat(docs-consistency-audit): tracked-path resolution by default in git repos (SP10 T1)`.

## Task T2 — complexity-audit: entrypoint module-MI relaxation
**Files:** Modify `skills/complexity-audit/scripts/complexity_audit.py` (`DEFAULT_THRESHOLDS` :18, `_radon_mi_findings` :127); Test `skills/complexity-audit/tests/test_entrypoint_mi.py` (new; clone the suite's existing radon-stub pattern).
- [ ] RED — four tests: entrypoint module with floor ≤ MI < `mi_low` → suppressed + counter `entrypoint_mi_relaxed: 1`; entrypoint with MI < floor → still fires; library module (no `__main__` guard) with MI < `mi_low` → fires; config `{"mi_entrypoint_low": null}` disables relaxation entirely.
- [ ] GREEN — kernel:
```python
_MAIN_GUARD = re.compile(r"^if __name__ ==", re.M)

def _is_entrypoint(path: Path) -> bool:
    try:
        return bool(_MAIN_GUARD.search(path.read_text(encoding="utf-8", errors="replace")))
    except OSError:
        return False
```
In the `_radon_mi_findings` loop: when the file is an entrypoint and `thresholds.get("mi_entrypoint_low")` is not None, suppress (and count) findings with `mi >= mi_entrypoint_low`. `DEFAULT_THRESHOLDS["mi_entrypoint_low"] = 20`. Counter rendered in the leaf report. Rationale documented in SKILL.md Limits: a standalone CLI's module MI is dominated by deliberate self-containment (the vendored-leaf architecture forbids decomposition-by-import); function-level lizard checks remain the actionable signal; MI < 20 still fires.
- [ ] Gates: leaf suite, `npm run check` green, collect-only. Commit: `feat(complexity-audit): relax module-MI for CLI entrypoints, floor 20 (SP10 T2)`.

## Task T3 — repo-A ratchet
- [ ] `npm run check` → `check:selfaudit` fails STALE (the `docs_consistency_audit.py` module-MI freeze dissolves; possibly others). Ratchet `scripts/self_audit_baseline.json` 106→105±, same commit; round-log note in `scripts/self_audit_frozen.md` (basename forms only — the fresh-clone guard test is watching). Re-run → 9 pass.
- [ ] Commit: `ratchet(selfaudit): entrypoint-MI relaxation dissolves INT-5 freeze (SP10 T3)`.

## Task T4 — release v0.5.1 (no push)
- [ ] Bump package.json + 16 SKILL.mds to 0.5.1; check_release + installer expectations; CHANGELOG (tracked-path resolution; entrypoint-MI relaxation). `npm run check` 9 pass; installer `--list` → 16 @ 0.5.1.
- [ ] **Fresh-clone sim (C-6):** `git clone . /tmp/sp10-ci-sim && cp -r node_modules /tmp/sp10-ci-sim/ && (cd /tmp/sp10-ci-sim && npm run check)` → exit 0, 9 pass.
- [ ] Commit: `release: v0.5.1 — tracked-path docs resolution + entrypoint-MI relaxation (SP10)`.

## Task T5 — steady-state dogfood loop (serial: repo-A, then repo-B, then repo-P)
Environment for every wave: `SKILLS_ROOT=/home/jakub/projects/repo-audit-skills/skills` (the v0.5.1 checkout), `WAVE_RUNNER=/home/jakub/projects/repo-audit-refactor-optimize/scripts/run_diagnosis_wave.py`. One `RUN=docs/audits/$(date -u +%Y%m%dT%H%M%SZ)` per repo.
- [ ] Per repo: bootstrap probe (`check_skill_requirements.py --repo <repo> --out-dir <repo>/$RUN --extra-root ~/.claude/skills`) → diagnosis wave → 4-class triage backlog with playbook rule per row → **mechanical batches** via Spark workers (suite green after EACH batch) → **≤2 structural batches** per C-3 from the decomposition bucket (repo-B candidates: the `_bootstrap_report`/`_lane_resolve`/`_skill_probe` library-module MI entries; repo-P: top hotspot complexity files) → ratchet wave/selfaudit baselines shrink-only per C-4 (expected: repo-B 13→≈9, repo-P module-MI share dissolves; tracked-only docs deltas fixed-first) → run report v2 at `$RUN/run_report.{json,md}`, `validate_run_report.py --schema 2` pass.
- [ ] Versions: repo-B → 0.4.1 / repo-P → 0.3.1 iff source changed (C-2), with CHANGELOG entries.
- [ ] **Convergence (C-5):** run everything a second time per repo → zero deltas, or STOP.
- [ ] Commit per step, per repo.

## Task T6 — SHIP (human-gated) + final report
- [ ] Fresh-clone sims for every repo being pushed (repo-A: 9 gates; B/P: suite + wave gate with SKILLS_ROOT pointing at the repo-A clone's `skills/`).
- [ ] Present the actuals table (baseline shrinks, suite counts, convergence outputs) and **STOP for explicit human authorization**.
- [ ] On authorization: push mains; tag + GitHub release v0.5.1 (and 0.4.1/0.3.1 if bumped); watch CI green on all pushed repos; reinstall (repo-A installer `--dest ~/.claude/skills --force`; B/P rsync mirroring the SP9 pattern); readback: installer `--list` 16 @ 0.5.1 + bootstrap probe exit 0.
- [ ] Final report `docs/self-audit/2026-06-sp10-steady-state-run.md` (basename forms for any gitignored artifact mentions): per-task evidence, expected-vs-actual shrink table, structural batch ledger (incl. discarded attempts), convergence outputs, ship record. Commit + push (within the same authorization).

## Definition of Done
1. Both FP classes fixed at the leaf with counted suppression + both-direction tests (C-1); v0.5.1 shipped, CI green, reinstalled, readback green.
2. Baseline shrinks recorded: selfaudit 106→105±, repo-B wave 13→actual, repo-P wave 59→actual — every dissolved entry a ratchet, zero new freezes.
3. Steady-state loop exercised end-to-end on all three repos by ONE session: probe, wave, triage, worker batches, ≤2 structural batches/repo, convergence ×2, v2 run reports validator-green.
4. Fresh-clone sims green before every push; nothing pushed without explicit in-session human authorization; stale purge untouched.

---

# Launch block (paste into ONE fresh Codex gpt-5.5 session)

```
You are the ORCHESTRATOR (Codex gpt-5.5) for SP10 — precision round + steady-state dogfood across
/home/jakub/projects/{repo-audit-skills,repo-audit-refactor-optimize,perf-benchmark-skill}, which you
own SERIALLY (no other sessions; work one repo at a time). Coordinate ONLY for code work: workers =
native Codex Spark subagents, cap 4, packets per plan C-7 (one goal, <=2 files, content inlined,
failing test included, <=8k tokens). A worker's green is NOT evidence — re-run every gate yourself
and read real output; never trust a piped exit code, grep the gate JSON.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-11-sp10-precision-and-steady-state.md
— pre-flight rows 1-6, Contracts C-1..C-7, Tasks T0-T6.

PRE-FLIGHT (failure -> STOP): repo-A main clean at the SP10 plan commit (docs-only on top of
1eaa8c1 — record the actual SHA; anything further, proceed only if gates green), npm run check -> 9
passes, collect-only 695;
repo-B 0146002 clean, pytest tests/ -> 100 passed; repo-P e821681 clean, pytest -> 154 passed;
~/.claude/skills has 16 leaves @ 0.5.0.

ORDER: T1 docs-consistency tracked-path resolution (default in git repos, --filesystem-paths opt-out,
path_resolution noted in report; kernel + 5 tests in plan) -> T2 complexity-audit entrypoint module-MI
relaxation (mi_entrypoint_low default 20, None disables, entrypoint_mi_relaxed counter; kernel + 4
tests in plan) -> T3 repo-A selfaudit ratchet (INT-5 MI freeze dissolves, 106->105±, same-commit,
basename forms only in frozen-log notes) -> T4 release v0.5.1 (16 SKILL.mds + package.json +
check_release + installer + CHANGELOG; MANDATORY fresh-clone sim: git clone . /tmp/sp10-ci-sim, copy
node_modules, npm run check -> 9 passes) -> T5 steady-state loop per repo (A then B then P; one RUN
dir each; SKILLS_ROOT=/home/jakub/projects/repo-audit-skills/skills WAVE_RUNNER=/home/jakub/projects/
repo-audit-refactor-optimize/scripts/run_diagnosis_wave.py): probe -> wave -> 4-class triage with
playbook citations -> mechanical worker batches (suite green after EACH) -> <=2 structural batches per
repo in THROWAWAY worktrees, merged only if all gates stay green else discarded with the attempt
recorded -> ratchet baselines SHRINK-ONLY (tracked-only docs deltas are FIXED first, basename/
placeholder rewording, never frozen; unfixable growth = STOP) -> run report v2 validator-green ->
convergence: second identical run, zero deltas -> bump repo-B 0.4.1 / repo-P 0.3.1 ONLY if source
changed -> T6 SHIP: fresh-clone sims for every repo to be pushed, present the actuals table, then
STOP for EXPLICIT human authorization; only after it: push mains, tag+release v0.5.1 (+0.4.1/0.3.1 if
bumped), watch CI green, reinstall (repo-A installer --dest ~/.claude/skills --force; B/P rsync),
readback probe, final report docs/self-audit/2026-06-sp10-steady-state-run.md.

HARD RULES: every suppression counted in the leaf report, never silent; both-direction regression
tests for each precision fix; baselines shrink-only; commit per task; NOTHING pushed/tagged/released/
reinstalled before the human authorizes at T6; stale-skill purge is OUT OF SCOPE. Final report:
expected-vs-actual shrink table (selfaudit 106->?, repo-B wave 13->?, repo-P wave 59->?), structural
batch ledger incl. discards, convergence outputs, ship record.
```
