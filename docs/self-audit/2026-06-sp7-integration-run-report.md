# SP7 Track INT — Integration Run Report

**Date:** 2026-06-11
**Orchestrator:** Opus (Track INT), serial integration on `main`.
**Plan:** `docs/superpowers/plans/2026-06-10-sp7-parallel-skill-tracks.md` (Track INT, contracts C-6/C-7/C-9).
**Scope:** release repo-audit-skills v0.4.0 — six new audit leaves merged in pinned order, SIGNALS schema bump (PERF + SECURITY), gates kept green at every step. **Nothing pushed, tagged, or published — local commits only.**

---

## Pinned order executed

`gate-harden (INT-1, pre-completed) → A1 hotspot → A3 repo-hygiene → A2 dependency → A4 docs-consistency → [schema bump INT-6] → A5 security → A6 test-effectiveness → release (INT-9) → run report (INT-10)`

A5 (security-audit) was confirmed reviewer-accepted at `29cfd52` mid-run; the STOP-GUARD before INT-7 was lifted on that confirmation, and the branch SHA matched the accepted SHA exactly.

## Pre-flight (INT-0) — all green

| Check | Expected | Actual |
|---|---|---|
| `main` clean at `bee4502` (INT-1) | yes | yes |
| `npm install` | ok | ok |
| `npm run check` | green | selfaudit 103==103, coverage 11 suites (count 1 ≤ baseline 2), release pass |
| `python3 -m pytest --collect-only -q` | 464 | 464, zero errors |
| INT-1 gate tests (`tests/test_check_self_audit.py`) | 3 passed | 3 passed (stale-baseline detection active) |
| Leaf branch SHAs | per plan | hotspot `039cec1`, repo-hygiene `aa2d0af`, dependency `0681887`, docs-consistency `53259d8`, test-effectiveness `3720355`, security `29cfd52` — all exact |

State correction applied throughout: INT-1 had already ratcheted the baseline 104 → **103** (dissolving the `check_coverage_gap.py ↔ check_self_audit.py:23-31` ratchet-idiom clone) and main collect-only was **464** (not 461). All later plan "104" references read as 103.

## Per-merge results (each gate run by INT on `main`, real output read — worker "green" never trusted)

Every merge used `git merge --no-ff --no-commit` so the suite/registry edits fold into one merge commit. No merge had a conflict (partition holds). Each leaf's diff touched only `skills/<leaf>/**` (verified pre-merge). A pre-existing unrelated `package-lock.json` version drift (committed `0.1.0` vs `package.json` `0.3.0`) was reverted at each merge to keep commits surgical.

| Step | Commit | Leaf tests | collect-only | Registration | Freeze | check:selfaudit | check:coverage |
|---|---|---|---|---|---|---|---|
| INT-2 A1 hotspot | `6adb8a9` | 30 passed | 464→494 | none (standalone) | 0 | 103==103 | 12 suites |
| INT-3 A3 repo-hygiene | `acc223a` | 18 passed | 494→513 (+18 leaf, +1 umbrella wildcard test) | registry `languages:["*"]` + `select_leaves` wildcard | 1 (`_git` clone) | 104==104 | 13 suites |
| INT-4 A2 dependency | `03d72b1` | 47 passed | 513→560 | registry `languages:["python"]` | 0 | 104==104 | 14 suites |
| INT-5 A4 docs-consistency | `a33fa14` | 25 passed | 560→585 | registry `languages:["python"]` | 1 (module MI) | 105==105 | 15 suites |
| INT-6 schema bump | `5eec479` | — (+1 schema test) | 585→586 | re-vendor 10 copies | 0 (count-neutral swap) | 105==105 | 15 suites |
| INT-7 A5 security | `01e42bc` | 10 passed | 586→596 | none (standalone) + CI bandit pin | 1 (`load_thresholds` clone) | 106==106 | 16 suites |
| INT-8 A6 test-effectiveness | `2036938` | 48 passed | 596→645 (+48 leaf, +1 umbrella skip-test) | registry `requires:{mutation_scope}` + CI mutmut pin | 1 (`build_parser` clone) | 107==107 | 17 suites |
| INT-9 release 0.4.0 | `b24b5ce` | — | 645 | version + check_release + installer + README | 0 | 107==107 | 17 suites |

Full `npm run check` was run and confirmed `NPM_EXIT=0` (real npm exit, not a piped `tail` exit) after every merge.

## Freeze adjudications (target 0; hard cap 10 per leaf; got 4, all individually justified, none blanket)

All four are **intrinsic to the standalone-vendored-leaf architecture** — each leaf is an independently-installable skill with a self-contained `scripts/` dir (only `health_common.py` is shared/vendored). The established precedent (frozen-log sections B/C and round-log R2) is that cross-leaf skeleton clones cannot be deduped without a forbidden cross-skill import, and hoisting shared helpers into `shared/health_common.py` is empirically net-negative (R2: relocates clones into the 6×-vendored module + adds `maintainability_index` findings). Every PREFER-FIX option was considered and rejected on those grounds. Each clone is invisible in any single branch (each branch holds only its own copy) and could only surface at integration.

| INT step | Finding | Kind | Frozen-log home | Baseline |
|---|---|---|---|---|
| INT-3 | `skills/hotspot-audit/scripts/_audit_git.py ↔ skills/repo-hygiene-audit/scripts/_git_utils.py:36-53` | cross-leaf `_git` subprocess wrapper (C-3 skeleton) | section C2 | 103 → 104 |
| INT-5 | module-level `maintainability_index` on `skills/docs-consistency-audit/scripts/docs_consistency_audit.py` (radon MI 23.5 < 65) | single-file-tool MI idiom (the **one documented A4 candidate**) | section D (12th entry) | 104 → 105 |
| INT-7 | `skills/repo-hygiene-audit/scripts/_thresholds.py ↔ skills/security-audit/scripts/_reporting.py:25-33` | cross-leaf `load_thresholds` (C-3 skeleton) | section C2 | 105 → 106 |
| INT-8 | `skills/docs-consistency-audit/scripts/docs_consistency_audit.py ↔ skills/test-effectiveness-audit/scripts/_cli.py:39-50` | cross-leaf `build_parser` CLI skeleton (C-2/C-3 mandated flags) | section C2 | 106 → 107 |

A5's own in-branch freeze candidate (its post-bump `health_common.py` differing from the pre-bump siblings) became **obsolete** at INT-6: once all 10 copies were post-bump, A5's copy was byte-identical (`cmp` confirmed IDENTICAL), so it joined the existing clone group with no new finding.

## Baseline ratchets / swaps (equality gate, INT-1 onward: baseline == snapshot exactly)

- **INT-1 (pre-completed, `bee4502`):** 104 → 103, removing the dissolved `check_coverage_gap.py ↔ check_self_audit.py:23-31` ratchet-idiom clone.
- **INT-3/INT-5/INT-7/INT-8:** +1 each (the four freezes above), via `cp self_audit_snapshot.json self_audit_baseline.json` (canonical sort, minimal +6-line diff each). 103 → 104 → 105 → 106 → 107.
- **INT-6 (count-neutral swap):** the `SIGNALS += PERF, SECURITY` +2-line hunk shifted the single line-pinned vendored-clone entry `shared/health_common.py ↔ skills/complexity-audit/scripts/health_common.py` from `:1-99` to `:1-101`. Exactly 1 stale + 1 new, same pair, **NET ZERO** new findings; stale entry replaced with its shifted twin in the same commit. snapshot 105 == baseline 105.

## One PREFER-FIX (not a freeze)

At INT-6, while documenting the swap, a frozen-log reference to a non-existent path (`scripts/health_common.py`) tripped the newly-registered docs-consistency leaf (`doc_path_missing`, scanning `scripts/self_audit_frozen.md` which is in self-audit scope). **Fixed** by citing an existing example path — no freeze, baseline unchanged. (Lesson recorded: markdown under `scripts/` is in self-audit scope; path tokens there must resolve.)

## Schema bump evidence (INT-6, C-6)

- TDD: `tests/test_health_common.py::test_perf_and_security_signals_in_schema` added — red before the hunk, green after.
- `shared/health_common.py` diff = exactly `+ "PERF"` `+ "SECURITY"` inside the `SIGNALS` frozenset (no other change).
- Re-vendored byte-identical into all **10** existing `skills/*/scripts/health_common.py` copies via a **targeted** loop over existing copies (not the plan's literal `for d in skills/*/scripts` glob, which would wrongly create copies in dirs that have none → new clones). `check:vendored` → pass, 10 copies checked. (A6 forked pre-bump; its 11th copy was re-vendored to post-bump at the INT-8 merge — `cmp` IDENTICAL.)

## CI changes

`.github/workflows/check.yml` pip-install list extended: `+ bandit==1.9.4` (INT-7, security-audit integration tests) and `+ mutmut==3.6.0` (INT-8, test-effectiveness integration tests). Both pinned and verified locally before the gate runs.

## Final numbers (C-9) — each with evidence

| Metric | Target | Actual | Evidence |
|---|---|---|---|
| `package.json` version | 0.4.0 | **0.4.0** | check:release `"version":"0.4.0"` |
| Skill count | 16 | **16** | `node bin/install-repo-audit-skills.js --list` → 16; check:release validates 16 |
| `check_coverage_gap.SUITES` | 17 | **17** | check:coverage `"suites":17` |
| Self-audit baseline == snapshot | equality | **107 == 107** | check:selfaudit `count 107, baseline 107` (zero new, zero stale) |
| Baseline composition | 103 + adjudicated | **103 + 4 freezes = 107** | round log + sections C2/D |
| Coverage-gap baseline | 2 | **2** | check:coverage `"baseline":2` |
| Installer `--list` | 16 @ 0.4.0 | **16 @ 0.4.0** | installer JSON |
| Root collection | 464 + 3(INT-1) + Σ leaf | **645**, zero errors | `pytest --collect-only -q` |
| `npm run check` | green | **NPM_EXIT=0** | release gate run |

**Collection arithmetic:** 464 (post-INT-1 base) + 30 (A1) + 18 (A3) + 47 (A2) + 25 (A4) + 10 (A5) + 48 (A6) = 642 leaf tests; plus 3 plan-mandated integration tests added by INT — the `select_leaves` wildcard umbrella test (INT-3), the `PERF`/`SECURITY` schema test (INT-6), and the `mutation_scope` fail-safe-skip umbrella test (INT-8) = **645**. (The goal's formula `464 + 30+18+47+25+48 + A5(10) = 642` did not count those 3 INT-authored tests; they are required by the plan steps and are accounted for here.)

## Worktree cleanup

Removed the five merged leaf worktrees (branches kept): `../ras-sp7-hotspot-audit`, `../ras-sp7-repo-hygiene-audit`, `../ras-sp7-dependency-audit`, `../ras-sp7-docs-consistency-audit`, `../ras-sp7-test-effectiveness-audit`. All six `sp7/*` leaf branches are preserved for the human.

`../ras-sp7-security-audit` (the A5 orchestrator session's worktree, branch `sp7/security-audit`) is **left intact** — it belongs to the A5 session, was outside this INT session's named "five", and its worker sub-worktrees (`-w1`/`-w2`) were already cleaned by that session. Flagged here for the A5 session / human to remove (`git worktree remove ../ras-sp7-security-audit`; the branch stays).

## Known non-regression (not chased, per plan)

Full unfiltered `python3 -m pytest -q` fails on `test_umbrella_requires.py::test_real_registry_smoke` due to a pre-existing `helpers.py` module-name collision (root pytest collects all leaf `helpers.py` without packages). `npm run check` (per-suite coverage runs) and `--collect-only` do not hit it; gates were collect-only + `npm run check` + named suites.

## Track INT DoD

INT-0..10 complete with evidence; check:selfaudit equality holds (baseline == snapshot, zero stale); v0.4.0 built atomically; nothing pushed, tagged, or published.
