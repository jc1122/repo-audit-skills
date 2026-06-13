# SP15 candidate overflow

The SP14 convergence target is **frozen** to the redundancy-lane finding universe
(duplicate-code EXTRACT/MERGE, dead-code DELETE, unused-imports/redefinitions/locals,
redundant-test DELETE/MERGE). Any NEW finding class / lane / metric / engine capability
discovered mid-run is parked here and never folded into the active SP14 run (L-1).

## Deferred by the SP14 spec (§9 non-goals)
- Region/hunk-level and symbol/dependency-level conflict models (wider within-file fan-out;
  file-level is the safe v1).
- Across-repo fan-out (one engine pointed at many repos with a global resource governor).
- Multi-language remediation (SP14 stays Python-oriented).
- Wiring the non-redundancy lanes (complexity / structure / coverage / security / hotspot)
  into the MPRR engine.

## Discovered during SP14 (append as encountered)
- **Auto-consume `scripts/remediation_excludes.json` in the engine.** SP14 added a durable
  machine-readable remediation-scope policy (excluding intentional `tests/fixtures/`), but the
  MPRR engine's `mprr_normalize`/`mprr_partition` step does not yet load it — an orchestrator
  still has to apply it when building the audit scope. Wiring the engine to self-filter
  excluded paths (so intentional residue is never even proposed) is the next mechanization
  step: it converts a per-run judgment into permanent enforced state.
- **Duplicate-named test classes in `growth-audit/tests/test_growth_audit.py`** (8 classes +
  1 function defined twice; the earlier definitions are shadowed/never-run and have *different*
  bodies than their twins — latent test-coverage loss). Deferred-hard from SP14 dead-code
  remediation because auto-deletion would discard differing shadowed scenarios; needs a human
  decision to rename-and-revive vs delete. Worth scanning for family-wide.
- **repo-A test-tree dead-code is below the selfaudit scope.** `self_audit.py::_prefixes()`
  audits production code only (`skills/*/scripts`), never `tests/`. SP14 cleaned `tests/`
  unused imports/locals opportunistically, but there is no standing gate keeping test dirs
  clean. Candidate: an optional tests-scoped dead-code ratchet (excluding fixtures).
