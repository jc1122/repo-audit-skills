# SP7 freeze candidates — docs-consistency-audit

This file tracks findings that may warrant baseline exceptions during
self-audit for SP7. Candidates are added here by the implementation team
after review and before the freeze gate.

## Candidate 1: `maintainability_index` on `<module>` of `skills/docs-consistency-audit/scripts/docs_consistency_audit.py`

- Finding: `{"leaf": "complexity", "metric": "maintainability_index", "path": "skills/docs-consistency-audit/scripts/docs_consistency_audit.py", "symbol": "<module>"}`
- Measured: radon MI 23.5 against the leaf threshold of 65.

Justification: this is the established single-file-tool module-MI freeze
idiom. Every leaf in this family ships one self-contained audit script by
design, and all 14 sibling single-file tools already carry a frozen
module-level `maintainability_index` finding in `scripts/self_audit_baseline.json`
at comparable MI values (24–38, e.g. `structure_audit.py` 24.3,
`complexity_audit.py` 37.6). Radon's module MI is dominated by total
Halstead volume and SLOC, so a ~600-line tool cannot reach MI 65 without
splitting into multiple modules — which would break the self-contained
leaf layout (vendored `health_common.py` plus exactly one script) and was
shown in dogfood round R2 to be a net regression. The SP7 A4 repair
already decomposed every flagged function (post-refactor: 34 functions,
max CC 10, max NLOC 50, max params 5, avg CCN 4.0); the per-function
complexity, duplication, lint, and format findings are all cleared
outright, leaving module MI as the only structural residue.
