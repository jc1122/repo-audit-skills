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
- _(none yet)_
