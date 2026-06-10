# Frozen self-audit findings (Actionability Rule)

Each entry: path :: leaf/metric :: reason.

## Round log

- **R1** (fix): cleared 15 lint findings in `scripts/self_audit.py`, `scripts/check_self_audit.py`, `scripts/check_release.py` (E401/E702/E501/format_drift). Baseline 191 -> 176. 0 frozen. (A parallel leaf-lint attempt was discarded: line-wrapping the near-identical leaf scripts churns `duplicate_tokens` line-range symbols and pushed `_vulture_findings` over the nloc threshold — a regression.)
