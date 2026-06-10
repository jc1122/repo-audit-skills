# Dogfooding Self-Improvement Run — Design (Sub-project 2)

**Date:** 2026-06-10
**Status:** Approved; **Revision 1** (post dry-run) folds in three blockers found by previewing
the self-audit on the package itself.
**Predecessor:** Sub-project 1 (integration) — complete; the package is now `repo-audit-skills`
with nine skills.

## Goal

Make `repo-audit-skills` deterministic and hardened, and then have it improve its own code by
running its own pipeline on itself in an Opus-orchestrated, OpenCode-worker loop that iterates
until it converges to a stable fixpoint.

## Dry-run evidence (why Revision 1 exists)

Running the code-health pipeline over the package's own source produced **611 findings**, which
exposed three problems the original design missed:
- **128 findings were on `tests/` fixtures** — the deliberately-dirty code the auditors test
  *against*, which must never be "fixed."
- **Findings carried mixed absolute/relative paths** (the same file appeared as both
  `/home/jakub/.../x.py` and `skills/.../x.py`): the `quality` and `dead-code` leaves leak
  absolute paths from `ruff`. Absolute paths make any baseline machine-specific and break dedupe.
- **~400 of the production findings are `quality` LINT/FORMAT/TYPE** — mostly bulk-auto-fixable,
  far more than a 4-fix-per-round loop could ever converge.

## Context

- **code-health** (5 leaves + `code-health-audit-pipeline`): deterministic *ordering* but two
  determinism leaks — floating tool versions (`>=`, `npx --yes jscpd`) and absolute finding
  paths (above) — plus no subprocess timeouts and unguarded `ast.parse` in `structure-audit`.
- **test-audit** (`test-audit-pipeline` + leaves): has timeouts already, but leaks
  `datetime.now`/`runtime_ms` into outputs. Ships no in-repo tests.

## Decisions

1. **Two phases, net-before-loop.** Full self-improvement refactors the package's own code —
   including the audit tools — so the safety net is built in **Phase 0** before any refactoring.
   The **convergence loop is Phase 1**.
2. **Convergence = fixpoint at ratchet floor.** The actionable set is driven to empty: every
   actionable finding is either fixed or explicitly frozen-with-justification (decision 10).
3. **Loop scope = full self-improvement, gated by the safety net**, only where a change is
   guarded by behavior/golden tests — the **Actionability Rule** (decision 7).
4. **code-health is the loop's primary driver** (self-audit over the package's own production
   code).
5. **test-audit runs once as an advisory report**, not in the convergence gate.
6. **No output-contract changes.** A refactor may change a tool's internal structure but never
   the findings it emits for a given input. Golden tests enforce this.
7. **Actionability Rule.** A finding is a *work item* only if the file it touches is covered by
   behavior/golden tests; otherwise it is *frozen into the baseline floor* with a justification.
   (The untested test-audit scripts are audited and tracked but never refactored.)
8. **Path normalization (NEW).** Every leaf must emit finding paths **relative to `--root`**.
   Fix the `quality` and `dead-code` leaves' absolute-path leaks so baselines are
   machine-portable and dedupe works. This is a determinism prerequisite for the baseline.
9. **Production-scoped self-audit (NEW).** `self_audit.py` audits only production code by passing
   explicit `--source-prefix` values — each skill's `scripts/` dir, plus `shared` and `scripts` —
   so `tests/` and fixtures are excluded. (It does not rely on the leaves' currently no-op
   `--exclude` flag.)
10. **Bulk-remediate, then triage-to-floor (NEW).** A Phase-0 **bulk pass** (`ruff check --fix` +
    `ruff format` over production scripts) clears the auto-fixable LINT/FORMAT majority *before*
    the baseline is frozen. Phase 1 then handles the residual: **each round, every selected
    finding is either FIXED or FROZEN-WITH-JUSTIFICATION** (logged in `scripts/self_audit_frozen.md`),
    so the actionable set strictly shrinks. Caps: up to **8 findings/round**, up to **8 rounds**.

## Architecture

### Phase 0 — the safety net

**C1 — Determinism**
- Pin tool versions (`==`) in every code-health leaf `pyproject.toml`; replace `npx --yes jscpd`
  with a pinned, lockfiled jscpd invoked from `node_modules/.bin`.
- **Normalize finding paths to be relative to `--root`** in the `quality` and `dead-code` leaves
  (the absolute-path leak). The other three leaves already do this.
- Segregate `test-audit`'s `datetime.now`/`runtime_ms` into a `meta` block; verify with a
  serialization unit test asserting the canonical artifact carries no wall-clock/timing fields.
- Per-tool **golden/idempotence tests**: run each code-health tool twice on a frozen fixture,
  assert byte-identical findings JSON.

**C2 — Hardening**
- Subprocess `timeout=` on every `subprocess.run` that lacks one (code-health leaves + umbrella),
  mapped to a clean `EXIT_ERROR`.
- Guard `ast.parse` and reads so `SyntaxError`/`UnicodeDecodeError`/`OSError` skip the file,
  never traceback.
- Adversarial fixture corpus + a meta-test asserting every leaf exits in {0,1,2} with no
  traceback.

**C3 — Self-audit harness + ratchet gate (production-scoped)**
- `scripts/self_audit.py`: runs `code-health-audit-pipeline` over the package's **production**
  code via explicit per-skill `scripts/` prefixes + `shared` + `scripts` (tests/fixtures
  excluded), writing a normalized snapshot.
- `scripts/self_audit_baseline.json`: the accepted floor (frozen **after** C5 bulk remediation).
- `scripts/check_self_audit.py` + `npm run check:selfaudit`: fails on findings not in the
  baseline (regressions); wired into `npm run check`.

**C4 — test-audit advisory (one-shot, not gated).**

**C5 — Bulk remediation (NEW).** Before freezing the baseline: run `ruff check --fix` and
`ruff format` over the production scripts (and `shared/health_common.py`, re-vendored identically
to all five leaves), keeping every test + golden test green. This clears the auto-fixable
LINT/FORMAT majority so the baseline reflects only the residual.

Phase 0 ends when `npm run check` is green including `check:selfaudit`, golden/idempotence and
adversarial tests pass, bulk remediation is committed, and the baseline is frozen.

### Phase 1 — the convergence loop

Bounded rounds the orchestrator drives:

```
round (cap 8 findings):
  1. run scripts/self_audit.py -> current findings, ranked
  2. select up to 8 top-ranked ACTIONABLE findings (Actionability Rule)
  3. one worker per finding (own worktree): EITHER
       FIX it structurally (no output-contract change), OR
       FREEZE it with a one-line justification appended to scripts/self_audit_frozen.md
  4. ACCEPT a worker's result only if `npm run check` is green AND the affected skill's full
     pytest suite (incl. idempotence/golden) passes AND the tool's findings on its fixtures are
     unchanged. Otherwise discard.
  5. merge accepted results; re-run self_audit; ratchet the baseline to the new set; commit.
  6. record net change (fixed + frozen) for this round.
```

**Fixpoint / stop:**
- **Converged:** the actionable set is empty — every finding is fixed or justified-frozen.
- **Bounded:** at most 8 rounds.
- **No-progress / oscillation:** a round that neither fixes nor freezes any finding, or a
  repeated finding set, stops the run with a report.
- Every round ends green and committed.

## Out of scope

Changing any tool's output contract; refactoring untested code (frozen instead); gating on the
test-audit pipeline; a unified top orchestrator; cross-repo work; fixing the leaves' `--exclude`
no-op (self-audit uses explicit prefixes instead).

## Testing & acceptance (Definition of Done)

1. `npm run check` green incl. `check:selfaudit`; golden/idempotence, adversarial, and timeout
   tests pass.
2. **Determinism:** every code-health leaf + umbrella byte-identical across two runs; **all
   finding paths relative to `--root`** (no absolute paths in any leaf's output); test-audit
   canonical artifact free of wall-clock/timing; tool versions pinned `==`; jscpd lockfiled.
3. **Hardening:** every leaf exits in {0,1,2} with no traceback across the adversarial corpus;
   all `subprocess.run` calls carry timeouts.
4. **Self-audit scoped to production:** `self_audit.py` reports zero findings on `tests/`
   fixtures; bulk remediation committed; baseline frozen post-bulk.
5. **Convergence:** the loop reached an empty actionable set (every finding fixed or
   justified-frozen) or the 8-round bound, green and committed each round; final
   `self_audit_baseline.json` + `self_audit_frozen.md` committed; a run report with per-round
   net change and a justification for each frozen finding.

## Risks

- **Moving-target audit** — refactoring the tools could change their findings; rejected by
  golden/output-contract tests.
- **Over-freezing** — a lazy worker could freeze rather than fix; mitigated by "prefer fix; freeze
  only with a concrete reason" and the orchestrator reviewing `self_audit_frozen.md` entries.
- **Gate cost** — `check:selfaudit` runs the full pipeline each `npm run check`; acceptable, but
  the heaviest gate.
- **Version pinning vs. environment** — pins are against installed versions; a different CI must
  install the pinned set or the determinism gate will (correctly) flag.
