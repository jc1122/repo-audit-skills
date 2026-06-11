# SP9 Production Run — Final Report (K5-T5)

**Date:** 2026-06-11
**Plan:** `2026-06-11-sp9-production-readiness.md` (committed `360f6c4` in repo-B, under its `docs/plans` tree)
**Architecture:** 5 Codex gpt-5.5 orchestrators (K1–K5) + native Spark workers; K5-T4 ship executed by the supervising Claude session after explicit human authorization; every track's claims independently re-verified before acceptance.

## Shipped versions

| Repo | Version | Tag commit | CI |
|---|---|---|---|
| repo-audit-skills | **v0.5.0** (16 skills) | `b442066` | green (push + tag) |
| repo-audit-refactor-optimize | **v0.4.0** | `0146002` | green |
| perf-benchmark-skill | **v0.3.0** + perf-optimization **0.2.0** | `e821681` | green |

GitHub releases published for all three. Installed into the harness skills root (installer for the 16 leaves; rsync for orchestrator + perf skills); readback probe: bootstrap checker exit 0, lanes code-health/coverage/security/hygiene/test = full.

## Per-track results (each independently re-verified)

- **K1 leaf precision** (`sp9/leaf-precision`, 6 commits): docs-consistency `--exclude-prefix` + placeholder/generated-output skip; hotspot solo-author + own-test-pair suppression; quality `format_drift` config-gate; dead-code test-referenced vulture suppression; test-effectiveness clean ToolError on mutmut baseline failure. All suppressions counted in reports, never silent; both-direction regression tests. Verified: 9 gates green, 688 collected.
- **K2 ratchet hardening** (`sp9/ratchet-brevity`, 4 commits): duplication identities migrated to content-hash symbols (28/28, count-neutral 107→107 — line-pin churn eliminated); coverage gate gained stale detection via `gate_common.verdict` and immediately ratcheted its own baseline 1→0 (now `[]`, nothing under-covered); pip-audit advisory runbook; brevity (dependency-audit SKILL 295→85). Verified: 9 gates green, 681 collected.
- **K3 orchestrator completion** (repo-B, 16 commits): bootstrap checker decomposed (D1–D7 real debt cleared); `validate_run_report.py` (schema v2 adds `backlog.wont_fix`); `run_diagnosis_wave.py` (one-command wave); 4-class triage taxonomy + docs-repair playbook; `check_wave_baseline.py` convergence gate seeded at 23. Verified: 100 passed, validator pass, wave 23==23.
- **K4 perf self-audit** (repo-P, 5 commits): absorbed the never-run SP8 P-track — bootstrap probe, diagnosis, fast-tier perf baseline + 2-line ledger, ONE bounded optimization attempt → honest `no_candidates` verdict (third consecutive no-win for `bench_parse_massif`); wave gate seeded; brevity (perf-optimization SKILL 357→109, sample-report 296→54). Verified: 154 passed, wave 59==59, run report v2 valid.
- **K5 integration + convergence**: merged K2-before-K1 (`2661dda`, `06c9f62` — identity migration first, so leaf edits merged without baseline churn), released v0.5.0 (`8fa2d14`), two-run convergence proof: repo-A wave run2 == run3 (2423 raw / 1015 ids, 0 new, 0 stale); repo-B ratchet 23→13 (every `expires: v0.5.0` freeze genuinely dissolved); repo-P 59==59. Stopped at the T4 human gate as designed.

## Convergence demonstrated (plan C-7)

K3/K4 deliberately seeded baselines with the installed 0.4.0 leaves, freezing known false positives as `expires: v0.5.0`. After the v0.5.0 build, every one of those freezes dissolved and was ratcheted away: vulture test-referenced FP, both `format_drift` rows (no declared standard), hotspot solo-author/own-test noise, and the docs output-path refs. The docs lane now reports **0 findings in both repo-B and repo-P**. SP8's measured 53% diagnosis noise in repo-B is structurally eliminated for the targeted FP classes.

## Ship deviation: fresh-clone CI failure (fixed forward)

First push of v0.5.0 (`1bc81a0`) failed CI: `check:selfaudit` found `doc_path_missing` for `scripts/self_audit_frozen.md` → the gitignored self-audit snapshot, referenced by literal path in K5's merge-resolution note (introduced in merge `06c9f62`, invisible to `git log -S` and to every local gate run — snapshots persist on dev machines, not in fresh clones). Root-caused from the CI log, reproduced in a fresh local clone, swept for the whole class (5 literal snapshot tokens across `scripts/self_audit_frozen.md` + 4 runbooks, 3 of which would have failed `check:docs` next), fixed by basename rewording with regression test `tests/test_fresh_clone_doc_tokens.py` (red→green), verified with a full fresh-clone 9-gate run (exit 0, 9 pass), then re-shipped: tag + release deleted and recreated at `b442066` after CI green. Collection: 695.

**Lesson recorded:** local gate green ≠ fresh-clone green when gitignored artifacts can satisfy doc-path checks. The new test locks the invariant; a `--tracked-only` resolution mode for the docs leaf is an SP10 candidate.

## Final numbers (plan C-8 actuals)

| Item | Value |
|---|---|
| repo-A `npm run check` | 9/9 pass — locally, in fresh clone, and in CI |
| Self-audit baseline | 106 (post-merge regeneration; all duplication entries content-hashed) |
| Security / hygiene / docs / dependency baselines | 49 / `[]` / `[]` / `[]` |
| Coverage-gap baseline | `[]` (0 == 0 across 17 suites) |
| repo-A collection | 695, zero errors |
| repo-B suite / wave | 100 passed / 13 == 13 |
| repo-P suite / wave | 154 passed / 59 == 59 |
| Frozen entries | every entry individually justified; zero blanket freezes |
| SKILL.md budgets | all ≤ 160 lines (largest: repo-B SKILL.md 114) |

## Deferred to SP10

Module-MI idiom tuning for compact CLI scripts (7 frozen in repo-B, family-wide pattern); post-v0.5.x decomposition buckets (repo-B 9, repo-P complexity 44); docs-leaf `--tracked-only` resolution; multi-language leaves; opencode bridge unique-port default (bridge unused in SP9).
