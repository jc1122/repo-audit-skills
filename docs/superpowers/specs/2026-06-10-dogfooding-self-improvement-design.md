# Dogfooding Self-Improvement Run — Design (Sub-project 2)

**Date:** 2026-06-10
**Status:** Approved (pending spec review)
**Predecessor:** Sub-project 1 (integration) — complete; the package is now `repo-audit-skills`
with nine skills.

## Goal

Make `repo-audit-skills` deterministic and hardened, and then have it improve its own code by
running its own pipelines on itself in an Opus-orchestrated, OpenCode-worker loop that iterates
until it converges to a stable fixpoint.

## Context

The merged package contains two pipeline families:
- **code-health** (5 leaves + `code-health-audit-pipeline`): deterministic *output* (sorted,
  hashed findings) but weak *inputs* — floating tool versions (`>=`, `npx --yes jscpd`), no
  subprocess timeouts, unguarded `ast.parse` in `structure-audit`.
- **test-audit** (`test-audit-pipeline` + `test-quality-assurance` + `test-redundancy-triage`):
  already has subprocess timeouts, but leaks wall-clock `datetime.now` and per-stage
  `runtime_ms` (`time.time`) into its outputs, so reruns are not byte-identical. The migrated
  scripts ship no in-repo tests.

## Decisions

1. **Two phases, net-before-loop.** Full self-improvement refactors the package's own code —
   including the audit tools — so the safety net (determinism + characterization tests +
   hardening + self-audit baseline) is built in **Phase 0** before any refactoring. The
   **convergence loop is Phase 1**.
2. **Convergence = fixpoint at ratchet floor.** Stop when a round nets zero safe reductions and
   all gates are green, idempotence holds (two runs byte-identical), and the adversarial corpus
   is clean. The remaining findings are frozen as the final accepted baseline.
3. **Loop scope = full self-improvement, gated by the safety net.** Workers may refactor the
   package's own source to satisfy its own audit (pin versions, add timeouts/guards, segregate
   timestamps, reduce flagged complexity/duplication/dead-code) **only where the change is
   guarded by behavior/golden tests**. This is the **Actionability Rule** (decision 6).
4. **code-health is the loop's primary driver.** The self-audit that drives refactoring is the
   code-health pipeline run over the package's own `skills/ + shared/ + scripts/`.
5. **test-audit runs once as an advisory report**, not in the convergence gate (it needs
   coverage tooling and the migrated skills have no own suites to coverage-run).
6. **Actionability Rule.** A finding is a *work item* only if the file it touches is covered by
   behavior/golden tests that would catch a regression; otherwise it is *frozen into the
   baseline floor*. No safety net → no refactor. (Optional Phase-0 stretch: add characterization
   golden tests for the test-audit scripts to bring them into scope; default is they stay
   frozen.)
7. **No output-contract changes.** A refactor may change a tool's internal structure but must
   never change the findings it emits for a given input. Golden tests enforce this.

## Architecture

### Phase 0 — the harness / safety net (parallelizable mechanical work)

Four independent components; each fans out across workers (per-skill / per-concern).

**C1 — Determinism**
- Pin tool versions: in every code-health leaf `pyproject.toml`, change `>=` to `==` against
  the currently-installed versions. Replace `npx --yes jscpd` in `duplication-audit` with a
  pinned jscpd resolved from a committed lockfile (add `jscpd` to a root `package.json`
  devDependency + `package-lock.json`, invoke the local binary).
- Segregate volatile metadata: in `test-audit-pipeline`/leaves, move `datetime.now` timestamps
  and `runtime_ms` out of the canonical findings/report artifact into a separate `meta` block.
  Verify with a **serialization-level unit test** asserting the canonical artifact contains no
  wall-clock/timing fields (cheap; no full pipeline run, which would need coverage tooling).
- Golden + idempotence tests: for each **code-health** leaf and the umbrella, add a test that
  runs the tool twice on a frozen fixture and asserts byte-identical findings JSON. These are
  the characterization net that makes Phase-1 refactoring safe.

**C2 — Hardening**
- Subprocess timeouts: add an explicit `timeout=` to every `subprocess.run` that lacks one
  (code-health leaves + umbrella), with `TimeoutExpired` mapped to a clean `EXIT_ERROR` (2).
- Guarded parsing: wrap `ast.parse` and file reads (`structure-audit`, and any other `ast`
  user) so `SyntaxError`/`UnicodeDecodeError`/`OSError` skip the file and continue, never
  traceback.
- Adversarial corpus + meta-test: a shared fixture set (syntax-error, empty, non-UTF8/BOM,
  symlink, deeply-nested, file-outside-prefix) and a test asserting every leaf exits in
  {0,1,2} and prints no traceback on each input.

**C3 — Self-audit harness + ratchet gate**
- `scripts/self_audit.py`: runs `code-health-audit-pipeline` over the package's own
  `skills/ + shared/ + scripts/`, writing a normalized findings snapshot.
- `scripts/self_audit_baseline.json`: the accepted floor (initial snapshot).
- `scripts/check_self_audit.py` + `npm run check:selfaudit`: fails if the current snapshot
  contains findings **not present** in the baseline (regressions); never fails on
  baseline-or-fewer. Wired into `npm run check`.

**C4 — test-audit advisory (one-shot)**
- A documented command that runs `test-audit-pipeline` over the package's own tests and writes
  an advisory report. Not gated. Captures test-quality/redundancy signal for humans.

Phase 0 ends when `npm run check` is green including `check:selfaudit`, golden/idempotence and
adversarial meta-tests pass, and the baseline is committed.

### Phase 1 — the convergence loop (orchestrated run)

The Opus orchestrator runs bounded rounds:

```
round:
  1. run scripts/self_audit.py  -> current findings, ranked
  2. select the top-ranked ACTIONABLE findings (Actionability Rule); cap N per round
  3. dispatch one worker per selected finding (own worktree) to fix it structurally
  4. each worker: make the change; run the skill's tests + golden test + `npm run check`;
     a change is ACCEPTED only if every gate stays green and the tool's output contract is
     unchanged (golden test passes). Reject/discard otherwise.
  5. orchestrator merges accepted fixes; re-runs self_audit; ratchets the baseline DOWN to the
     new (smaller) finding set; commits the new baseline.
  6. record net reduction for this round.
```

**Fixpoint / stop conditions:**
- **Converged:** a round produces zero accepted reductions (no actionable finding could be
  safely fixed) AND gates green + idempotence + adversarial clean. Freeze the current baseline
  as final.
- **Bounded:** at most 6 rounds.
- **No-progress / oscillation:** if a round's accepted reduction is zero, or the finding set
  repeats a prior round, stop and report (do not thrash).
- Every round leaves the repo green and committed, so the run is safe to stop at any round.

## Out of scope

- Changing any tool's output contract / finding semantics.
- Refactoring code not covered by behavior/golden tests (frozen into baseline instead).
- Gating on the test-audit pipeline (advisory only this sub-project).
- A unified top orchestrator across both umbrellas.
- Cross-repo work (everything is now one repo).

## Testing & acceptance (Definition of Done)

1. `npm run check` green including `check:vendored`, `check:fixtures`, `check:release`,
   **`check:selfaudit`**; golden/idempotence and adversarial meta-tests pass.
2. **Determinism:** every code-health leaf + umbrella produces byte-identical findings across
   two runs on the frozen corpus; test-audit's canonical artifact carries no wall-clock/timing
   fields (serialization unit test), with volatile metadata confined to a separate `meta`
   block. All tool versions pinned (`==`) and jscpd lockfiled.
3. **Hardening:** every leaf exits in {0,1,2} with no traceback across the full adversarial
   corpus; all `subprocess.run` calls have timeouts.
4. **Convergence:** the loop reached a fixpoint (or the 6-round bound) with a green tree each
   round; the final `self_audit_baseline.json` is committed and `check:selfaudit` is green
   against it. The run reports per-round net reductions and the final accepted-floor finding
   count with justification for what remains.
5. All existing behavior tests still pass; no tool output contract changed (golden tests green).

## Risks

- **Moving-target audit.** Refactoring the audit tools could change their own findings. Mitigated
  by golden/output-contract tests (decision 7) — such a change is rejected.
- **Untested test-audit scripts.** Heavy, untested; the Actionability Rule freezes them rather
  than risk unguarded refactors. Bringing them into scope needs characterization tests first.
- **Version pinning vs. environment.** Pin against installed versions; record them. A CI with
  different versions must install the pinned set or the determinism gate will (correctly) flag.
- **Loop cost/runaway.** Bounded rounds + no-progress stop + per-round cap prevent thrash and
  unbounded spend.
