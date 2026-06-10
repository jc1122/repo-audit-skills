# Frozen self-audit findings (Actionability Rule)

Each entry: path :: leaf/metric :: reason.

## Round log

- **R1** (fix): cleared 15 lint findings in `scripts/self_audit.py`, `scripts/check_self_audit.py`, `scripts/check_release.py` (E401/E702/E501/format_drift). Baseline 191 -> 176. 0 frozen. (A parallel leaf-lint attempt was discarded: line-wrapping the near-identical leaf scripts churns `duplicate_tokens` line-range symbols and pushed `_vulture_findings` over the nloc threshold — a regression.)
- **R2** (attempted FIX, DISCARDED): hoisting `ToolError`/`rel`/`iter_python_files` into `shared/health_common.py` traded 17 cross-leaf clones for 13 vendored-copy clones + 6 new `maintainability_index` findings (net +2). `health_common.py` is vendored byte-identical into all 5 leaves, so any code placed there is cloned 6×. Conclusion: cross-leaf duplication is intrinsic to the standalone-vendored-leaf architecture — see freeze rationale below.
- **R3** (fix): fixed B904 in the umbrella + wrapped 13 E501 across the six code-health scripts (+ ruff-format polish on structure_audit.py). Baseline 176 -> 162. 0 real regressions (duplication line-range symbols churned, which is expected and absorbed by the ratchet).
