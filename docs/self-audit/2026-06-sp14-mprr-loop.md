# SP14 — Massively-Parallel Redundancy Remediation (MPRR) — run ledger

Orchestrator: Claude Opus 4.8 (unattended). Authority: the SP14 plan + spec under
`docs/superpowers/`. This ledger is truth; numbers in the launch prompt are stale hints.

## Entry verification (2026-06-13)

- repo-A `~/projects/repo-audit-skills` @ `02258e0` — clean, CI green (run 27464405757).
- repo-B `~/projects/repo-audit-refactor-optimize` @ `8f27083` — clean, CI green (run 27463637135).
- repo-P `~/projects/perf-benchmark-skill` @ `ac58303` — clean, CI green (run 27460830633).
- Install root: `~/.claude/skills` → `~/.agents/skills` (symlink confirmed).
- Stale `/tmp/sp13` pruned; no live worktrees besides the three mains.
- Phase-A engine worktree: `/tmp/sp14/repo-B-phaseA-engine` on branch `sp14/mprr-engine` (from `8f27083`).

---

## Phase A — build + ship the MPRR engine (repo-B)

Method: `superpowers:subagent-driven-development` — one fresh worker per plan task,
strict TDD, two-stage review (spec compliance → code quality) between tasks. The
orchestrator re-runs every gate itself; a worker's self-reported green is never evidence.

### Task batch log (engine branch `sp14/mprr-engine`, worktree `/tmp/sp14/repo-B-phaseA-engine`)

All implementer + reviewer roles ran as native Opus subagents (sonnet). Every gate
below was **re-run by the orchestrator** (a worker's self-reported green is not evidence).

| Task | Module | Commit | Orchestrator-re-run gate | Review |
|---|---|---|---|---|
| 1 | `mprr_normalize` | `fbf36f0` | `test_mprr_normalize` 6 passed | ✅ spec+quality |
| 2 | `mprr_partition` | `5e93694` | `test_mprr_partition` 4 passed | ✅ (combined w/3) |
| 3 | `mprr_schedule` | `a1aadb0` | `test_mprr_schedule` 4 passed incl. **200-example invariant+liveness** (DoD #1) | ✅ invariant structurally proven |
| 4 | `mprr_gate` | `52de5ed` | `test_mprr_gate` 4 passed; fail-closed on missing keys | ✅ (combined w/5,6) |
| 5 | `mprr_integrate` | `63dba3e` | `test_mprr_integrate` 4 passed (merge-clean + conflict→`InvariantViolation`) | ✅ |
| 6 | `mprr_packets` | `8f3e41d` | `test_mprr_packets` 3 passed | ✅ |
| 7 | `mprr_run` CLI | `7a279f8` | `test_mprr_run` 3 passed | ✅ (combined w/8,9) |
| 8 | KPI miner ext. | `eacc666` | `test_mine_iteration_kpis` 4 passed (3 pre-existing intact) | ✅ R5 mined-not-typed |
| 9 | fixtures + e2e | `548e45a` | `test_mprr_e2e` 3 passed (known/degenerate/non-python R1) | ✅ |
| 10 | SKILL.md MPRR section + MPRR references page (repo-B) + nosec fix | `31ba6ab` | full suite 187; instruction-lint **0 net-new findings** vs main | ✅ |

**Necessary plan-vs-reality deviations (recorded, not gamed):**
- `bcabba7` **CI hypothesis**: repo-B had NO pyproject/requirements and CI installed only
  `pytest==9.0.3`; the plan assumed `hypothesis` was "already a test dep" (it was not).
  Added pinned `hypothesis==6.155.2` to `.github/workflows/check.yml` so the DoD-#1
  property tests run in CI. (Test-only env addition; no declared-dependency growth — repo-B
  has no dep manifest for the dependency/growth gates to see.)
- `08383ba` **plain-script import fix**: the verbatim `mprr_run.py` did `from scripts import …`
  which raised `ModuleNotFoundError` under the documented `python scripts/mprr_run.py …`
  invocation (used by the plan, SKILL.md, the launch prompt, the instruction-lint probe, AND
  the Phase-B pump). Added a repo-root `sys.path` bootstrap. The orchestrator instruction-lint
  gate caught this — it was the root cause of all 3 introduced dead-command findings, now gone.
- repo-B has **no ruff/bandit/type tooling**; its real ship gates are `pytest -q` +
  `scripts/check_release.py`. The plan's "ruff lint + format + type" gate list does not apply
  to repo-B; I ran repo-B's actual established gates. (The nosec hygiene fix in `31ba6ab` is
  therefore inert today but left correct for any future security-audit run.)

**Operational note carried to Phase B:** `mprr_run._class_of` falls back to `"mechanical"`,
so every `integrate` **evidence JSON the orchestrator builds must include `remediation_class`**
(the packet already carries it) — otherwise a refactor/test_removal item would be checked
against the wrong gate tier. The orchestrator controls evidence construction, so this never fires.

### Phase A ship evidence (DoD #1, #5, #6 partial, #7)

- **Full repo-B suite:** `pytest -q` → **187 passed** (worktree, fresh-clone, and CI).
- **Release gate:** `scripts/check_release.py` → `{"status":"pass"}`.
- **Fresh-clone sim** (binding lesson — before any push): clone → checkout `sp14/mprr-engine`
  → CI-equivalent venv (`pytest==9.0.3 hypothesis==6.155.2`) → `pytest tests/ -q` 187 passed +
  `check_release` pass + `mprr_run.py --help` OK from the clean tree.
- **Merge + push:** fast-forward `8f27083..e4dda1c` → `main`; pushed.
- **CI:** run `27472490889` on `e4dda1c` → **success** (checkout, setup-python, install deps
  incl. hypothesis, run tests, release checks all ✓). No fix-forward needed.
- **Release:** tagged + pushed **`v0.5.0`** (SKILL.md `version: 0.5.0`, CHANGELOG `## 0.5.0`).
- **Reinstall:** rsync repo→`~/.agents/skills/repo-audit-refactor-optimize` (excl `.git`,
  venvs, caches). Readback: installed `version: 0.5.0`, installed `check_release` pass,
  7 `mprr_*.py` scripts present, installed `mprr_run.py --help` OK.
- **Bootstrap probe:** installed `check_skill_requirements.py --repo <repo-A> --extra-root
  ~/.agents/skills` → **exit 0**, `restart_required=false`, `stop_before_discovery=false`.
- **Pump smoke test (real merges, validates the Phase-B round-trip):** toy git repo, 2 disjoint
  dead-code DELETE findings → `plan` emitted packets `[d1,d2]` (running `{d1:[a.py], d2:[b.py]}`)
  → 2 disjoint worker branches → `integrate d1`/`integrate d2` both exit 0 via real `merge_clean`
  → merged main has both dead funcs removed → mined KPI `{dispatched:2, merged:2,
  merge_conflict_rate:0.0, peak_concurrency:2}`.

**Phase A: COMPLETE + SHIPPED (repo-B v0.5.0).** Proceeding to Phase B.

