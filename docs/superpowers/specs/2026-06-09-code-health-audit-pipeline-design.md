# Code Health Audit Pipeline — Design

Date: 2026-06-09
Status: Approved (design phase)
Scope: First refactoring lane, built as a **new standalone package/repo** (working name
`code-health-skills`), separate from `repo-audit-skills`. Python-only, designed Open/Closed
for later C and Rust expansion. Top-orchestrator integration is deferred to a later cycle.

## 1. Goal and Context

The `repo-audit-skills` package established one repeating pattern: granular *component
("leaf") diagnostic skills* feed an *orchestrating "pipeline" skill* that merges their
output into a single ranked report plus a machine-readable summary carrying a supervisor
decision and exit codes `0/1/2`. The test domain implements this fully there
(`test-quality-assurance` + `test-redundancy-triage` → `test-audit-pipeline`).

The refactoring / code-health domain has **no owned skills** anywhere. This design closes
that gap with five owned, maximally-deterministic leaf skills and one umbrella pipeline —
built from scratch in a **new, separate package** so the new work is cleanly isolated from
the existing test/perf skills. The new package reuses the *proven shape* of
`repo-audit-skills` (skill contract, installer, release checks) without bundling its skills.

### Decisions locked during brainstorming

- Refactoring lane first (performance lane is a later, separate spec/cycle).
- Python-only now; umbrella designed Open/Closed so C/Rust leaves plug in later without
  reshaping it.
- Maximally deterministic: prefer tools that do the work without external intelligence.
- Granular leaf skills (separately manageable) + one umbrella pipeline skill.
- Diagnose-only / advisory: leaves and umbrella detect and rank; they never mutate source.
  Execution stays in a consumer's gated execution stage.
- Umbrella drives leaves via a deterministic Python orchestrator script (Approach A),
  exactly as `test-audit-pipeline/audit_pipeline.py` calls its sibling leaf scripts.
- Code quality (lint/format/types) is part of the pipeline as a fifth leaf — an owned,
  deterministic replacement for the external `python-code-quality`.
- **New standalone package/repo** (working name `code-health-skills`): the five skills do
  NOT go into `repo-audit-skills`. The new repo has its own installer + release machinery
  and installs alongside the old package into the same skills root.
- **Top-orchestrator integration deferred**: `repo-audit-refactor-optimize` is not rewired
  in this cycle. The five skills ship standalone and individually runnable; wiring them
  into any orchestrator is a separate later decision.

## 2. Package and Skill Layout

A new standalone repo (working name `code-health-skills`), structured like
`repo-audit-skills` but containing only the new skills and its own release machinery:

```
code-health-skills/                    # NEW repo, sibling to repo-audit-skills
├─ package.json                        # name: code-health-skills, own version line
├─ README.md, AGENTS.md, LICENSE
├─ bin/install-code-health-skills.js   # own installer (cloned shape), own skills[] list
├─ scripts/check_release.py            # own release gate (REQUIRED_SKILLS = the 5 below)
├─ scripts/check_skill_fixtures.py     # own --help smoke gate
└─ skills/
   ├─ complexity-audit/      (leaf)   radon + lizard          → SIMPLIFY / DECOMPOSE
   ├─ duplication-audit/     (leaf)   jscpd + symilar         → EXTRACT / MERGE
   ├─ dead-code-audit/       (leaf)   vulture + ruff F-codes  → DELETE
   ├─ structure-audit/       (leaf)   grimp import graph      → RESTRUCTURE
   ├─ quality-audit/         (leaf)   ruff + ruff format + ty → LINT / FORMAT / TYPE
   └─ code-health-audit-pipeline/  (umbrella)
          scripts/code_health_pipeline.py   # runs leaves in parallel, merges, ranks
          scripts/leaf_registry.json        # OCP: leaf name → script path → languages
          references/{rubric.md, finding-schema.json, sample-report.md,
                      prioritization.md, rule-ownership.md}
```

Each skill follows the existing skill contract (`SKILL.md` + frontmatter, `scripts/`,
`references/`, `agents/openai.yaml`, `LICENSE`). The release/install machinery is the same
*shape* as `repo-audit-skills`, cloned and trimmed to this package's five skills — not a
dependency on the old package.

### OCP hinge: `leaf_registry.json`

The umbrella does **not** hardcode the leaves. It reads `leaf_registry.json` (leaf name →
script path → applicable languages), filters to the target repo's languages, and runs the
matching leaves. Adding a C or Rust leaf later = a new leaf skill + one registry entry,
with zero edits to `code_health_pipeline.py`.

## 3. Shared Finding Schema and Leaf Contract

Every leaf is independently runnable and emits the **same finding schema** (one shared
`references/finding-schema.json`, modeled on `perf-benchmark`'s schema). A finding:

```json
{
  "id": "stable-hash",
  "leaf": "complexity",
  "signal": "DECOMPOSE",
  "severity": "high",
  "path": "src/pkg/foo.py",
  "location": {"line_start": 40, "line_end": 95, "symbol": "process"},
  "metric": {"name": "cyclomatic_complexity", "value": 22, "threshold": 10},
  "evidence": {"tool": "radon", "raw": "F 40:0 process - C (22)"},
  "confidence": "high",
  "suggested_action": "Split process() — 22 branches exceed threshold 10"
}
```

`signal` enum (nine verbs): `SIMPLIFY`, `DECOMPOSE`, `EXTRACT`, `MERGE`, `DELETE`,
`RESTRUCTURE`, `LINT`, `FORMAT`, `TYPE`.

`id` is a deterministic hash of `(leaf, path, symbol, metric.name)` so findings are stable
across runs.

### Uniform leaf CLI contract

- Inputs: `--root`, `--source-prefix` (filter to product code), `--exclude`, `--out-dir`,
  `--config` (threshold/rule overrides), `--format json|md`.
- Outputs: `<leaf>_findings.json` (list, sorted for byte-stable output) + `<leaf>_report.md`.
- Exit codes: `0` = clean, `1` = advisory findings present, `2` = tool/config error.
- Determinism: pinned tool flags, sorted findings, stable IDs → identical input yields
  byte-identical JSON (enforced by a determinism test).
- No source mutation — advisory only, like `test-redundancy-triage`.
- Repo-agnostic — no hardcoded paths; everything driven by `--root` / `--source-prefix`.

## 4. The Five Leaf Skills

All tools are pip-installable and declared in each leaf's `pyproject.toml`. A missing tool
yields a clean exit `2` ("errored") rather than a silent skip or a guess.

### complexity-audit — SIMPLIFY / DECOMPOSE
- Tools: `radon cc` (cyclomatic complexity/function), `radon mi` (maintainability
  index/module), `lizard` (NLOC, token count, parameter count; cross-checks CCN).
- Default thresholds (config-overridable): CC > 10 → `medium`, CC > 20 → `high`;
  MI < 65 → `low`, MI < 50 → `medium`; function length > 50 NLOC → DECOMPOSE;
  params > 5 → SIMPLIFY.
- Sole source of truth for complexity (ruff `C901` is excluded from `quality-audit`).

### duplication-audit — EXTRACT / MERGE
- Primary: `jscpd` (token-based clone detection, JSON reporter, language-aware).
  Fallback: pylint `symilar`.
- Threshold: min 50 tokens / 5 lines (config-overridable). Clone spanning ≥2 files →
  EXTRACT; clones within one module → MERGE.
- One finding per clone group, listing all instances (paths + line ranges).

### dead-code-audit — DELETE
- Tools: `vulture` (unused functions/classes/methods/vars with confidence %), `ruff`
  F-codes F401 (unused import), F811 (redefinition), F841 (unused local).
- Vulture confidence % maps to the schema `confidence` field; `--allowlist` (vulture
  whitelist) suppresses known false positives (e.g. framework hooks).
- Owns exactly F401/F811/F841 in the ruff space (see rule-ownership map).

### structure-audit — RESTRUCTURE
- Tool: `grimp` (the import-graph library behind import-linter). Builds the module import
  graph; computes import cycles, fan-in / fan-out per module, god-modules.
- Optional `--layers` config (ordered layering contract); declared-layering violations
  become RESTRUCTURE findings.
- Defaults: any import cycle → `high`; fan-in > 20 or fan-out > 20 → `medium`.

### quality-audit — LINT / FORMAT / TYPE
- Tools: `ruff check` (lint), `ruff format --check` (formatting drift, reported not
  applied), type checker `ty` by default (`mypy` selectable via `--config`).
- Advisory only: reports violations / drift / type errors; never runs `ruff --fix` or
  reformats. Auto-fix stays in the orchestrator's gated Execute stage.
- Runs ruff with an explicit `select`/`ignore` that excludes codes owned by other leaves
  (F401/F811/F841 and C901), guaranteeing non-overlap.

### Scope boundary

These leaves surface **refactoring and code-quality signals** (the nine verbs). They do
not reimplement formatting application, full static analysis suites, or style philosophy
beyond what the tools deterministically report.

## 5. Rule-Ownership Map (non-overlap contract)

A single canonical map in `references/rule-ownership.md` is the source of truth; no
tool/rule is counted by two leaves. The umbrella `(path, line, rule)` dedupe is a backstop
only.

```
dead-code-audit   → vulture, ruff F401/F811/F841                 → DELETE
complexity-audit  → radon cc/mi, lizard, ruff C901 (mccabe)      → SIMPLIFY/DECOMPOSE
duplication-audit → jscpd / symilar                               → EXTRACT/MERGE
structure-audit   → grimp import graph                            → RESTRUCTURE
quality-audit     → ruff (all EXCEPT F401/F811/F841, C901),
                    ruff format --check, ty/mypy                  → LINT/FORMAT/TYPE
```

## 6. Umbrella Orchestration and Supervisor/Exit-Code Contract

`code_health_pipeline.py`, deterministically:

1. **Discover** — read `leaf_registry.json`, filter leaves whose `languages` include the
   repo's languages (Python now; C/Rust leaves register later).
2. **Run in parallel** — each leaf script via `ThreadPoolExecutor` (all read-only,
   independent), each writing to its own `out-dir/<leaf>/`. Leaf-script overrides
   (`--complexity-script`, …) mirror `test-audit-pipeline`.
3. **Merge & dedupe** — collect `<leaf>_findings.json`, dedupe by `(path, line, rule)`,
   attach owning leaf.
4. **Rank** — score by `severity × confidence ÷ effort`, grouped by signal, using the
   prioritization model in `references/prioritization.md`.
5. **Emit**:
   - `code_health_report.md` — ranked backlog grouped by signal.
   - `code_health_summary.json` — `supervisor` decision + `exit_code` + per-leaf rollup +
     ranked findings (machine-readable contract, mirroring `pipeline_summary.json`).

### Supervisor decision + exit codes (matching test-audit 0/1/2)

- `0` — **PASS**: no findings above `info`, no configured hard gate breached.
- `1` — **ADVISE**: advisory findings present (normal case — refactoring/quality work to
  consider). Non-blocking.
- `2` — **GATE**: a configured hard gate breached (e.g. import cycle present, type errors
  > N, or a leaf errored). Blocking.

Gate thresholds are config-driven (`--config`), default conservative. A leaf that errors
(missing tool, exit `2`) surfaces as `GATE` with that leaf marked `errored` — never a
silent skip.

## 7. Release, Install, and Coexistence

The new package owns its own release/install machinery, cloned in *shape* from
`repo-audit-skills` and trimmed to its five skills. The skills are repo-agnostic tools:
developed and released in `code-health-skills`, installed once to the skills root via the
package's own installer, then run against any target repo via `--root`.

Hard constraint (carried from the reference machinery): every skill's `SKILL.md` `version`
must equal `package.json` version (`check_release.py`). Shipping bumps this package's own
version; its five skills carry that version in lockstep — independent of the
`repo-audit-skills` version line.

Package files to create (own machinery, not edits to the old package):

| File | Role |
|---|---|
| `package.json` | `name: code-health-skills`, own version, `files[]`, `scripts.check` |
| `bin/install-code-health-skills.js` | installer; `skills[]` = the five skills |
| `scripts/check_release.py` | `REQUIRED_SKILLS` / `REQUIRED_SCRIPTS` = the five skills |
| `scripts/check_skill_fixtures.py` | `--help` smoke command per skill script |
| `README.md`, `AGENTS.md`, `LICENSE` | package docs/license |

`npm run check` (fixtures + release) is the single green-light gate. Every script supports
`--help`; entry scripts live at stable `scripts/<name>.py` paths the checker asserts.
Release flow mirrors the reference package: commit → push `main` → tag `vX.Y.Z` → GitHub
release → reinstall into `~/.agents/skills` → verify `--help`.

### Coexistence with `repo-audit-skills` (collision avoidance)

Both packages install into the same skills root and must not collide:

- **Disjoint skill names** — the five new skill directories (`complexity-audit`,
  `duplication-audit`, `dead-code-audit`, `structure-audit`, `quality-audit`,
  `code-health-audit-pipeline`) do not overlap any `repo-audit-skills` name, so there is no
  file collision at the skills root.
- **Independent installers** — each package's installer iterates only its own `skills[]`
  list, so `--force` from one never clobbers the other's skills.
- **Independent version lines** — the two packages bump versions independently; the
  lockstep constraint applies within each package only.

## 8. Orchestrator Integration (Deferred)

Top-orchestrator integration is explicitly **out of scope for this cycle**. The five skills
ship standalone and individually runnable. `repo-audit-refactor-optimize` (in
`repo-audit-skills`) is not modified now — no activation-matrix, SKILL, or bootstrap-manifest
edits.

When integration is taken up later (its own spec/cycle), the seam is already clean: because
skills resolve by name at the shared skills root, an orchestrator can reference
`code-health-audit-pipeline` cross-package without either package depending on the other's
build. Recorded here so the deferred work is not lost, not planned here.

## 9. Testing Strategy

Per-leaf tests (following `perf-benchmark/tests/` style — `helpers.py` + staged tests):
- Clean fixture repo → leaf exits `0`, empty findings.
- Dirty fixture with a *known* planted smell (CC-25 function, 60-line clone, unused
  function, import cycle, lint+type violation) → leaf exits `1` with the expected finding
  id/metric.
- Determinism test — run twice, assert byte-identical `*_findings.json`.
- Missing-tool test — tool absent → exit `2`, leaf marked `errored`, no crash.

Umbrella tests:
- Merge/rank/decision with stubbed leaf outputs (no real tools) → asserts ranking order,
  dedupe, and the 0/1/2 supervisor mapping including GATE-on-errored-leaf.
- Leaf discovery from `leaf_registry.json` + `--*-script` override resolution.
- Parallel execution writes isolated per-leaf `out-dir`s.

Package-gate tests:
- Every new script answers `--help` (fixtures smoke test).
- `npm run check` passes (release gate, version lockstep).

## 10. OCP Extensibility (C/Rust later)

Three seams, none requiring umbrella surgery:
1. `leaf_registry.json` — a C leaf registers with `"languages": ["c"]`; the umbrella
   auto-includes it for C repos.
2. Shared `finding-schema.json` — a new leaf emits the same schema; merge/rank/report work
   unchanged.
3. Rule-ownership map — extended per language; Python ownership untouched.

Adding `c-complexity-audit` later = new leaf skill + one registry entry + release-machinery
registration. Zero edits to `code_health_pipeline.py`.

## 11. Out of Scope

- Performance lane (separate later spec/cycle, possibly its own package).
- C / Rust leaves (designed for, not built now).
- Auto-fix / source mutation (lives in a consumer's gated execution stage).
- Top-orchestrator integration / `repo-audit-refactor-optimize` edits (deferred; §8).
- Any edits to the `repo-audit-skills` package (the new work is fully standalone).
```
