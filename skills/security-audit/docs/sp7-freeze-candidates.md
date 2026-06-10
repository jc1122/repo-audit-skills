# SP7 freeze candidates — security-audit (A5)

This leaf produces **one** self-audit finding that is not in the base-SHA
baseline-104 and that is **genuinely unavoidable in-branch**. It is documented
here per plan C-5 for INT to adjudicate. All other findings the leaf initially
produced (3 boilerplate duplicate-token clones and 1 maintainability-index
finding) were eliminated by restructuring the analyzer into a thin CLI plus
small documented modules; only the one below remains.

## Candidate 1 — vendored post-bump `health_common.py` duplicate-token clone

- **Finding:** `leaf=duplication`, `metric=duplicate_tokens`,
  `path=shared/health_common.py`,
  `symbol=skills/security-audit/scripts/health_common.py:31-101`.
- **Cause:** Per plan C-6 / the A5 in-branch contract, this leaf VENDORS THE
  POST-BUMP `health_common.py` (the base file with `PERF` and `SECURITY`
  appended to `SIGNALS`). Every other leaf vendors the pre-bump file, so the
  ten pre-bump copies are byte-identical and jscpd clusters them into the single
  baseline entry `shared/health_common.py ↔ skills/complexity-audit/scripts/health_common.py:1-99`.
  Security's copy differs by exactly the two-line SIGNALS hunk, so jscpd reports
  it as a *separate* clone of `shared/health_common.py` rather than folding it
  into the existing cluster — hence one new `duplicate_tokens` entry.
- **Why unavoidable:** The post-bump vendoring is mandated (it is also why
  `check:vendored` is expected-red in-branch with exactly this file). The
  duplicated region is the body of `health_common.py`, which must stay
  byte-identical to `shared/health_common.py` except for the SIGNALS hunk; it
  cannot be shortened or restructured.
- **Self-resolving at INT:** When INT lands the schema-bump commit, ALL 16
  leaves' `health_common.py` become byte-identical to the post-bump
  `shared/health_common.py`. They re-cluster into a single baseline clone and
  this extra entry disappears. INT therefore needs **no permanent baseline
  freeze** for it: after re-vendoring + the equality-gate (INT-1), the snapshot
  collapses back to one health_common clone. If INT runs the hardened self-audit
  on this branch *before* re-vendoring the other leaves, freeze only this single
  `duplicate_tokens` entry and ratchet it out in the same commit that makes the
  copies identical.
- **Recommendation:** Transient; no standing freeze. Verified: with a pre-bump
  (identical) `health_common.py` the leaf produces ZERO new self-audit findings,
  confirming this entry is solely an artifact of the mandated post-bump copy.
