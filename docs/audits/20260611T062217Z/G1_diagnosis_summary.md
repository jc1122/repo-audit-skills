# SP8 Track G — G1 Diagnosis Wave Summary

Run dir: `docs/audits/20260611T062217Z`
HEAD at wave: `3d0af2d` (post-G0 commit). All lanes read-only w.r.t. source; disjoint out-dirs.

## Lane results (orchestrator-verified, real output)

| Lane | Cmd scope | Exit | Result | vs pre-flight row 7 |
|---|---|---|---|---|
| coverage | `check:coverage` | 0 | pass; snapshot **1** < baseline **2** (one-way ratchet); `coverage.json` 284 KB (not committed, C-6) | as expected |
| umbrella code-health | production 18-prefix + `--coverage-json` | 1 | supervisor **ADVISE**, **108** findings (107 self-audit baseline identities + 1 coverage TEST `scripts/self_audit.py` 0%); test-effectiveness skipped (needs mutation_scope) | as expected |
| hotspot | `--rev 3d0af2d --max-commits 500` | 1 | **15** findings (churn_complexity_product / temporal_coupling_ratio / author_concentration) | deterministic |
| security | production 18-prefix, bandit-only | 1 | **64** findings; 50 low / 1 med / 13 high | EXACT match |
| hygiene | full repo, unprefixed | 0 | **0** findings, `"git": true` | EXACT match |
| docs-consistency | C-4 living-docs scope (44 prefixes) | 1 | **18** `doc_path_missing` | EXACT match |
| dependency | production 18-prefix | 0 | **0** findings, `manifest: false` | EXACT match |
| test-effectiveness | top-3 Python hotspot files, 150 mutants each | — | **N/A (tool error)** — see below | honest no-result |

## Hotspot top-3 PRODUCTION Python files (mutation targets + Phase-2 R3 priority)

By `churn_complexity_product` (excluding non-mutatable ratchet artifacts `scripts/self_audit_baseline.json` 7728, `scripts/self_audit_frozen.md` 2730):

1. `skills/code-health-audit-pipeline/scripts/code_health_pipeline.py` (2648) — suite `skills/code-health-audit-pipeline/tests`
2. `scripts/check_release.py` (2028) — suite `tests/`
3. `skills/quality-audit/scripts/quality_audit.py` (1686) — suite `skills/quality-audit/tests`

## test-effectiveness tool error (characterized)

All three runs: leaf raised uncaught `subprocess.CalledProcessError` because `python -m mutmut run`
exits 1. Reproduced for file 1 (estimated mutants 144 < 150 budget — it attempted to run):
mutmut's **baseline collection fails** (`failed to collect stats`) because the owning suite's
subprocess-integration test (`test_code_health_idempotent.py::test_byte_identical_across_runs`,
and analogous tests) shells out to the pipeline and reads `code_health_summary.json`; inside
mutmut's `.mutmut-work/mutants/` sandbox layout that output is never produced →
`FileNotFoundError` → baseline red → mutmut exits 1.

Two SP9-backlog findings (NOT fixed — test-effectiveness is out of G2 scope, and is a budgeted
dogfood tool, not a gate):
- **Robustness:** `_pipeline.py:74` catches `TimeoutExpired` but not `CalledProcessError`; a
  non-green baseline crashes the leaf instead of returning a clean `ToolError`.
- **Inherent:** subprocess-integration suites are incompatible with mutmut's `mutants/` sandbox;
  these targets are not cleanly mutation-testable with their current suites.

Kill-rate signal this round: **N/A**. Phase-2 R3 structural ranking uses hotspot churn alone.

## R1 fix-planning notes (security, from this snapshot)

- **13× hashlib (ALL highs):** `shared/health_common.py:61` (source) + 12 byte-identical vendored
  copies `skills/<leaf>/scripts/health_common.py:61`. INT-6 pattern → fix once in `shared/`
  (`usedforsecurity=False`), re-vendor byte-identical, `check:vendored` green. Clears all 13.
- **1× hardcoded_tmp_directory:** `scripts/check_release.py:140` — adjudicate `/tmp` literal
  (fix → `tempfile.gettempdir()` or freeze if documented default).
- **1× try_except_continue:** `skills/test-quality-assurance/scripts/audit_test_quality.py:123`
  — narrow/justify if ≤5-line diff else freeze.
- **2× hardcoded_password_string:** `skills/test-redundancy-triage/scripts/triage_redundancy.py`
  :2724, :2885 — bandit B105 false positives on literal `'False'` → freeze (justified FP).
- **Residual for per-finding freeze:** 26 subprocess_without_shell_equals_true (B603),
  17 blacklist (B404 `import subprocess`), 4 start_process_with_partial_path (B607) — deliberate
  pinned-tool subprocess wrappers, list-args, no shell. Adjudicated in G4-R1.
