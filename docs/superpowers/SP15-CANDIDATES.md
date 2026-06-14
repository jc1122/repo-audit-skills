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
- **Auto-consume the remediation-scope policy in the engine.** SP14 added a durable
  machine-readable remediation-scope policy (excluding intentional `tests/fixtures/`).
  Phase 2 folded that policy into the portable acceptance file under `.repo-audit` as
  remediation-stage `path` entries (the standalone `remediation_excludes.json` was retired),
  but the MPRR engine's `mprr_normalize`/`mprr_partition` step still does not load it — an
  orchestrator has to apply it when building the audit scope. Wiring the engine to self-filter
  excluded paths via the acceptance policy (so intentional residue is never even proposed) is
  the next mechanization step: it converts a per-run judgment into permanent enforced state.
- ~~Duplicate-named test classes in `skills/growth-audit/tests/test_growth_audit.py`~~ **RESOLVED
  (commit `1558303`).** The 8 shadowed classes + 1 function were a rewrite-left-behind: un-shadowed
  and run, 33 methods failed (obsolete API) → deleted; the 2 still-passing gap-closing tests
  (`test_gemfile_entries`, `test_json_entries`, covering `_package_json_dep_entries`) were revived
  into the running class. pytest 50→52, coverage 83→87%. Family-wide scan: no other file affected.
  Standing candidate: an automated check that flags duplicate top-level defs in test files (the
  shadowing is invisible to pytest collection — only ruff F811 caught it).
- **repo-A test-tree dead-code is below the selfaudit scope.** `self_audit.py::_prefixes()`
  audits production code only (`skills/*/scripts`), never `tests/`. SP14 cleaned `tests/`
  unused imports/locals opportunistically, but there is no standing gate keeping test dirs
  clean. Candidate: an optional tests-scoped dead-code ratchet (excluding fixtures).
