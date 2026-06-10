# SP7: Parallel Skill Tracks — Multi-Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
>
> **For every SP7 orchestrator (A1–A6, B, INT, C):** this plan is the single authority. You coordinate ONLY, never implement. Workers = OpenCode DeepSeek v4 Pro Max via opencode-worker-bridge (file-backed packets, one per worker, own git worktree). Automatic ONE-WAY fallback to native Opus subagent workers ONLY on infrastructure dispatch failure (credits/quota/auth/bridge unreachable) — a gate-failing CHANGE is discard/retry, never a backend switch. A worker's "green" is NOT evidence: re-run every gate yourself and read real output. Commit locally per task. Do NOT push, tag, or release — human reviews. Workers implement plan tasks VERBATIM via TDD.

**Goal:** Six new audit leaves in repo-audit-skills (hotspot-audit, dependency-audit, repo-hygiene-audit, docs-consistency-audit, security-audit, test-effectiveness-audit) developed in six concurrent per-leaf worktree branches; orchestrator upgrades in repo-audit-refactor-optimize (version-aware bootstrap, CI, run-report contract, playbook deepening, manifest lanes for the new leaves); one serial integration track releasing repo-audit-skills v0.4.0 (16 skills, 17 suites, SIGNALS += PERF/SECURITY); and a gated perf-optimization skill in perf-benchmark-skill wrapping the SP6 pipeline. The tracks are partitioned so no two orchestrators ever write the same files.

**Architecture (FIXED):** TRACK A = six per-leaf orchestrators in repo-audit-skills, each in its own worktree+branch, touching ONLY `skills/<leaf>/**`. TRACK B = one orchestrator in repo-audit-refactor-optimize (separate repo, fully concurrent). TRACK INT = one SERIAL integration orchestrator in repo-audit-skills main, starting after A1–A4 report done. TRACK C = one orchestrator in perf-benchmark-skill + a small serialized repo-B follow-up, gated on human SP6-convergence confirmation AND Track B merged.

**Tech stack:** Python 3 stdlib for leaf logic (A5 wraps bandit==1.9.4, A6 wraps mutmut==3.6.0 — pinned, verified on Python 3.14); pytest; node ≥18 for the installer; no new runtime deps anywhere else.

**Repos:**
- repo-A = `/home/jakub/projects/repo-audit-skills` — main at `6938fb50031956b2df6237e76f67456d6f93422f` ("release: v0.3.0"), clean; root `python3 -m pytest --collect-only -q` → **461 tests collected**; self-audit baseline **104**; coverage-gap baseline **2**; suites in `scripts/check_coverage_gap.py` **11**.
- repo-B = `/home/jakub/projects/repo-audit-refactor-optimize` — v0.2.0, `python3 -m pytest tests/ -q` → **53 passed**; NO CI.
- repo-C = `/home/jakub/projects/perf-benchmark-skill` — SP6 run IN FLIGHT, **READ-ONLY until the human confirms SP6 converged**.

## Out of scope (deliberately deferred)

- **Service-level load/soak/spike performance lane** (ISTQB load/soak/spike taxonomy): requires a deployed service, a traffic model, and hours of wall clock — not expressible in this family's deterministic, repo-local, minutes-bounded gates. SP8 candidate; the SP6 playbook's mention of it as "planned SP7" is superseded by this plan.
- **Non-Python code-health leaves:** the leaf CLI contract is language-neutral, but every analyzer pinned in SP7 is Python-bound; each new language needs its own tool pins, fixtures, and self-audit-neutrality proof — defer until the six SP7 leaves have soaked on real repos.
- **Further SIGNALS additions beyond PERF+SECURITY:** every new signal forces a schema bump + 16-way re-vendor + consumer audit; only PERF (Track C) and SECURITY (A5) have committed producers in SP7.
- **API-compatibility diffing** (public-interface break detection): needs two checkouts (a version pair), which breaks the single-tree `--root` leaf contract — defer until a two-tree contract exists.

---

## Empirical pre-flight (verified 2026-06-10 against the SHAs above; every orchestrator re-verifies its own rows before dispatching)

1. **Leaf CLI contract** (`skills/coverage-gap-audit/scripts/coverage_gap_audit.py:140-164`, `skills/structure-audit/scripts/structure_audit.py:320-339`): flags `--root`, `--source-prefix` (append → `source_prefixes`), `--out-dir`, `--config` (JSON threshold overrides), `--format {json,md}` default json; leaf-specific extras (`--coverage-json`, `--exclude`). Missing required args → print `{"status": "error", ...}` JSON, return `hc.EXIT_ERROR`. Success → write `<LEAF>_findings.json` (via `hc.write_findings`) + `<LEAF>_report.md`, print `{"status": "ok", "findings": N, "leaf": LEAF}`, return `EXIT_FINDINGS(1)` if findings else `EXIT_CLEAN(0)`. Tool errors → `ToolError` → status-error JSON + exit 2 (tool-missing convention: `quality_audit.py:80-81` raises `ToolError("ruff is not installed")` on `FileNotFoundError`).
2. **`scripts/check_coverage_gap.py:20-32`**: `SUITES` is a hardcoded 11-entry list (root `tests` + 10 `skills/*/tests`). INT's per-merge edit = append `"skills/<leaf>/tests",`. Its `_prefixes()` (lines 36-41) AND `.coveragerc` (`source = scripts, shared, skills`) are dynamic → a merged leaf's scripts enter coverage scope IMMEDIATELY, so the suite registration must land in the same gate-run as the merge or check:coverage fails with new findings.
3. **`scripts/self_audit.py:23-28` `_prefixes()`**: dynamically appends every `skills/<name>/scripts` dir → new leaf code auto-enters self-audit scope, in-branch too. This justifies the zero-new-findings in-branch rule. NOTE (deviation from prior briefing): `scripts/check_self_audit.py` is TODAY a ONE-WAY ratchet — it re-runs the audit and fails only on findings NOT in the baseline; disappeared findings do not fail it. Task INT-1 hardens it BEFORE any merge: baseline entries absent from the snapshot (stale entries) also FAIL, with instructions to ratchet the baseline down in the same commit. Track A worktrees fork from the base SHA and therefore keep the one-way script in-branch; the equality-style gate applies on main from INT-1 onward. Baseline identity = the 4-key tuple `{leaf, metric, path, symbol}` (verified — entries carry no line numbers, so pure line shifts cannot create stale entries).
4. **`scripts/check_release.py:17-40`**: `REQUIRED_SKILLS` and `REQUIRED_SCRIPTS` are hardcoded 10-entry dicts; version source = `package.json`; every listed `SKILL.md` frontmatter `version:` must equal it. Unlisted skill dirs are NOT checked → new leaves are invisible to check:release until INT adds them.
5. **`bin/install-repo-audit-skills.js:10-21`**: hardcoded 10-element `skills` array. INT must append the 6 new names.
6. **`shared/health_common.py:18-31`**: `SIGNALS = frozenset({"SIMPLIFY","DECOMPOSE","EXTRACT","MERGE","DELETE","RESTRUCTURE","LINT","FORMAT","TYPE","TEST"})`. **There is NO runtime signal validation anywhere** — `Finding` never checks membership; the only consumer is `tests/test_health_common.py:65` (`assert "TEST" in hc.SIGNALS`). The schema bump is therefore purely additive: frozenset edit + re-vendor + test extension.
7. **`skills/code-health-audit-pipeline/scripts/code_health_pipeline.py`**: `_partition_leaves` (lines 112-146) implements ONLY the `coverage_json` requires key; ANY unknown key → fail-safe skip with reason `"requires <key> artifact"`, skipped leaves never enter `leaf_exit` so they cannot gate. `select_leaves` (lines 107-109) is plain set intersection — `languages: ["*"]` is NEVER selected today (no wildcard); INT adds wildcard support (task INT-3, the A3 merge). `EFFORT` (lines 21-32) lacks PERF/SECURITY but `EFFORT.get(signal, 2)` defaults safely — no edit needed.
8. **repo-B `scripts/check_skill_requirements.py`** (979 lines, not 753): B1 slots = `_extract_skill_name` (line 381, reads first 2048 bytes / 20 lines for `name:`), `_register_skill` (line 442), `_skill_entry` (line 494, assigns states `usable_now/advisory_only/installable_now/manual_only`). Lane evaluators use `_all_usable` = `state == "usable_now"` (line 544), so a new `stale_installed` state automatically degrades lanes with no evaluator changes. `load_dependency_manifest` (line 293) never validates the manifest `"version"` field → bumping 1→2 is cosmetic and safe. `_evaluate_performance_lane` line 626 already emits `"Optimization skill missing; lane remains benchmark-first."` when preferred is usable and a declared fallback is not — Track C's repo-B follow-up is manifest+tests only.
9. **SP6 plan T5/T6/T7** (`/home/jakub/projects/perf-benchmark-skill/docs/plans/2026-06-10-sp6-perf-bench-v0.2.md`): `--findings-out` writes shared-shape PERF findings — exact keys `id,leaf,signal,severity,path,location,metric,evidence,confidence,suggested_action`; `leaf == "perf-benchmark"`, `signal == "PERF"`, severity high(FAIL)/medium(WARN), `location == {"line_start":0,"line_end":0,"symbol":"<workload>"}`, `id = sha1("perf-benchmark|<path>|<workload>|<metric>")[:16]`, sorted by `(path, metric.name)`, byte-deterministic. `--baseline-ledger` = JSONL lines `{"timestamp_utc","tier","rubric_total","wall_time_mean","dimensions":{name:tier}}`, `compare` → `{"vs_last":{...},"vs_best":{...}}` (≥1-tier drops; best = max rubric_total; corrupt lines skipped with warning). Summary gains `environment` (keys `cpu_model,kernel,governor,smt,load_avg_1m,python_version,timestamp_utc`; timestamp+load excluded from determinism comparisons) and `wall_time_percentiles {p50,p95,p99}`. Noise gate: CV > `--max-cv` → dimension tier `"N/A (noise)"`. Acceptance ratchet: ≥5% median win, CV ≤ 5% both runs, fingerprints match, suite green.
10. **Tooling:** bandit, mutmut, deptry NOT installed system-wide; PyPI reachable. Pinned: **bandit==1.9.4** (verified on Python 3.14.4; JSON result keys: `filename,line_number,line_range,end_col_offset,issue_severity,issue_confidence,issue_text,test_id,test_name,more_info,issue_cwe,code`; severities/confidences `LOW/MEDIUM/HIGH`). **mutmut==3.6.0** (verified on 3.14.4): loads config AT IMPORT TIME — even `--help` crashes unless CWD has `setup.cfg [mutmut] source_paths=...` → A6 must run it with `cwd=` a prepared sandbox; commands `run/results/show/apply/browse/export-cicd-stats/print-time-estimates/tests-for-mutant`; `mutmut run` flags: only `--max-children`; `mutmut results` lists ONLY problem mutants as `    <module>.x_<func>__mutmut_<N>: <status>` (statuses seen: `no tests`; also `survived`, `timeout`, `suspicious`, `skipped`); `mutmut export-cicd-stats` writes `mutants/mutmut-cicd-stats.json` = `{"killed","survived","total","no_tests","skipped","suspicious","timeout","check_was_interrupted_by_user","segfault"}`; per-file `mutants/<src-path>.meta` JSON has `exit_code_by_key` (one key per mutant → authoritative per-module totals); `print-time-estimates` requires an existing `mutants/` dir → unusable as a pre-run budget counter (A6 uses an ast-based estimate + hard subprocess timeout instead).
11. **Misc:** repo-A has NO root `pyproject.toml` and NO root `CHANGELOG` (relevant to A2/A3 self-audit neutrality); leaf test layout = `conftest.py` (sys.path shim) + `helpers.py` (`load_module()` via importlib for in-process coverage + `run_cli()` subprocess) + `test_<leaf>_{cli,findings,relpaths,idempotent}.py` + `tests/fixtures/`; repo-A CI (`.github/workflows/check.yml`) pins python 3.14 + tool versions and runs `npm install` then `npm run check`; `jscpd` is an npm devDependency → **every Track A worktree must run `npm install` before any `npm run check:*`**; repo-B artifact convention `/tmp/repo-audit-refactor-optimize/<repo-name>/<timestamp>/` (`references/pipeline.md:75`).

---

## Contracts (FROZEN — every track builds against these; deviation = STOP and report)

### C-1. Names, branches, worktrees

| # | Skill dir (frozen) | LEAF id | Script | Branch | Worktree |
|---|---|---|---|---|---|
| A1 | `hotspot-audit` | `hotspot` | `scripts/hotspot_audit.py` | `sp7/hotspot-audit` | `../ras-sp7-hotspot-audit` |
| A2 | `dependency-audit` | `dependency` | `scripts/dependency_audit.py` | `sp7/dependency-audit` | `../ras-sp7-dependency-audit` |
| A3 | `repo-hygiene-audit` | `repo-hygiene` | `scripts/repo_hygiene_audit.py` | `sp7/repo-hygiene-audit` | `../ras-sp7-repo-hygiene-audit` |
| A4 | `docs-consistency-audit` | `docs-consistency` | `scripts/docs_consistency_audit.py` | `sp7/docs-consistency-audit` | `../ras-sp7-docs-consistency-audit` |
| A5 | `security-audit` | `security` | `scripts/security_audit.py` | `sp7/security-audit` | `../ras-sp7-security-audit` |
| A6 | `test-effectiveness-audit` | `test-effectiveness` | `scripts/test_effectiveness_audit.py` | `sp7/test-effectiveness-audit` | `../ras-sp7-test-effectiveness-audit` |

Worktree creation (record the SHA): `git -C /home/jakub/projects/repo-audit-skills rev-parse HEAD && git -C /home/jakub/projects/repo-audit-skills worktree add ../ras-sp7-<leaf> -b sp7/<leaf>`. Expected base SHA `6938fb50031956b2df6237e76f67456d6f93422f`; if main moved, record the new SHA and proceed only if `npm run check` is green there.

### C-2. Leaf CLI contract (= the existing leaves' contract, verified)

Every new leaf MUST expose exactly: `--root`, `--source-prefix` (repeatable, dest `source_prefixes`, default `[]`), `--out-dir`, `--config` (JSON file overriding `DEFAULT_THRESHOLDS`), `--format {json,md}` (default `json`), plus the leaf-specific flags pinned in its task. Exit codes `hc.EXIT_CLEAN=0 / hc.EXIT_FINDINGS=1 / hc.EXIT_ERROR=2`. Outputs in `--out-dir`: `<LEAF>_findings.json` (via `hc.write_findings(findings, out_dir, LEAF)`) and `<LEAF>_report.md`. stdout: one JSON status line (`{"status":"ok","findings":N,"leaf":LEAF}` or `{"status":"error","message":...}`). Missing required args → status-error + exit 2 (argparse itself must not `sys.exit` for these; mirror `coverage_gap_audit.py:167-178`). All findings sorted via `hc.sort_findings`; paths root-relative POSIX; byte-deterministic across runs.

### C-3. Leaf skeleton (normative template — each A-task instantiates it with its table row + its verbatim functions; this is a shared contract, not a cross-task reference)

```python
#!/usr/bin/env python3
"""<one-line leaf description>"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "<LEAF>"

DEFAULT_THRESHOLDS = { <leaf threshold dict from its task> }


class ToolError(RuntimeError):
    pass


# <leaf-specific analysis functions from its task, ending in:>
# def analyze_tree(root, source_prefixes, thresholds, <extras>) -> list[hc.Finding]


def render_report(findings: list[hc.Finding]) -> str:
    lines = [f"# <skill-dir> report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    by_signal: dict[str, list[hc.Finding]] = {}
    for f in findings:
        by_signal.setdefault(f.signal, []).append(f)
    for signal in sorted(by_signal):
        lines.append(f"## {signal} ({len(by_signal[signal])})")
        for f in by_signal[signal]:
            lines.append(
                f"- `{f.path}:{f.line_start}` {f.symbol} — "
                f"{f.metric_name}={f.metric_value:g} [{f.severity}]"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        try:
            thresholds.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"invalid --config: {exc}") from exc
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="<leaf description> (advisory).")
    parser.add_argument("--root")
    parser.add_argument(
        "--source-prefix", action="append", default=[], dest="source_prefixes",
        help="Path prefix(es) relative to --root to include. Repeatable.",
    )
    parser.add_argument("--out-dir")
    parser.add_argument("--config", help="JSON file overriding thresholds.")
    parser.add_argument("--format", choices=["json", "md"], default="json")
    # <leaf-specific arguments from its task>
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir:  # extend per leaf-required extras
        print(json.dumps({"status": "error", "message": "--root and --out-dir are required"}))
        return hc.EXIT_ERROR
    try:
        thresholds = load_thresholds(args.config)
        findings = analyze_tree(args.root, args.source_prefixes, thresholds)  # + extras
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, f"{LEAF}_report.md").write_text(render_report(findings), encoding="utf-8")
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
```

### C-4. Leaf test conventions (normative; instantiate per leaf)

- `tests/conftest.py` — byte-for-byte the existing pattern:

```python
import sys
from pathlib import Path

_here = str(Path(__file__).parent)
if _here not in sys.path:
    sys.path.insert(0, _here)
sys.modules.pop("helpers", None)
```

- `tests/helpers.py` — existing pattern with the leaf's script/findings names:

```python
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "<script>.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("<script>", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False
    )


def read_findings(out_dir):
    return json.loads((Path(out_dir) / "<LEAF>_findings.json").read_text())
```

- Test modules `test_<leaf-snake>_{cli,findings,relpaths,idempotent}.py`; module basenames must be UNIQUE repo-wide (root pytest collects everything without packages).
- **Coverage rule:** subprocess CLI runs are NOT traced by pytest-cov here. All coverage-clearing tests call `load_module().main([...])` or the analysis functions IN-PROCESS. Keep EXACTLY ONE subprocess smoke test per leaf (`test_help_exits_zero` via `run_cli("--help")`); every other CLI/exit-code contract test goes through `mod.main([...])` in-process with `capsys` for the status line.
- Mandatory tests per leaf: help smoke (subprocess); clean fixture → exit 0, `[]` findings; dirty fixture → exit 1, golden findings JSON compared field-by-field (`fixtures/golden_findings.json`, paths root-relative); missing required args → exit 2 + status-error; tool/input error → exit 2; relpath test (findings paths contain no absolute paths and use `/` separators); idempotence test (two runs → byte-identical `<LEAF>_findings.json`).
- Frozen fixtures live under `tests/fixtures/` (committed trees; A1 builds git history in-test via the pinned-env helper in its task — commit SHAs are reproducible because all author/committer name/email/date env vars are pinned).

### C-5. In-branch contract (EVERY Track A branch; encoded in every Track A launch block)

1. Touch ONLY `skills/<leaf-dir>/**`. NO edits to `shared/`, `scripts/`, `package.json`, baselines, `leaf_registry.json`, other skills, CI, docs outside the leaf dir.
2. `SKILL.md` with frontmatter `name: <skill-dir>`, `version: 0.3.0` (INT bumps all 16 to 0.4.0 atomically), `description: >` block; body documents workflow, flags, exit codes, output contract, threshold defaults, and honest limits.
3. Vendored `scripts/health_common.py` byte-identical to main's `shared/health_common.py` — EXCEPT A5, which vendors the post-bump file (C-6) and therefore has an EXPECTED-RED `check:vendored` in-branch.
4. Gates, all run from the worktree root after `npm install`:
   - `python3 -m pytest skills/<leaf-dir>/tests -q` → green (run from the leaf dir too: `cd skills/<leaf-dir> && python3 -m pytest tests -q`).
   - `python3 -m pytest --collect-only -q` → `461 + <leaf tests> tests collected`, zero errors.
   - Local coverage proof: `python3 -m pytest skills/<leaf-dir>/tests -q --cov=skills/<leaf-dir>/scripts --cov-report=term` → every file under `skills/<leaf-dir>/scripts/` ≥ 50% (health_common.py included — its import+dataclass lines clear 50% via in-process use; verify, don't assume).
   - `npm run check:selfaudit` → pass with ZERO new findings vs baseline-104 (in-branch this is the base-SHA ONE-WAY ratchet; the INT-1-hardened equality gate exists only on main and never gates Track A branches; the new scripts are auto-scoped; write finding-clean code: functions ≤ existing complexity gates, no duplication, no dead code, mypy/ruff-clean per quality-audit defaults). If a finding is GENUINELY unavoidable: do NOT touch `scripts/self_audit_frozen.md` or the baseline; document ≤3 candidate freezes with rationale in `skills/<leaf-dir>/docs/sp7-freeze-candidates.md` for INT to adjudicate, and get the branch green by fixing everything else.
   - `npm run check:vendored` → pass (A5: EXPECTED FAIL, exactly one defect naming `skills/security-audit/scripts/health_common.py`; anything else failing = real bug).
   - `npm run check:fixtures` → pass. `npm run check:coverage` → EXPECTED FAIL in-branch (the 11-suite list doesn't include the new leaf; its scripts show as uncovered) — the local coverage proof above is the in-branch substitute. `npm run check:release` → pass (new dir is unlisted, hence ignored).
5. Commit per task; final commit message `feat(<leaf-dir>): <summary> (SP7 <A#>)`. Leaf reports done with: leaf test count, coverage table, gate outputs, freeze-candidate file (or "none").

### C-6. Post-bump SIGNALS (verbatim; A5 vendors it, INT lands it)

The post-bump `shared/health_common.py` is main's file at the base SHA with EXACTLY this hunk applied to lines 18-31 (and no other change):

```python
SIGNALS = frozenset(
    {
        "SIMPLIFY",
        "DECOMPOSE",
        "EXTRACT",
        "MERGE",
        "DELETE",
        "RESTRUCTURE",
        "LINT",
        "FORMAT",
        "TYPE",
        "TEST",
        "PERF",
        "SECURITY",
    }
)
```

### C-7. Umbrella registration & requires keys (pinned decisions)

| Leaf | leaf_registry.json | Rationale |
|---|---|---|
| hotspot-audit | **STANDALONE** (not registered) | History-window args (`--rev`/`--max-commits`) can't be pinned by the umbrella; unpinned runs change with every commit → would break the self-audit ratchet and surprise stranger repos on non-git roots. |
| dependency-audit | Registered, NO `requires`, `languages: ["python"]` | Offline core is deterministic and manifest-gated (no deps manifest → no findings, see A2). `--advisory-report` is standalone-only. |
| repo-hygiene-audit | Registered, `languages: ["*"]` | INT-3 (the A3 merge) adds wildcard support to `select_leaves`. All findings prefix-filtered → self-audit-neutral. |
| docs-consistency-audit | Registered, `languages: ["python"]` | Command introspection is Python-specific. Docstring group default-OFF (config opt-in) keeps registration self-audit-neutral. |
| security-audit | **STANDALONE** (not registered) | Deliberate-run tool; bandit on subprocess-heavy tooling repos (like this one) would bury the 104 baseline; heavier dep. |
| test-effectiveness-audit | Registered WITH `"requires": {"mutation_scope": true}` | Current pipeline fail-safe-skips unknown keys (verified) → visible in `skipped` as `requires mutation_scope artifact`, never runs, never gates. Pipeline plumbing for it is future work. |

Pinned requires-key NAMES (for future pipeline support and for the standalone flags): `advisory_report` (A2/A5 flag `--advisory-report`), `mutation_scope` (A6, scope = `--paths` file + `--max-mutants`).

### C-8. Advisory-report JSON shape (shared by A2 and A5; never fetched in-band)

```json
{
  "source": "pip-audit",
  "generated_utc": "2026-06-10T00:00:00Z",
  "packages": [
    {
      "name": "requests",
      "installed_version": "2.19.0",
      "latest_version": "2.32.3",
      "vulns": [
        {"id": "PYSEC-2018-28", "severity": "high", "fix_versions": ["2.20.0"]}
      ]
    }
  ]
}
```

`severity` ∈ {"low","medium","high","critical", null}; `critical` maps to finding severity `high`; null → `medium` with confidence `medium`. `latest_version` null = unknown (no outdated finding).

### C-9. Global numbers (final state after INT)

Version target **0.4.0** (package.json + ALL 16 SKILL.md). Skill count **16**. `check_coverage_gap.SUITES` **17**. Self-audit baseline: **equality from INT-1 onward — baseline == snapshot exactly = 104 − entries removed by fixes + only INT-adjudicated freezes (target 0; hard cap 10 per leaf — more = STOP and report, never blanket-freeze); the hardened `check_self_audit.py` fails on stale entries**. Coverage-gap baseline stays **2**. Installer `--list` → 16 skills. Root collection: `461 + 3 (INT-1 gate tests) + Σ(new leaf tests)`, zero errors, exact number recorded in the INT run report. Repo-B ends at **0.3.0** (Track B), then **0.3.1** (Track C follow-up). perf-optimization SKILL.md **0.1.0**.

### C-10. Concurrency & worker caps

Recommended batch 1 = A1+A2+A3+A4+B (5 concurrent orchestrator sessions). Batch 2 = A5+A6 (launch anytime; their MERGES are deferred until after INT's schema bump). INT starts only after A1–A4 report done. C starts only after the human confirms SP6 converged AND Track B is merged. Per-orchestrator worker caps: each Track A leaf **2**, Track B **3**, INT **2**, Track C **2**. No orchestrator ever writes outside its own worktree/repo (Track B's C4 follow-up belongs to Track C's session, serialized after B merges).

**Global resource contention (binding for every concurrent session):**

- **(a) Bridge artifact isolation.** The opencode-worker-bridge run directory is caller-selected: every bridge command takes an explicit `--run-dir`, and its SKILL.md (`~/.claude/skills/opencode-worker-bridge/SKILL.md`, "Create a run directory under the user workspace, for example `artifacts/opencode-worker-bridge/<timestamp>/`") keeps all state/packet/result JSON under that directory. Each SP7 orchestrator session MUST create a session-unique run dir inside its OWN worktree/repo — `artifacts/opencode-worker-bridge/sp7-<track-id>-<YYYYMMDDTHHMMSSZ>/` with `<track-id>` ∈ {a1..a6, b, int, c} — and pass it as `--run-dir` to every bridge command. Concurrent sessions never share or reuse packet/result paths; the run dir is gitignored-or-untracked scratch, never committed.
- **(b) Quota independence.** OpenCode quota/credit exhaustion triggers the ONE-WAY native-Opus fallback PER SESSION, independently: one session falling back does NOT switch any other; each session keeps its own backend decision for its whole life and reports it.
- **(c) Stagger.** Launch batch-1 sessions ~2 minutes apart (A1 → A2 → A3 → A4 → B) so worktree creation, `npm install`, and first worker dispatch don't collide on disk and API bursts.
- **(d) Global worker ceiling.** Batch 1 peak = A1–A4 at cap 2 each + B at cap 3 = **11 concurrent workers max**. If quota/credit errors appear early in any session, reduce per-session caps first (Track A 2→1, Track B 3→2) before any session flips to native fallback.

---

# TRACK A — six per-leaf orchestrators in repo-audit-skills

Common shape per leaf (2 workers): **Wave 1** W-1 = fixtures + failing tests (the verbatim test code below) ∥ W-2 = `SKILL.md` + `docs/sp7-freeze-candidates.md` stub ("none yet") + vendored `health_common.py` copy. **Wave 2** W-1 = implementation to green (script per C-3 + the leaf's verbatim functions) while W-2 = relpath/idempotence/coverage tests. **Gate (orchestrator):** the full C-5 gate list, re-run yourself. Each leaf's task below pins: extra CLI flags, thresholds, finding constructors, fixtures, and the leaf-specific test assertions.

### Task A1: hotspot-audit — git-history mining (stdlib only)

**Files:** `skills/hotspot-audit/{SKILL.md, docs/sp7-freeze-candidates.md, scripts/hotspot_audit.py, scripts/health_common.py, tests/conftest.py, tests/helpers.py, tests/test_hotspot_cli.py, tests/test_hotspot_findings.py, tests/test_hotspot_relpaths.py, tests/test_hotspot_idempotent.py, tests/fixtures/golden_findings.json}`

**Extra CLI flags:** `--rev` (default `"HEAD"`), `--max-commits` (int, default 500). Both the RESOLVED rev SHA and max-commits are recorded in every finding's `evidence_raw` and in the stdout status line (`"rev": sha, "max_commits": N`) for determinism.

**Thresholds:** `DEFAULT_THRESHOLDS = {"min_churn_commits": 5, "min_churn_complexity_product": 1000, "min_coupling_ratio": 0.7, "min_coupling_changes": 5, "max_commit_files": 50, "min_author_share": 0.9, "min_author_commits": 10}`

**Core functions (verbatim):**

```python
def _git(root: Path, *args: str) -> str:
    import subprocess
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True, capture_output=True, timeout=120, check=False,
        )
    except FileNotFoundError as exc:
        raise ToolError("git is not installed") from exc
    if proc.returncode != 0:
        raise ToolError(f"git {args[0]} failed: {proc.stderr.strip()}")
    return proc.stdout


def _resolve_rev(root: Path, rev: str) -> str:
    out = _git(root, "rev-parse", "--verify", f"{rev}^{{commit}}")
    return out.strip()


def read_history(root: Path, rev: str, max_commits: int) -> list[dict]:
    """List of {"sha", "author", "files": [paths]} oldest-last, newest-first order kept."""
    sha = _resolve_rev(root, rev)
    raw = _git(
        root, "log", sha, f"--max-count={max_commits}",
        "--numstat", "--no-renames", "--format=%x01%H%x02%an",
    )
    commits: list[dict] = []
    for block in raw.split("\x01"):
        if not block.strip():
            continue
        head, _, body = block.partition("\n")
        commit_sha, _, author = head.partition("\x02")
        files = []
        for line in body.splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[2]:
                files.append(parts[2])
        commits.append({"sha": commit_sha, "author": author, "files": files})
    return commits


def _nloc(path: Path) -> int:
    try:
        return sum(
            1 for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.strip()
        )
    except OSError:
        return 0


def _in_scope(rel: str, prefixes: list[str]) -> bool:
    return not prefixes or any(rel.startswith(p) for p in prefixes)
```

`analyze_tree(root, source_prefixes, thresholds, rev, max_commits)` then computes, over `commits = read_history(...)` (raising `ToolError("not a git repository: <root>")` when `git rev-parse --git-dir` fails, and `ToolError("no commits reachable from --rev <rev>")` when history is empty):

- **(a) hotspot**, signal `DECOMPOSE`: per file that still exists under root and is in scope, `churn` = number of commits touching it; skip files with `churn < min_churn_commits`; `product = churn * _nloc(file)`; finding when `product >= min_churn_complexity_product`. `metric_name="churn_complexity_product"`, `metric_value=float(product)`, `metric_threshold=float(min_churn_complexity_product)`, `symbol="<file>"`, `line_start=line_end=1`, severity `high` if ≥4× threshold, `medium` if ≥2×, else `low`; confidence `medium`; `evidence_tool="git"`; `evidence_raw=f"{churn} commits x {nloc} nloc in last {len(commits)} commits from {sha[:12]}"`; suggested_action `f"Hotspot: {rel} changes often and is large; split along change axes"`.
- **(b) temporal coupling**, signal `RESTRUCTURE`: over commits with `1 < len(files) <= max_commit_files`, count pair co-changes for in-scope, still-existing file pairs; for each pair with `co >= min_coupling_changes` and `ratio = co / min(churn_a, churn_b) >= min_coupling_ratio`: path = lexicographically smaller file, `symbol=f"{a}<->{b}"` (sorted), `metric_name="temporal_coupling_ratio"`, `metric_value=round(ratio, 2)`, threshold `min_coupling_ratio`, severity `medium`, confidence `medium`, evidence_raw `f"{co} co-changes of {a} and {b} from {sha[:12]}"`, suggested_action "Files co-change; move the shared concern into one module or merge them".
- **(c) knowledge concentration**, signal `RESTRUCTURE`: per in-scope existing file with `churn >= min_author_commits`, top author share `= max(author_counts)/churn`; finding when `share > min_author_share`: `metric_name="author_concentration"`, `metric_value=round(share, 2)`, threshold `min_author_share`, severity `low`, **confidence `low`**, `symbol="<file>"`, evidence_raw `f"top author {top}/{churn} commits from {sha[:12]}"`, suggested_action "Knowledge concentrated in one author; schedule reviews/pairing on this file".

**Fixture helper (verbatim, in `tests/helpers.py` after the C-4 block):**

```python
import os
import subprocess as sp

PIN_ENV = {
    "GIT_AUTHOR_NAME": "alice", "GIT_AUTHOR_EMAIL": "alice@x.test",
    "GIT_COMMITTER_NAME": "alice", "GIT_COMMITTER_EMAIL": "alice@x.test",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00 +0000",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00 +0000",
    "HOME": "/tmp", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
}


def _g(repo, *args, author=None):
    env = dict(os.environ, **PIN_ENV)
    if author:
        env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = author
        env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = f"{author}@x.test"
    sp.run(["git", "-C", str(repo), *args], env=env, check=True, capture_output=True, text=True)


def make_history(tmp_path):
    """8 deterministic commits: hot.py churns 6x at 200 nloc (product 1200 >= 1000);
    a.py+b.py co-change 5x; hot.py is also the knowledge fixture (6/6 alice commits,
    surfaced only via a lowered min_author_commits config); bob touches only b.py once."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")
    for i in range(6):
        (repo / "hot.py").write_text(
            "\n".join(f"x{j} = {j}  # rev {i}" for j in range(200)) + "\n")
        if i < 5:
            (repo / "a.py").write_text(f"a = {i}\n")
            (repo / "b.py").write_text(f"b = {i}\n")
        _g(repo, "add", "-A")
        _g(repo, "commit", "-q", "-m", f"c{i}")
    (repo / "b.py").write_text("b = 99\n")
    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "bob-touch", author="bob")
    (repo / "calm.py").write_text("calm = 1\n")
    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "calm")
    return repo
```

**Key findings-test assertions (verbatim core of `test_hotspot_findings.py`):**

```python
from helpers import load_module, make_history


def test_hotspot_churn_product(tmp_path):
    repo = make_history(tmp_path)
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    assert rc == 1
    import json
    data = json.loads((out / "hotspot_findings.json").read_text())
    hot = [f for f in data if f["metric"]["name"] == "churn_complexity_product"]
    assert [f["path"] for f in hot] == ["hot.py"]
    assert hot[0]["metric"]["value"] == 1200.0  # 6 commits x 200 nloc; < 2x threshold -> "low"
    assert hot[0]["signal"] == "DECOMPOSE"
    assert hot[0]["severity"] == "low"
    pairs = [f for f in data if f["metric"]["name"] == "temporal_coupling_ratio"]
    assert [f["location"]["symbol"] for f in pairs] == ["a.py<->b.py"]
    assert pairs[0]["metric"]["value"] == 1.0  # co=5 / min(churn a=5, churn b=6) = 5/5
    # default min_author_commits=10 > the fixture's 6 -> no knowledge findings by default
    assert [f for f in data if f["metric"]["name"] == "author_concentration"] == []


def test_author_concentration_with_lowered_config(tmp_path):
    repo = make_history(tmp_path)
    mod = load_module()
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"min_author_commits": 5}')
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)])
    assert rc == 1
    import json
    data = json.loads((out / "hotspot_findings.json").read_text())
    conc = [f for f in data if f["metric"]["name"] == "author_concentration"]
    # a.py: alice 5/5 commits; hot.py: alice 6/6 commits; b.py: alice 5/6 = 0.83 < 0.9 -> absent
    assert [f["path"] for f in conc] == ["a.py", "hot.py"]
    assert all(f["confidence"] == "low" and f["signal"] == "RESTRUCTURE" for f in conc)


def test_non_git_root_exits_two(tmp_path, capsys):
    mod = load_module()
    plain = tmp_path / "plain"
    plain.mkdir()
    rc = mod.main(["--root", str(plain), "--out-dir", str(tmp_path / "o")])
    assert rc == 2
    assert "not a git repository" in capsys.readouterr().out
```

(W-1 MUST recompute the coupling expectation from the fixture before freezing: `a.py` churn 5, `b.py` churn 6, co-changes 5 → ratio `5/5 = 1.0`; the inline comment stays as the audit trail. The hotspot value 360 = 6×60. If the implementation computes differently, fix the implementation, not the golden, unless the fixture math above is wrong — then fix the comment AND the golden together and say so in the report.) Also: pin a `--max-commits 3` test asserting fewer/zero findings and that `evidence_raw` contains the resolved short SHA, and a `--rev` test pinning to the first commit (`git rev-list --max-parents=0 HEAD`) → zero findings (one commit of history).

**A1 DoD:** C-5 gates green (this leaf has no expected-red beyond check:coverage); findings deterministic across two full runs (byte-identical); non-git and empty-history exits proven in-process; SKILL.md documents the pinned-window determinism contract and the standalone (non-registry) status.

### Task A2: dependency-audit — declared vs imported (stdlib; tomllib ⇒ Python ≥3.11, document it)

**Files:** `skills/dependency-audit/{SKILL.md, docs/sp7-freeze-candidates.md, scripts/dependency_audit.py, scripts/health_common.py, tests/conftest.py, tests/helpers.py, tests/test_dependency_cli.py, tests/test_dependency_findings.py, tests/test_dependency_advisory.py, tests/test_dependency_relpaths.py, tests/test_dependency_idempotent.py, tests/fixtures/...}`

**Extra CLI flags:** `--advisory-report PATH` (optional; C-8 shape; unreadable/malformed → `ToolError` exit 2).

**Thresholds:** `DEFAULT_THRESHOLDS = {}` (this leaf is rule-based; keep the dict empty but the `--config` plumbing intact).

**Manifest rule (self-audit-critical):** a "deps manifest" = `pyproject.toml` containing a `[project]` table, or any root-level `requirements*.txt`. If NO manifest exists → ALL offline groups are skipped, status line gains `"manifest": false`, exit 0 with zero findings. (repo-A has no root pyproject → registration is self-audit-neutral; verified.)

**Offline core (verbatim key functions):**

```python
import ast
import sys as _sys
import tomllib

MODULE_TO_DIST = {
    "PIL": "pillow", "cv2": "opencv-python", "yaml": "pyyaml", "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4", "dateutil": "python-dateutil", "dotenv": "python-dotenv",
    "jwt": "pyjwt", "OpenSSL": "pyopenssl", "Crypto": "pycryptodome", "git": "gitpython",
    "fitz": "pymupdf", "attr": "attrs", "pkg_resources": "setuptools", "serial": "pyserial",
    "usb": "pyusb", "websocket": "websocket-client", "zmq": "pyzmq", "magic": "python-magic",
    "docx": "python-docx", "pptx": "python-pptx",
}
STDLIB = frozenset(_sys.stdlib_module_names)


def _norm(name: str) -> str:
    return name.lower().replace("_", "-")


def _dist_candidates(module: str) -> tuple[str, str]:
    """(candidate dist name, confidence): exact table hit -> high, else normalized guess -> medium."""
    if module in MODULE_TO_DIST:
        return MODULE_TO_DIST[module], "high"
    return _norm(module), "medium"


def collect_imports(root: Path, prefixes: list[str]) -> dict[str, list[tuple[str, int, bool]]]:
    """top-level module -> [(relpath, lineno, is_test_scope)]"""
    out: dict[str, list[tuple[str, int, bool]]] = {}
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if prefixes and not any(rel.startswith(p) for p in prefixes):
            continue
        is_test = "tests" in Path(rel).parts or Path(rel).name.startswith("test_")
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods = [node.module.split(".")[0]]
            for m in mods:
                out.setdefault(m, []).append((rel, node.lineno, is_test))
    return out


def declared_deps(root: Path) -> tuple[dict[str, str], bool]:
    """normalized dist -> manifest relpath; bool = any manifest found."""
    declared: dict[str, str] = {}
    found = False
    py = root / "pyproject.toml"
    if py.exists():
        try:
            data = tomllib.loads(py.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ToolError(f"invalid pyproject.toml: {exc}") from exc
        project = data.get("project")
        if isinstance(project, dict):
            found = True
            specs = list(project.get("dependencies", []))
            for extra in (project.get("optional-dependencies") or {}).values():
                specs.extend(extra)
            for spec in specs:
                declared.setdefault(_spec_name(spec), "pyproject.toml")
    for req in sorted(root.glob("requirements*.txt")):
        found = True
        for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-")):
                declared.setdefault(_spec_name(line), req.name)
    return declared, found


def _spec_name(spec: str) -> str:
    import re
    return _norm(re.split(r"[\s\[<>=!~;]", spec.strip(), 1)[0])
```

Local-module rule: a top-level import name is LOCAL (skipped) when `root/<name>.py` or `root/<name>/__init__.py` exists, or `<name>` is a directory directly under any `--source-prefix`. Finding groups (all require `found == True`):

- **unused declared** → `DELETE`: declared dist with no import mapping to it (compare normalized dist vs `_dist_candidates` of every imported third-party module). path = manifest relpath, `line_start=1`, `symbol=<dist>`, `metric_name="declared_unused"`, value `1.0`, threshold `0.0`, severity `low`, **confidence `medium`** (dynamic imports/plugins are invisible to ast — say so in evidence_raw), evidence_tool `"ast"`.
- **undeclared imported** → `RESTRUCTURE`: imported module not in STDLIB, not local, whose dist candidate isn't declared. path = first importing file (sorted), line = its lineno, `symbol=<module>`, `metric_name="import_undeclared"`, value `1.0`, threshold `0.0`, severity `medium`, confidence from `_dist_candidates`.
- **runtime dep only used in tests** → `RESTRUCTURE`: declared in `[project.dependencies]` (NOT optional/requirements) whose every import site `is_test`. path = manifest, `symbol=<dist>`, `metric_name="runtime_dep_test_only"`, severity `low`, confidence `medium`.
- **advisory mode** (only with `--advisory-report`): per package with non-empty `vulns` → `RESTRUCTURE`, path = manifest relpath (or `"pyproject.toml"` if none), `symbol=<name normalized>`, `metric_name="dependency_vulnerabilities"`, `metric_value=float(len(vulns))`, threshold `0.0`, severity = max severity per C-8 mapping, confidence `high`, evidence_tool `"advisory-report"`, evidence_raw = comma-joined vuln ids + fix versions. Per package with `latest_version` non-null and != installed → `RESTRUCTURE`, `metric_name="dependency_outdated"`, value `1.0`, severity `info`, confidence `medium`. NOTE: advisory findings deliberately use `RESTRUCTURE`, not `SECURITY` — A2 merges BEFORE the schema bump; `SECURITY` is reserved to the security-audit leaf.

**Fixtures:** `fixtures/dirty/` = `pyproject.toml` declaring `requests`, `left-pad-py` (unused) + optional dep `rich` (unused), `src/app.py` importing `requests`, `yaml` (undeclared → dist `pyyaml` medium... NOTE `yaml` IS in the table → high), `src/util.py` importing `pendulum` (undeclared, table-miss → medium), `tests/test_app.py` importing `pytest`; plus `pytest` declared in `[project.dependencies]` → runtime_dep_test_only. `fixtures/clean/` = matching imports/declarations. `fixtures/no_manifest/` = imports only → exit 0, `"manifest": false`. `fixtures/advisory.json` = C-8 example verbatim. Golden findings JSON frozen for `dirty` and for `dirty + advisory`.

**A2 DoD:** C-5 gates; the limits of the mapping table documented honestly in SKILL.md ("import-name→dist mapping is heuristic beyond the 21-entry table; confidence reflects this"); Python ≥3.11 requirement (tomllib) stated in SKILL.md; advisory shape (C-8) reproduced in SKILL.md.

### Task A3: repo-hygiene-audit — tracked-tree hygiene + release hygiene (stdlib + git ls-files; languages ["*"])

**Files:** `skills/repo-hygiene-audit/{SKILL.md, docs/sp7-freeze-candidates.md, scripts/repo_hygiene_audit.py, scripts/health_common.py, tests/conftest.py, tests/helpers.py, tests/test_repo_hygiene_cli.py, tests/test_repo_hygiene_findings.py, tests/test_repo_hygiene_release.py, tests/test_repo_hygiene_relpaths.py, tests/test_repo_hygiene_idempotent.py, tests/fixtures/...}`

**Extra CLI flags:** none. **Thresholds:** `DEFAULT_THRESHOLDS = {"max_tracked_file_bytes": 1048576}`.

**Git handling:** reuse A1's `_git` helper shape (own copy — leaves are self-contained). `git ls-files -z` = tracked set; `git ls-files -ci --exclude-standard -z` = tracked-but-ignored. Non-git root → git-dependent groups skipped, status line gains `"git": false`, config/release groups still run, exit per normal contract. git binary missing → `ToolError` exit 2.

**Prefix rule (self-audit-critical):** when `--source-prefix` is given, EVERY finding (including release-hygiene findings whose paths are `package.json`, `.github`, `LICENSE`, etc.) is dropped unless its `path` starts with a prefix. Under repo-A self-audit (prefixes = `shared`, `scripts`, `skills/*/scripts`) this leaf must produce ZERO findings — add the dedicated test `test_prefixed_run_on_own_repo_shape_is_clean` using a fixture mimicking that layout.

**Check groups → findings:**

| Group | Detection | Signal / severity / confidence | metric_name |
|---|---|---|---|
| tracked artifact | tracked path with a part in `{"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}` or name matching `*.pyc`, `*.pyo`, `.coverage`, `.coverage.*`, `.DS_Store`, `*.orig`, `*.rej` | DELETE / medium / high | `tracked_artifact` (value 1.0, thr 0.0) |
| tracked-but-gitignored | `ls-files -ci` entry | DELETE / medium / high | `tracked_ignored` |
| oversized tracked file | tracked file `stat().st_size > max_tracked_file_bytes` | RESTRUCTURE / medium / high | `tracked_file_bytes` (value = size, thr = max) |
| broken symlink | tracked `Path.is_symlink()` and not `Path.exists()` | DELETE / low / high | `broken_symlink` |
| conflicting tool configs | >1 of {`pytest.ini`, `setup.cfg` containing `[tool:pytest]`, `pyproject.toml` containing `[tool.pytest.ini_options]`} — same pattern for ruff {`ruff.toml`, `.ruff.toml`, pyproject `[tool.ruff]`} | RESTRUCTURE / medium / high; path = the SECOND+ config file, symbol = `"pytest-config"` / `"ruff-config"` | `conflicting_configs` (value = count, thr 1.0) |
| version mismatch | collect versions from any of: pyproject `[project].version`, `package.json` `"version"`, first `## X.Y.Z`-style CHANGELOG*.md heading token, `__version__ = "X.Y.Z"` string literal in any top-level `<root>/*/__init__.py`; >1 distinct value → one finding per disagreeing source (path = that file, symbol = `"version"`, evidence_raw lists all sources) | RESTRUCTURE / medium / high | `version_mismatch` (value = distinct count, thr 1.0) |
| missing CI | no `.github/workflows/*.yml|yaml` | RESTRUCTURE / low / high; path `".github"`, symbol `"<ci>"`, line 1 | `ci_missing` |
| missing LICENSE | no root `LICENSE*` | RESTRUCTURE / low / high; path `"LICENSE"`, symbol `"<license>"` | `license_missing` |

**Fixtures:** the dirty tree is built BY THE TEST into tmp via `helpers.make_dirty_repo(tmp_path)` (A1-style pinned git env), containing: a committed `pkg/__pycache__/x.pyc`; a committed `debug.log` with `*.log` in `.gitignore` (tracked-but-ignored); a committed 2048-byte `blob.bin` (the oversize test passes `--config` with `{"max_tracked_file_bytes": 1024}` — keeps the fixture small instead of committing megabytes); a broken symlink `dangling -> nowhere`; `pytest.ini` + pyproject `[tool.pytest.ini_options]` (conflicting configs); pyproject version `1.0.0` vs CHANGELOG.md `## 1.1.0` (mismatch); no `.github`; no LICENSE. `helpers.make_clean_repo(tmp_path)` = minimal compliant repo (LICENSE, `.github/workflows/check.yml`, single pytest config, agreeing versions). Golden findings JSON frozen against the dirty builder (paths are deterministic).

**A3 DoD:** C-5 gates; the prefix-filter test above green; SKILL.md documents `languages: ["*"]` intent, the non-git degradation, and that family-contract checks (version-sync across SKILL.md files etc.) remain per-repo scripts, NOT this skill (design principle: useful on a stranger's repo).

### Task A4: docs-consistency-audit — docs vs reality (stdlib; import-introspection guarded)

**Files:** `skills/docs-consistency-audit/{SKILL.md, docs/sp7-freeze-candidates.md, scripts/docs_consistency_audit.py, scripts/health_common.py, tests/conftest.py, tests/helpers.py, tests/test_docs_consistency_cli.py, tests/test_docs_consistency_findings.py, tests/test_docs_consistency_docstrings.py, tests/test_docs_consistency_relpaths.py, tests/test_docs_consistency_idempotent.py, tests/fixtures/...}`

**Extra CLI flags:** none. **Thresholds:** `DEFAULT_THRESHOLDS = {"docstring_min_percent": None}` — docstring group is OFF unless `--config` sets a number (repo policy, not dogfood tuning; keeps umbrella registration self-audit-neutral).

**Scope:** `*.md` files under root filtered by prefixes (same `_in_scope` rule as A1). All findings signal `LINT`.

**Group 1 — unknown flags in documented commands (confidence medium):** extract fenced blocks tagged `bash|sh|shell|console`; per line (strip leading `$ `), `shlex.split`; if `tokens[0] in {"python","python3"}` and some token ends with `.py` and `(root/token)` exists: introspect. **Introspection guard (side-effect mitigation — import executes top-level code):** first `ast.parse` the target; ONLY import when the module's AST contains an `import argparse` and a top-level `def build_parser`; import via `importlib.util.spec_from_file_location` with `sys.argv` untouched; call `build_parser()`; known flags = union of `a.option_strings` over `parser._actions` (documented private-API pin: argparse has no public enumeration; pin the attribute and add a test that would fail loudly if it vanishes). Doc flags = tokens starting `--` (split at `=`). Unknown flag → finding: path = md file, line = fence's first line, `symbol = <script relpath>`, `metric_name="doc_flag_unknown"`, value 1.0, thr 0.0, severity `medium`, evidence_tool `"argparse"`, evidence_raw names the flag and script. Modules failing the guard are SKIPPED silently (heuristic honesty), never imported.

**Group 2 — dead doc paths (confidence medium):** inline code spans `` `...` `` matching `^[A-Za-z0-9_.\-/]+$`, containing `/`, not containing `://`, with suffix in `{.py,.md,.json,.toml,.cfg,.yml,.yaml,.sh,.js,.txt}`; if `(root/span)` doesn't exist → `metric_name="doc_path_missing"`, severity `low`, symbol = the span.

**Group 3 — stale version pins (confidence high):** package name+version from pyproject `[project]` (name, version) or `package.json`; if neither exists → group skipped. Regex `rf"{re.escape(name)}==(\d+\.\d+\.\d+)"` over md files EXCLUDING `CHANGELOG*.md` (changelogs are historical); mismatch → `metric_name="doc_version_stale"`, value = 1.0, severity `medium`, evidence_raw shows found vs current.

**Group 4 — docstring coverage (only when configured):** per in-scope `*.py` module (prefix-filtered like A1): public defs/classes (`not name.startswith("_")`, includes methods of public classes); `pct = 100*documented/public_total` (modules with 0 public symbols skipped); `pct < docstring_min_percent` → `metric_name="docstring_percent"`, value = round(pct,1), thr = configured, severity `low`, confidence `medium`, symbol `"<module>"`.

**Fixtures:** `fixtures/dirty/` tree with `README.md` (fenced bash block calling `python3 tools/cli.py --root . --no-such-flag`, a span `` `missing/file.py` ``, `mypkg==9.9.9`), `tools/cli.py` (argparse module WITH `build_parser` exposing only `--root/--out`), `tools/sideeffect.py` (argparse import but NO build_parser + a top-level `raise RuntimeError("must never be imported")` — the guard test asserts it is never executed AND no finding is produced for its doc mention), `pyproject.toml` name `mypkg` version `1.0.0`, `pkg/mod.py` with 1 documented / 3 public functions. `fixtures/clean/` mirrors with consistent docs. Goldens for: default run (groups 1-3) and configured run (`{"docstring_min_percent": 80}` adds the docstring finding). The side-effect guard test is MANDATORY:

```python
def test_guard_never_imports_module_without_build_parser(tmp_path):
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out)])
    assert rc == 1  # completes; RuntimeError module was skipped, not imported
```

**A4 DoD:** C-5 gates; guard test green; SKILL.md states the import-introspection caveat verbatim ("targets are imported; only modules defining build_parser and importing argparse are eligible; never point --root at untrusted code you would not import") and the docstring group's opt-in default.

### Task A5: security-audit — pinned bandit wrapper (signal SECURITY; vendors POST-BUMP health_common)

**Files:** `skills/security-audit/{SKILL.md, docs/sp7-freeze-candidates.md, scripts/security_audit.py, scripts/health_common.py  ← POST-BUMP per C-6, tests/conftest.py, tests/helpers.py, tests/test_security_cli.py, tests/test_security_findings.py, tests/test_security_advisory.py, tests/test_security_relpaths.py, tests/test_security_idempotent.py, tests/fixtures/...}`

**EXPECTED-RED in-branch:** `npm run check:vendored` fails with exactly one defect (`skills/security-audit/scripts/health_common.py` differs) — BY DESIGN; INT merges this branch only AFTER the schema-bump commit makes them byte-identical. Every other C-5 gate must be green. Add the in-suite assertion `test_vendored_signals_include_security` (`load HC via importlib; assert {"PERF","SECURITY"} <= HC.SIGNALS`).

**Tool pin:** `bandit==1.9.4`, invoked as `[sys.executable, "-m", "bandit", "-r", *targets, "-f", "json", "-q"]` with `targets` = `[root/p for p in source_prefixes]` (existing dirs only) or `[root]`; `FileNotFoundError`/`ModuleNotFoundError` probe → `ToolError("bandit is not installed; pip install bandit==1.9.4")` exit 2 (probe via `importlib.util.find_spec("bandit")` BEFORE running). Parse stdout JSON `results` (bandit exits 1 on findings — treat exit ∉ {0,1} or unparseable JSON as ToolError; include `errors` array content in the message).

**Mapping table (pin in SKILL.md and code):**

| bandit issue_severity | finding severity | bandit issue_confidence | finding confidence | metric_value |
|---|---|---|---|---|
| HIGH | high | HIGH | high | 3.0 |
| MEDIUM | medium | MEDIUM | medium | 2.0 |
| LOW | low | LOW | low | 1.0 |

Per result: signal `SECURITY`, path = `filename` made root-relative (reuse coverage-gap's `_rel` helper shape), `line_start = line_number`, `line_end = max(line_range)`, `symbol = test_name`, `metric_name = f"bandit_{test_id}"` (stable_id therefore distinguishes rules per file), `metric_value` from severity per table, `metric_threshold = 0.0`, evidence_tool `"bandit"`, evidence_raw `f"{issue_text} [{test_id}]"`, suggested_action `f"Review and remediate {test_id} at {path}:{line}"`.

**Extra CLI flags:** `--advisory-report PATH` (C-8 shape) → per package with vulns: signal `SECURITY`, path = `"pyproject.toml"` if it exists under root else `"<advisory>"`, symbol = package name, `metric_name="dependency_vulnerabilities"`, value = len(vulns), severity per C-8, confidence `high`, evidence_tool `"advisory-report"`. Never any network in-band.

**Fixtures:** `fixtures/dirty/pkg/insecure.py` planting deterministic B-series hits:

```python
import subprocess  # B404

PASSWORD = "hunter2"  # B105


def run(cmd):
    return subprocess.call(cmd, shell=True)  # B602
```

`fixtures/clean/pkg/safe.py` = pure arithmetic. Golden findings frozen from a real pinned-bandit run (W-1 generates, orchestrator verifies stability across two runs). `fixtures/advisory.json` = C-8 example. CLI/contract tests in-process; bandit-missing test monkeypatches `importlib.util.find_spec` to return None.

**A5 DoD:** C-5 gates with the documented check:vendored expected-failure (exactly one defect — paste the gate output in the report); golden bandit findings byte-stable across two runs; SKILL.md documents the pin (`bandit==1.9.4`), the mapping table, the advisory mode, and that this leaf is STANDALONE (not in the umbrella registry) by design.

### Task A6: test-effectiveness-audit — pinned mutmut wrapper (artifact-gated by REQUIRED scope)

**Files:** `skills/test-effectiveness-audit/{SKILL.md, docs/sp7-freeze-candidates.md, scripts/test_effectiveness_audit.py, scripts/health_common.py  ← current main copy (NOT post-bump; emits TEST only), tests/conftest.py, tests/helpers.py, tests/test_test_effectiveness_cli.py, tests/test_test_effectiveness_parsing.py, tests/test_test_effectiveness_findings.py, tests/test_test_effectiveness_relpaths.py, tests/test_test_effectiveness_idempotent.py, tests/fixtures/...}`

**Tool pin:** `mutmut==3.6.0`. CRITICAL VERIFIED QUIRK: mutmut loads config at import time — ALL invocations must run with `cwd=<sandbox>` where `setup.cfg` exists; never invoke it from the target repo root (it would litter `mutants/` there and violate never-mutate).

**Extra CLI flags (REQUIRED — refuses to run unscoped):** `--paths FILE` (newline-separated root-relative `.py` files/dirs to mutate), `--tests-dir REL` (root-relative test dir to copy), `--max-mutants INT`. Missing any → status-error explaining WHY (mutation testing an unscoped repo costs hours; feed it e.g. the top-N hotspot paths) + exit 2. **Thresholds:** `DEFAULT_THRESHOLDS = {"min_kill_rate": 0.8, "mutmut_timeout_seconds": 600, "estimated_mutants_per_def": 8}`.

**Sandbox protocol (verbatim spec):** `work = Path(out_dir)/".mutmut-work"` (wiped per run); copy each `--paths` entry to `work/<same relpath>` and `--tests-dir` to `work/<same relpath>`; write `work/setup.cfg`:

```
[mutmut]
source_paths=<comma-free space-separated list of the copied top-level path entries>
```

**Budget pre-flight:** `print-time-estimates` cannot pre-count (verified — needs an existing mutants dir). Instead: `estimate = (number of ast.FunctionDef/AsyncFunctionDef nodes across scoped files) * estimated_mutants_per_def`; if `estimate > max_mutants` → `ToolError(f"scope too large: ~{estimate} mutants > --max-mutants {max_mutants}; narrow --paths")` exit 2. Then run `[sys.executable, "-m", "mutmut", "run"]` with `cwd=work`, `timeout=mutmut_timeout_seconds` (TimeoutExpired → ToolError), then `[..., "-m", "mutmut", "export-cicd-stats"]`, then capture `[..., "-m", "mutmut", "results"]` stdout. If ACTUAL total (Σ meta keys) > max_mutants, finish but add `"budget_exceeded": true` to the status line (honest disclosure, not a crash).

**Parsing (in-process functions, the coverage-clearing core):**

```python
def parse_results_text(text: str) -> dict[str, str]:
    """'    calc.x_weak__mutmut_1: no tests' -> {key: status}; killed mutants are absent."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if ": " in line and "__mutmut_" in line:
            key, _, status = line.partition(": ")
            out[key] = status.strip()
    return out


def module_totals(work: Path) -> dict[str, int]:
    """mutants/<rel>.py.meta -> {module_rel_path: total_mutants} via exit_code_by_key length."""
    totals: dict[str, int] = {}
    for meta in sorted((work / "mutants").rglob("*.py.meta")):
        rel = meta.relative_to(work / "mutants").as_posix()[: -len(".meta")]
        data = json.loads(meta.read_text(encoding="utf-8"))
        totals[rel] = len(data.get("exit_code_by_key", {}))
    return totals


def key_to_module(key: str) -> str:
    """'pkg.calc.x_weak__mutmut_3' -> 'pkg/calc.py' (dotted module prefix before .x_)."""
    dotted = key.split(".x_", 1)[0]
    return dotted.replace(".", "/") + ".py"
```

Per module: `problems` = results-text keys mapping to it with status in `{"survived", "no tests"}`; `kill_rate = (total - len(problems)) / total` (timeout/suspicious/skipped count as killed — environment-dependent statuses must not flap findings; documented). `kill_rate < min_kill_rate` → finding: signal `TEST`, path = module root-relpath, `symbol="<module>"`, `line_start=line_end=1`, `metric_name="mutation_kill_rate"`, `metric_value=round(kill_rate, 3)`, `metric_threshold=min_kill_rate`, severity `high` if `< 0.5` else `medium`, confidence `high`, evidence_tool `"mutmut"`, evidence_raw = up to 10 entries `key=status` + `…(+N more)`, suggested_action "Strengthen assertions/cases for <module>: surviving mutants listed in evidence". (Per-mutant `file:line+operator` detail requires one `mutmut show` per survivor; pin: run `mutmut show <key>` for at most the first 3 survivors per module and append their `@@ -N` hunk header line numbers to evidence_raw.)

**Fixture package** `fixtures/weakpkg/` (the stable-survivor pattern verified during pre-flight):

```python
# fixtures/weakpkg/src/calc.py
def add(a, b):
    return a + b


def weak(x):
    if x > 10:
        return True
    return True
```

```python
# fixtures/weakpkg/tests/test_calc.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from calc import add


def test_add():
    assert add(1, 2) == 3
```

Verified ground truth for this package under mutmut 3.6.0: 5 mutants total (1 for `add`, 4 for `weak`); `add` mutant killed; all 4 `weak` mutants status `no tests`; cicd-stats `{"killed": 1, "survived": 0, "total": 5, "no_tests": 4, ...}` → `src/calc.py` kill_rate `0.2` → one `TEST` finding, severity `high`. Tests: parsing functions against FROZEN captured fixtures (`fixtures/captured/results.txt`, `fixtures/captured/calc.py.meta`, `fixtures/captured/mutmut-cicd-stats.json` — W-1 captures them from one real run and commits them) + EXACTLY ONE real-mutmut integration test (subprocess, `timeout=180`, asserts the golden finding above; skipped with explicit `pytest.skip("mutmut not installed")` only when `find_spec("mutmut")` is None — locally the orchestrator must have run `pip install mutmut==3.6.0` so it executes).

**A6 DoD:** C-5 gates; the unscoped-refusal exit-2 path tested in-process; sandbox proven side-effect-free (test asserts the FIXTURE tree has no `mutants/` or `setup.cfg` after a run); SKILL.md documents the pin, the budget rationale (runtime), the kill-rate accounting rule, and the registry entry `requires: {"mutation_scope": true}` semantics (umbrella skips it until pipeline plumbing exists).

---

# TRACK B — one orchestrator in repo-audit-refactor-optimize (fully concurrent with Track A)

Repo: `/home/jakub/projects/repo-audit-refactor-optimize`, main, clean, `python3 -m pytest tests/ -q` → 53 passed. Worker cap 3. **Wave 1:** W-A=B1 ∥ W-B=B3 ∥ W-C=B5. **Wave 2 (after B1 merged):** W-A=B2 ∥ W-B=B6 (after B3 — both touch CI) ∥ W-C=B4. **Wave 3 (after B1+B2 merged):** B7. **Tail (orchestrator):** version 0.3.0 + CHANGELOG finalization. All tests use the existing helpers `write_skill`/`write_manifest` and fixtures `sample_manifest`/`python_pytest_repo` in `tests/test_check_skill_requirements.py` — read its top 60 lines first; if `write_skill` does not already accept a version, extend it backward-compatibly (`write_skill(root, name, version=None)` adds `version: {version}` to the frontmatter when set).

### Task B1: version-aware bootstrap (`min_version` + `stale_installed`)

**Files:** Modify `scripts/check_skill_requirements.py` (functions `_extract_skill_name`:381, `_register_skill`:442, `_skill_entry`:494, `build_bootstrap_report`:766), `scripts/skill_bootstrap_manifest.json` (`"version": 1` → `2` — cosmetic, loader never validates it; verified), `tests/test_check_skill_requirements.py`.

- [ ] **Step 1 (failing tests):**

```python
def test_skill_with_old_version_is_stale_installed(tmp_path: Path):
    repo = _python_repo(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest = _lane_manifest("code_health", preferred=["versioned-skill"])
    manifest["skills"]["versioned-skill"]["min_version"] = "0.4.0"
    write_manifest(manifest_path, manifest)
    skills_root = tmp_path / ".agents" / "skills"
    write_skill(skills_root, "versioned-skill", version="0.3.0")

    report = checker.build_bootstrap_report(
        repo_root=repo, manifest_path=manifest_path,
        out_dir=tmp_path / "out", env={"HOME": str(tmp_path)},
    )

    skill = report["skills"]["versioned-skill"]
    assert skill["state"] == "stale_installed"
    assert skill["found_version"] == "0.3.0"
    assert skill["min_version"] == "0.4.0"
    assert report["lanes"]["lane-under-test"]["state"] == "manual"
    assert any("stale" in w.lower() for w in report["warnings"])


def test_skill_meeting_min_version_is_usable(tmp_path: Path):
    # same arrangement with version="0.4.0" -> state "usable_now", lane "full"
    ...


def test_skill_without_version_frontmatter_is_stale_when_min_version_set(tmp_path: Path):
    # write_skill(..., version=None) + min_version "0.1.0" -> "stale_installed"
    # (unparsable/missing version == (0,0,0): we cannot prove freshness — fail closed)
    ...


def test_manifest_without_min_version_behaves_as_today(tmp_path: Path):
    # no min_version key anywhere -> states identical to current behavior ("usable_now")
    ...
```

(The two elided bodies follow the first test verbatim with the stated deltas — write them out fully; `...` here is plan compression, not permission to skip.)

- [ ] **Step 2 (implement):** rename `_extract_skill_name` → `_extract_skill_meta` returning `tuple[str | None, str | None]` (name, version) by scanning the same 20-line head for `name:` and `version:` (keep a thin `_extract_skill_name` wrapper if other callers exist — grep first). `_register_skill` stores `"version": version`. Add `_parse_version(v: str | None) -> tuple[int, int, int]` (split on `.`, first 3 ints; any failure → `(0, 0, 0)`). In `_skill_entry`, after the `usable_now` branch is selected, demote: if `skill_config.get("min_version")` and `_parse_version(discovered.get("version")) < _parse_version(min_version)` → state `"stale_installed"` + `found_version` (the raw string or `"unknown"`) + `min_version` keys; append `f"Skill {skill_name} found at {found} < required {min_version}; treated as stale_installed."` to a new `entry["warnings"]` list which `build_bootstrap_report` folds into report warnings. `stale_installed` ≠ `usable_now` → `_all_usable` False → lanes degrade with zero evaluator changes (verified at line 544).
- [ ] **Step 3:** `python3 -m pytest tests/ -q` → `57 passed` (53 + 4). Commit: `feat(bootstrap): min_version-aware skill resolution with stale_installed state (SP7 B1)`.

### Task B2: stale-root advisory (unreferenced skills)

**Files:** Modify `scripts/check_skill_requirements.py` (`build_bootstrap_report`, `_markdown_report`), `tests/...`.

- [ ] **Step 1 (failing test):** repo+manifest from `_lane_manifest`, `write_skill(skills_root, "orphan-skill")` not referenced by the manifest → `report["unreferenced_skills"] == ["orphan-skill"]`; markdown report contains a `## Unreferenced Skills (advisory)` section listing it; report with no orphans → `[]` and NO such markdown section; `summary.stop_before_discovery` unaffected.
- [ ] **Step 2 (implement):** in `build_bootstrap_report` after `usable_skills = _discover_skills(...)`: `report["unreferenced_skills"] = sorted(set(usable_skills) - set(manifest["skills"]))`; `_markdown_report` appends the advisory section when non-empty. Non-blocking by construction.
- [ ] **Step 3:** suite → `59 passed` (57 + 2). Commit: `feat(bootstrap): advisory unreferenced-skills section (SP7 B2)`.

### Task B3: CI workflow for this repo

**Files:** Create `.github/workflows/check.yml`:

```yaml
name: check

on: [push, pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install Python dependencies
        run: python -m pip install pytest==9.0.3
      - name: Run tests
        run: python -m pytest tests/ -q
```

- [ ] Validate statically (actionlint if available, else careful read); CI cannot run before a human pushes — record in the run report. Commit: `ci: pytest gate on push (SP7 B3)`.

### Task B4: run-report contract (docs-only; gate-bearing)

**Files:** Modify `SKILL.md` (Verification stage + Operating Model), `references/pipeline.md`, `references/verification.md`.

- [ ] **Step 1:** In `references/pipeline.md`, after the artifact-layout block (line ~75), add verbatim:

```markdown
## Run Report (required artifact)

Every orchestration run MUST end by writing a run report into the AUDITED repository at:

    docs/audits/<YYYYMMDDTHHMMSSZ>/run_report.json
    docs/audits/<YYYYMMDDTHHMMSSZ>/run_report.md

(timestamp = run start, UTC, compact ISO). `run_report.json` minimal schema (all keys required):

- `schema_version`: 1
- `repo_root`: absolute path audited
- `started_utc`, `finished_utc`: ISO timestamps
- `orchestrator_skill_version`: this SKILL.md frontmatter version
- `lanes`: {lane_name: state} from the bootstrap report
- `findings_totals`: {signal: count} across all diagnosis lanes
- `backlog`: {"accepted": N, "deferred": N, "coverage_gated": N}
- `batches`: [{"id", "signal", "files", "result": "accepted"|"discarded", "evidence"}]
- `verification`: [{"command", "exit_code"}]
- `warnings`: [str]

`run_report.md` is the human rendering of the same content. A run that did not write both
files is NOT complete: the Verification stage fails closed on their absence.
```

- [ ] **Step 2:** In `SKILL.md` Verification stage, add: "Write the run report (see references/pipeline.md, Run Report). Verification fails closed if `docs/audits/<run-id>/run_report.json` + `.md` are absent or missing schema keys — omission is a gate failure, not a warning." Mention the artifact in the Overview stage list.
- [ ] **Step 3:** suite still green (docs-only; `59 passed`). Commit: `docs(contract): committed run-report artifact required per run (SP7 B4)`.

### Task B5: remediation-playbook RESTRUCTURE deepening

**Files:** Modify `references/remediation-playbook.md` (after the Signal Procedures table, line ~25).

- [ ] **Step 1:** Append verbatim:

```markdown
## RESTRUCTURE at architecture scale

Use these when a RESTRUCTURE finding names a cycle, god module, layer violation, or
hotspot/coupling cluster (hotspot-audit). One procedure per batch; each has a MECHANICAL
verification condition — if it does not hold after the batch, discard the batch.

| Procedure | When | Mechanics | Verify (mechanical) |
|---|---|---|---|
| Dependency inversion at the cycle's weakest edge | `import_cycle_size` finding | Pick the cycle edge with the fewest imported symbols (count names actually used); extract those symbols' contract into a new lower-layer module (or Protocol); point both ends at it | structure-audit re-run: cycle count STRICTLY decreased; no new cycles; suite green |
| Interface extraction | god module by fan-in (`fan_in` finding) | Identify the symbol subsets distinct caller groups use; extract each subset into a facade module; rewire callers group by group, one commit per group | structure-audit re-run: target module fan-in strictly decreased; no caller behavior change (suite green) |
| Module split / merge | god module by fan-out, or temporal-coupling pair (`temporal_coupling_ratio`) | Split: cluster the module's defs by shared imports + co-change, move one cluster out. Merge: co-changing pair whose split serves no boundary → merge into one module, keep a deprecation re-export | structure-audit re-run: `fan_out` below threshold or strictly decreased / coupling pair gone next hotspot-audit window; suite green |
| Strangler fig | legacy module slated for replacement (hotspot + low kill-rate + DELETE cluster) | Stand up the replacement module behind the old entry points; migrate one caller per batch; old module shrinks to a shim | per batch: old module fan-in strictly decreases; final batch: dead-code-audit emits DELETE for the shim and it is removed; suite green throughout |

Standing rule: architecture batches are coverage-gated like all others — characterize-first
on any touched file carrying a TEST finding.
```

- [ ] **Step 2:** suite green (docs-only). Commit: `docs(playbook): arch-scale RESTRUCTURE procedures with mechanical verification (SP7 B5)`.

### Task B6: packaging-parity gates (version-sync check + CHANGELOG)

**Files:** Create `scripts/check_release.py`, `CHANGELOG.md`; modify `.github/workflows/check.yml` (after B3), `tests/test_check_release.py` (new file).

- [ ] **Step 1 (failing tests, new module `tests/test_check_release.py`):** in-process tests importing the script via importlib: pass-case (tmp tree with SKILL.md `version: 1.2.3` + CHANGELOG containing `## 1.2.3` → exit 0); missing CHANGELOG heading → exit 1, defect string names it; non-semver frontmatter → exit 1; missing manifest file → exit 1.
- [ ] **Step 2 (implement `scripts/check_release.py`):** stdlib; SOURCE OF TRUTH = `SKILL.md` frontmatter `version:` (reuse repo-A's `frontmatter()` parsing shape, `check_release.py:48-61` of repo-audit-skills, reimplemented locally); checks: semver regex `^\d+\.\d+\.\d+$`; `CHANGELOG.md` exists and contains a `## <version>` heading; `scripts/skill_bootstrap_manifest.json` parses as JSON with `skills`+`lanes`; `--root` flag (default repo root) so tests run on tmp trees; JSON pass/fail stdout, exit 0/1.
- [ ] **Step 3:** Create `CHANGELOG.md` with `## 0.2.0` (current state summary: SP5 rewire) and `## 0.1.0` (initial) entries. Add CI step after tests: `- name: Release checks` / `run: python scripts/check_release.py`. Suite green (59 + new ~4 = `63 passed`). Commit: `feat(release): SKILL.md-sourced version-sync gate + CHANGELOG (SP7 B6)`.

### Task B7: manifest entries + lanes for the six new leaves (names FROZEN per C-1; name-based late binding makes this safe concurrent with Track A)

**Files:** Modify `scripts/skill_bootstrap_manifest.json`, `scripts/check_skill_requirements.py` (one evaluator registration), `tests/test_check_skill_requirements.py`.

**Pinned lane shapes:**

- NEW lane `"hygiene"`: `{"always": true, "lane_type": "audit", "preferred": ["repo-hygiene-audit"], "fallback": [], "optional": ["dependency-audit", "docs-consistency-audit"], "manual_fallback": "Review repo hygiene manually (tracked artifacts, configs, release files) when the leaf is unavailable.", "blocking": false}` — repo-hygiene is language-agnostic (always); dependency/docs ride along as optionals so a missing optional never degrades the lane.
- NEW lane `"security"`: `{"when": {"python": true}, "lane_type": "audit", "preferred": ["security-audit"], "fallback": [], "manual_fallback": "Perform a manual security review; the bandit-based leaf is unavailable.", "blocking": false}`.
- `code-health-python` lane gains `"optional": ["hotspot-audit"]` (prioritization input, not a health gate).
- `test-python` lane gains `"optional": ["test-effectiveness-audit"]` (adding it to `fallback` would wrongly require it for the degraded pair).
- NEW generic evaluator: `_LANE_EVALUATORS["audit"] = lambda lane, skills, profile: _evaluate_preferred_fallback_lane(lane, skills, "Preferred audit skill unavailable; using fallback.")` — one line + tests; without it, `lane_type: "audit"` would fall into the orchestration evaluator with an unknown-lane-type warning (verified lines 674-680).
- 6 new skill entries, all `{"priority": "preferred", "source_type": "user-local", "install_source": null, "manual_fallback": "Part of repo-audit-skills v0.4.0+; install via its node installer.", "restart_required_if_installed": true, "min_version": "0.4.0"}` (dogfoods B1: until INT releases 0.4.0 and the human installs it, these resolve missing or stale — correct and intended). Add `"min_version": "0.3.0"` to the 8 existing repo-audit-skills-family entries (code-health-audit-pipeline, the 5 leaves, coverage-gap-audit, test-audit umbrella? — exactly the entries whose manual_fallback already says v0.3.0+).
- [ ] **Step 1 (failing tests):** hygiene lane full with only repo-hygiene installed + selected grows when optionals installed; security lane manual on a python repo without the skill, full with it; production-manifest test updates (lane count 8, skill count 22, the new lane shapes asserted literally).
- [ ] **Step 2:** implement manifest + evaluator registration. Suite green (63 + ~5 = `68 passed`; record exact).
- [ ] **Step 3:** Commit: `feat(manifest): hygiene+security lanes, hotspot/test-effectiveness optionals, min_version pins (SP7 B7)`.

### Track B tail (orchestrator): version + changelog

- [ ] `SKILL.md` frontmatter `0.2.0` → `0.3.0`; `CHANGELOG.md` gains `## 0.3.0` (B1-B7 summary); `python3 scripts/check_release.py` → pass; full suite green; README touch if it names a version. Commit: `release: v0.3.0 — version-aware bootstrap, run-report contract, new-leaf lanes (SP7 B)`. **Do NOT push.**

**Track B DoD:** suite `68 passed` (exact number recorded); CI file statically valid; `check_release.py` pass; run report of the orchestrator session (its own evidence summary) delivered in the final message — Track B does NOT write into repo-A or repo-C.

---

# TRACK INT — serial integration orchestrator in repo-audit-skills (starts after A1–A4 report done)

Operates on MAIN working tree at `/home/jakub/projects/repo-audit-skills` (no worktree). Worker cap 2 (workers only for mechanical edits; INT itself runs all gates). PINNED ORDER: **gate-harden (INT-1) → A1 → A3 → A2 → A4 → [schema bump] → A5 → A6 → release**. Rationale: the gate-harden lands first so every merge runs under the equality-style check:selfaudit; A1 first of the merges (no registry edit — suite registration only); A3 next (carries the one umbrella code change, wildcard selection, merged while the registry is still small); A2/A4 follow (registry-registered, A4 last of the four because its md-scanning has the highest self-audit adjudication likelihood); A5/A6 strictly after the schema bump (A5's vendored copy must match; A6's registry entry rides the same registry-edit pattern).

### INT-0: pre-flight (any failure → STOP and report)

- [ ] repo-A main clean; `npm install`; `npm run check` fully green; `python3 -m pytest --collect-only -q` → `461 tests collected` (+ any human-merged drift — record); baseline 104; SUITES length 11. A1–A4 orchestrators reported done with C-5 evidence; their branches exist.

### INT-1: harden check:selfaudit — stale-baseline detection (TDD; lands BEFORE any merge)

**Why:** `scripts/check_self_audit.py` is a one-way ratchet (pre-flight row 3): it fails only on findings missing from the baseline, so baseline entries whose findings no longer exist pass silently and the baseline drifts stale. Hardened behavior: after the existing new-findings check, if the baseline contains identity tuples (`{leaf, metric, path, symbol}` — the gate's stable ids; entries carry no other keys, verified) absent from the snapshot, FAIL listing them with instructions to ratchet the baseline down in the same commit. The testability mechanism mirrors the house pattern of `check_coverage_gap.py:122-135` (an injection flag that bypasses the live audit run, "testing/debugging only").

**Files:** Modify `scripts/check_self_audit.py`; create `tests/test_check_self_audit.py` (new module; basename unique repo-wide — verified no existing test references this script).

- [ ] **Step 1 (failing tests, verbatim):**

```python
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_self_audit.py"

FINDING_A = {"leaf": "complexity", "metric": "cyclomatic_complexity", "path": "scripts/x.py", "symbol": "f"}
FINDING_B = {"leaf": "quality", "metric": "lint_errors", "path": "scripts/y.py", "symbol": "<module>"}


def _run(tmp_path, capsys, snapshot, baseline):
    spec = importlib.util.spec_from_file_location("check_self_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    snap = tmp_path / "snapshot.json"
    base = tmp_path / "baseline.json"
    snap.write_text(json.dumps(snapshot))
    base.write_text(json.dumps(baseline))
    rc = mod.main(["--snapshot", str(snap), "--baseline", str(base)])
    return rc, json.loads(capsys.readouterr().out)


def test_stale_baseline_entry_fails_with_ratchet_message(tmp_path, capsys):
    rc, payload = _run(tmp_path, capsys, [FINDING_A], [FINDING_A, FINDING_B])
    assert rc == 1
    assert payload["status"] == "fail"
    assert payload["stale_baseline"] == [FINDING_B]
    assert "same commit" in payload["message"]


def test_equal_snapshot_and_baseline_passes(tmp_path, capsys):
    rc, payload = _run(tmp_path, capsys, [FINDING_A, FINDING_B], [FINDING_A, FINDING_B])
    assert rc == 0
    assert payload["status"] == "pass"


def test_new_finding_still_fails(tmp_path, capsys):
    rc, payload = _run(tmp_path, capsys, [FINDING_A, FINDING_B], [FINDING_A])
    assert rc == 1
    assert payload["new_findings"] == [FINDING_B]
```

  Run: `python3 -m pytest tests/test_check_self_audit.py -q` → Expected: `3 failed` (each with `TypeError: main() takes 0 positional arguments but 1 was given` — the current `main()` at `check_self_audit.py:14` accepts no argv and has no injection mode).

- [ ] **Step 2 (implement; minimal diff to the current 39-line script):** add `import argparse`; change `def main() -> int:` to `def main(argv: list[str] | None = None) -> int:` with parser flags `--snapshot` and `--baseline` (both "testing/debugging only", mirroring `check_coverage_gap.py`). When `--snapshot` is absent, keep the existing `subprocess.run([sys.executable, str(ROOT / "scripts" / "self_audit.py")], ...)` and read `ROOT / "scripts" / "self_audit_snapshot.json"`; otherwise read the given paths. Keep the existing new-findings block byte-for-byte, then append:

```python
    cur = {tuple(sorted(d.items())) for d in current}
    stale = [dict(t) for t in sorted(base - cur)]
    if stale:
        print(
            json.dumps(
                {
                    "status": "fail",
                    "stale_baseline": stale,
                    "message": "baseline entries no longer produced by the audit; "
                    "remove them from scripts/self_audit_baseline.json "
                    "in the same commit",
                },
                indent=2,
            )
        )
        return 1
```

  Run: `python3 -m pytest tests/test_check_self_audit.py -q` → Expected: `3 passed`.

- [ ] **Step 3 (gate on real state):** `npm run check:selfaudit` → must still PASS on main at the base SHA (snapshot equals baseline-104 there). If it reports `stale_baseline`, main has drifted since the pre-flight — ratchet `scripts/self_audit_baseline.json` down in this same commit and record the removed entries. `python3 -m pytest --collect-only -q` → `464 tests collected` (461 + 3). Commit: `feat(gates): check:selfaudit fails on stale baseline entries (SP7 INT-1)`.

**Interaction (binding for all later INT tasks):** every INT merge/fix commit that removes findings present in the baseline must ratchet the baseline down in the SAME commit — the hardened gate turns silent baseline drift into a hard failure. Track A branches fork from the base SHA and keep the one-way script in-branch; this equality-style gate governs main only, from INT-1 onward.

### INT-2..5: per-merge protocol (run once per leaf, in the pinned order; ~30 min each)

For `<leaf>` ∈ A1 `hotspot-audit`, A3 `repo-hygiene-audit`, A2 `dependency-audit`, A4 `docs-consistency-audit`:

- [ ] **Step 1:** `git merge --no-ff sp7/<leaf>` (conflicts impossible by partition; any conflict = contract breach → STOP).
- [ ] **Step 2:** `python3 -m pytest skills/<leaf>/tests -q` → green; `python3 -m pytest --collect-only -q` → previous + leaf count, zero errors.
- [ ] **Step 3:** Edit `scripts/check_coverage_gap.py` SUITES: append `"skills/<leaf>/tests",` (final list order = existing 11 then merge order; final length 17 after INT-8).
- [ ] **Step 4 (registration, leaf-specific):**
  - hotspot-audit: NONE (standalone; C-7).
  - repo-hygiene-audit: add registry entry `{"name": "repo-hygiene", "skill": "repo-hygiene-audit", "script": "repo-hygiene-audit/scripts/repo_hygiene_audit.py", "languages": ["*"], "findings_file": "repo-hygiene_findings.json"}` AND the wildcard change in `code_health_pipeline.py` `select_leaves` (TDD, umbrella suite):

```python
def select_leaves(leaves: list[dict], languages: list[str]) -> list[dict]:
    wanted = set(languages)
    return [
        leaf
        for leaf in leaves
        if "*" in leaf.get("languages", []) or wanted & set(leaf.get("languages", []))
    ]
```

  with a new umbrella test `test_select_leaves_wildcard_always_selected` (registry stub with `languages: ["*"]` selected for `["python"]` and `["rust"]`).
  - dependency-audit: registry entry `{"name": "dependency", "skill": "dependency-audit", "script": "dependency-audit/scripts/dependency_audit.py", "languages": ["python"], "findings_file": "dependency_findings.json"}`.
  - docs-consistency-audit: registry entry `{"name": "docs-consistency", "skill": "docs-consistency-audit", "script": "docs-consistency-audit/scripts/docs_consistency_audit.py", "languages": ["python"], "findings_file": "docs-consistency_findings.json"}` (the `name`/`findings_file` keep the LEAF id `docs-consistency`, matching the family convention, e.g. `coverage-gap` ↔ `coverage-gap-audit`).
- [ ] **Step 5 (freeze adjudication):** read `skills/<leaf>/docs/sp7-freeze-candidates.md`; run `npm run check:selfaudit`. PREFER FIX (dispatch a worker for a surgical fix inside the leaf, re-gate). A freeze requires: per-finding entry appended to `scripts/self_audit_frozen.md` (existing per-finding format) + matching baseline entry. >10 new findings from one registration = STOP and report (architectural conflict; never blanket-freeze). RATCHET-DOWN (INT-1 interaction): if a surgical fix removes findings that were in the baseline, the hardened gate reports them as `stale_baseline` — remove exactly those entries from `scripts/self_audit_baseline.json` in the same commit.
- [ ] **Step 6:** `npm run check` FULLY green (check:coverage now includes the new suite; check:release still ignores the unlisted skill — expected until INT-9). Commit: `merge(sp7): <leaf> + suite registration [+ registry] (SP7 INT)`.

### INT-6: schema bump

- [ ] **Step 1 (TDD):** extend `tests/test_health_common.py` next to line 65: `assert "PERF" in hc.SIGNALS` and `assert "SECURITY" in hc.SIGNALS` → run → FAIL.
- [ ] **Step 2:** apply C-6 to `shared/health_common.py` (only that hunk). Re-vendor ALL leaves: `for d in skills/*/scripts; do cp shared/health_common.py "$d/health_common.py"; done` (14 dirs at this point). `npm run check:vendored` → pass; root suite green; `npm run check` green (the +2 frozenset lines change no audited metrics — verify via check:selfaudit, expect zero new AND zero stale: baseline identity tuples carry no line numbers, so the line shift cannot strand entries).
- [ ] **Step 3:** Commit: `feat(schema): SIGNALS += PERF, SECURITY; re-vendor all leaves (SP7 INT)`.

### INT-7: merge A5 (security-audit)

- [ ] Per-merge protocol Steps 1–3 and 5–6 (suite → SUITES 16th entry). Registration: NONE (standalone per C-7). Verify `cmp shared/health_common.py skills/security-audit/scripts/health_common.py` → identical (A5 vendored the post-bump file; if not, STOP — A5 contract breach). CI edit: add `bandit==1.9.4 \` to the pip install list in `.github/workflows/check.yml` (A5's integration tests need it in CI). Local: `pip install bandit==1.9.4` before running its suite. Commit: `merge(sp7): security-audit + suite + CI bandit pin (SP7 INT)`.

### INT-8: merge A6 (test-effectiveness-audit)

- [ ] Per-merge protocol; SUITES → 17. Registration: registry entry `{"name": "test-effectiveness", "skill": "test-effectiveness-audit", "script": "test-effectiveness-audit/scripts/test_effectiveness_audit.py", "languages": ["python"], "findings_file": "test-effectiveness_findings.json", "requires": {"mutation_scope": true}}`. Add an umbrella test pinning the fail-safe skip: running the pipeline without the artifact lists `{"leaf": "test-effectiveness", "reason": "requires mutation_scope artifact"}` in `skipped` and exits without gating. CI edit: add `mutmut==3.6.0 \` to the pip list; local `pip install mutmut==3.6.0` before its suite. Commit: `merge(sp7): test-effectiveness-audit + suite + registry (requires mutation_scope) + CI mutmut pin (SP7 INT)`.

### INT-9: release 0.4.0 (atomic)

- [ ] **Step 1:** `package.json` version `0.4.0`; bump ALL 16 `skills/*/SKILL.md` frontmatter `version: 0.4.0` (the 10 existing were 0.3.0, the 6 new were authored at 0.3.0 per C-5).
- [ ] **Step 2:** `scripts/check_release.py`: append the 6 new entries to BOTH `REQUIRED_SKILLS` (`"<dir>": "<dir>"`) and `REQUIRED_SCRIPTS` (`"<dir>": ["scripts/<script>.py"]` per C-1). `bin/install-repo-audit-skills.js`: append the 6 dir names to the `skills` array. `package.json` description: extend with "hygiene/dependency/docs/security/hotspot/test-effectiveness leaves". README: add the 6 skills to its list.
- [ ] **Step 3 (full gate):** `npm run check` fully green (check:selfaudit now equality-style: zero new AND zero stale); `node bin/install-repo-audit-skills.js --list` → version `0.4.0`, 16 skills; `python3 -m pytest --collect-only -q` → `461 + 3 (INT-1) + Σ(new leaf tests) tests collected`, zero errors; `python3 -m pytest -q` green. Expected final numbers per C-9 — state each explicitly in the run report.
- [ ] **Step 4:** Commit: `release: v0.4.0 — six new audit leaves (hotspot-audit, dependency-audit, repo-hygiene-audit, docs-consistency-audit, security-audit, test-effectiveness-audit)`. **Do NOT push, do NOT tag, do NOT `npm publish`.**

### INT-10: run report

- [ ] Write `docs/self-audit/2026-06-sp7-integration-run-report.md`: per-merge gate outputs, adjudication decisions (every freeze with rationale, target zero), every baseline ratchet-down (stale entries removed, with the commit that removed them), schema-bump evidence, final numbers table (C-9), root collection count, worktree cleanup note (`git worktree remove` each `../ras-sp7-*` AFTER its branch is merged; keep branches for the human). Commit it. **Track INT DoD = INT-0..10 all checked with evidence; check:selfaudit equality holds at the end (baseline == snapshot, zero stale entries); nothing pushed.**

---

# TRACK C — perf-optimization skill in perf-benchmark-skill (+ serialized repo-B follow-up)

**GATE (hard):** start ONLY after (1) the human confirms SP6 converged in `/home/jakub/projects/perf-benchmark-skill` and (2) Track B is merged in repo-B. Worker cap 2.

**C-0: SP6 drift gate (numbered pre-flight; SP6 was in flight when this plan was written — the pinned interfaces in pre-flight row 9 are normative only as of the SP6 plan text):**

1. **State + suite:** `git -C /home/jakub/projects/perf-benchmark-skill log --oneline -3` (record); `python3 -m pytest tests/ -q` in that repo → green, record the exact count.
2. **Findings interface:** read `scripts/perf_benchmark/findings.py` (e.g. `sed -n '1,160p'`) and diff against the pins: findings-out key set exactly `id,leaf,signal,severity,path,location,metric,evidence,confidence,suggested_action`; `leaf == "perf-benchmark"`; `signal == "PERF"`; `id = sha1("perf-benchmark|<path>|<workload>|<metric>")[:16]`; sort `(path, metric.name)`.
3. **Ledger interface:** read `scripts/perf_benchmark/ledger.py` and diff: JSONL record keys exactly `{"timestamp_utc","tier","rubric_total","wall_time_mean","dimensions"}`; compare block `{"vs_last","vs_best"}`; corrupt lines skipped with warning.
4. **CLI + summary interface:** read `scripts/perf_benchmark/reporting.py` and run `python3 scripts/perf_benchmark_pipeline.py --help` (the converged CLI defines `--baseline-ledger`, `--max-cv`, `--findings-out` at lines 677/691/705 as of this writing) and diff: those three flags exist with unchanged meaning; summary keys `environment` (`cpu_model,kernel,governor,smt,load_avg_1m,python_version,timestamp_utc`), `wall_time_percentiles` (`p50,p95,p99`), and `ledger_regressions`; noise tier string exactly `"N/A (noise)"`; the Algorithmic Scaling dimension's exact name and metric name (feeds `ALGORITHMIC_METRIC_SUBSTRINGS` in C2).
5. **STOP rule:** ANY material drift — a key added/removed/renamed, a changed signal value, a changed tier string, a missing/renamed CLI flag — means STOP: write a side-by-side diff (pinned value ↔ found value, with file:line) and present it to the human for explicit sign-off BEFORE writing any C2/C3 fixture or the C2 constants block. Cosmetic drift (docstrings, internal helper names, unrelated code movement) does not gate but is still recorded in the report.

Wave 1: W-A=C1 ∥ W-B=C2. Wave 2: W-A=C3. Tail: C4 (repo-B, serialized) + version/README.

### Task C1: skill scaffold + optimization playbook

**Files (perf repo):** Create `perf-optimization/SKILL.md` (frontmatter `name: perf-optimization`, `version: 0.1.0`), `perf-optimization/references/optimization-playbook.md`.

- [ ] **SKILL.md workflow (pin this structure):** Inputs = a PERF findings file (`--findings-out` shape) + optionally the JSONL ledger + the before-run `benchmark_summary.json`. Stages: (1) **Algorithmic STOP gate** — if any finding's dimension is Algorithmic Scaling, it is the only permissible candidate; no constant-factor work until fixed. (2) **Select** — `scripts/select_candidate.py` (deterministic; below). (3) **One bounded change per iteration** — single dimension, single file-set, TDD, suite green. (4) **Verify** — re-run the SP6 pipeline (same tier/sizes/machine), then `scripts/verify_win.py`; ACCEPT = median (p50) win ≥ 5% AND no `"N/A (noise)"` timing dimension in either run (CV ≤ 5% gate) AND environment fingerprints match (excluding `timestamp_utc`, `load_avg_1m`) AND suite green AND no other dimension drops ≥1 tier; REJECT = discard the change entirely (`git checkout -- .`), record the numbers. (5) **Ledger** — append accepted runs via `--baseline-ledger`; an empty-candidate round terminates with "evaluated, no feasible low-risk win" + evidence (valid terminal outcome).
- [ ] **optimization-playbook.md — write this actual table** (metric → technique catalogue keyed to diagnostic tiers; tier names from the SP6 pipeline: `fast` = wall-time/scaling only, deeper tiers add valgrind dims):

```markdown
| Diagnostic tier | Dimension / metric | First-line techniques (in order) | Escalation |
|---|---|---|---|
| fast | Algorithmic Scaling (growth curve) | incremental maintenance over recompute; process deltas not history; dict/set lookup over scan; bound per-update work to changed inputs | redesign data flow; precompute indices |
| fast | Wall-time median (p50) | hoist invariants out of loops; kill redundant passes/copies; batch syscalls/IO; early-exit dominant branches | numpy vectorization / numba JIT (only after the above) |
| fast | Tail latency (p95/p99 spread) | find the tail cause: lazy init on first hit, GC pauses, pathological inputs; fix the cause, never average it away | cap input pathology; pre-warm; arena/object reuse |
| deep (cachegrind) | L1/LLC miss rate | contiguous layouts (arrays over object graphs); loop blocking/fusion; hot/cold field splitting; shrink working set | structure-of-arrays rewrite |
| deep (massif/tracemalloc) | heap peak / alloc churn | reuse buffers in loops; generators over materialized lists; __slots__/frozen dataclasses for hot objects; cap retained history | streaming redesign |
| deep (callgrind/perf) | CPU inclusive cost / IPC | remove interpreter overhead in hot loops (local variable caching, fewer attribute lookups); fold repeated parsing; memoize pure hot calls | C extension boundary / algorithm change |
| deep (perf) | branch-miss rate | sort/partition data so branches are predictable; replace data-dependent branches with arithmetic or table lookup; move rare cases out of the hot loop | branchless rewrite of the kernel |
```

  plus Standing Rules (mirror SP6's perf-remediation-playbook: STOP gate, one dimension per batch, measure-before/after same fingerprint, ≥5% ratchet, coverage gate, honest no-win).
- [ ] Commit: `feat(skill): perf-optimization scaffold + optimization playbook (SP7 C1)`.

### Task C2: deterministic candidate selection (TDD)

**Files:** Create `perf-optimization/scripts/select_candidate.py`, `perf-optimization/tests/test_select_candidate.py`, `perf-optimization/tests/fixtures/findings_*.json`.

- [ ] **Step 1 (failing tests):** fixtures = synthetic PERF findings files (pre-flight row 9 shape). Goldens: (a) mixed severities → highest severity first; (b) equal severity → higher `metric.value/metric.threshold` ratio first (threshold 0 → treat ratio as `metric.value`); (c) any finding whose `metric.name` matches the algorithmic-scaling metric (constants block `ALGORITHMIC_METRIC_SUBSTRINGS = ("scaling",)` — re-pinned at C pre-flight) wins regardless of severity (STOP gate); (d) tie → `(path, metric.name)` order; (e) empty/all-PASS input → exit 1, `{"status": "no_candidates"}`; (f) malformed JSON → exit 2. Output: `{"status": "ok", "candidate": {"id", "path", "metric_name", "severity", "ratio", "stop_gate": bool}}` to stdout AND `--out FILE`; byte-identical across runs.
- [ ] **Step 2 (implement):** stdlib argparse `--findings PATH --out PATH`; sort key `(not stop_gate, -severity_rank, -ratio, path, metric_name)` with `severity_rank = {"high": 3, "medium": 2, "low": 1, "info": 0}`.
- [ ] **Step 3:** perf-repo suite green (record count). Commit: `feat(select): deterministic PERF candidate selection with algorithmic STOP gate (SP7 C2)`.

### Task C3: win verification wrapper (TDD; NO real benchmarking in tests)

**Files:** Create `perf-optimization/scripts/verify_win.py`, `perf-optimization/tests/test_verify_win.py`, `perf-optimization/tests/fixtures/summary_*.json` (+ `ledger_*.jsonl`).

- [ ] **Step 1 (failing tests — five golden verdicts from synthetic summaries):**
  1. clean win: before p50 `2.0`, after p50 `1.8` (10% win), identical fingerprints, all tiers PASS, `--suite-exit-code 0` → verdict `accept`, exit 0.
  2. noisy: after summary's wall-time stability dimension tier `"N/A (noise)"` (CV 8%) → `reject`, reasons contain `"noise"`, exit 1.
  3. fingerprint mismatch: differing `governor` → `reject`, reasons contain `"fingerprint"` (and the test asserts differing `timestamp_utc`/`load_avg_1m` alone do NOT reject).
  4. regression: after p50 `2.2` → `reject`, reasons contain `"median"`; also a dimension dropping PASS→WARN with a winning median → `reject`, reasons contain `"tier"`.
  5. suite red: `--suite-exit-code 1` → `reject`, reasons contain `"suite"`.
  Plus: `--ledger` given → verdict JSON echoes the ledger's `vs_last` block (read-only; corrupt ledger line → warning, not crash — mirror SP6 T7 semantics).
- [ ] **Step 2 (implement):** stdlib argparse `--before S.json --after S.json --suite-exit-code INT [--min-win 5.0] [--ledger PATH] --out verdict.json`; checks in the fixed order median→noise→fingerprint→tier-drops→suite (report ALL failed reasons, not first-only); fingerprint keys compared: `cpu_model, kernel, governor, smt, python_version`; tier order `FAIL < WARN < PASS` (`"N/A (noise)"` = incomparable → noise rejection); verdict JSON `{"verdict": "accept"|"reject", "median_win_percent": float, "reasons": [...], "vs_last": {...}|null}`; exit 0 accept / 1 reject / 2 error.
- [ ] **Step 3:** suite green. Commit: `feat(verify): SP6-pipeline win verdict wrapper (SP7 C3)`.

### Task C4: repo-B follow-up (single serialized commit, AFTER Track B merged)

**Files (repo-B):** Modify `scripts/skill_bootstrap_manifest.json`, `tests/test_check_skill_requirements.py`, `CHANGELOG.md`, `SKILL.md`.

- [ ] Manifest: performance lane `"fallback": ["perf-optimization"]`; new skill entry `"perf-optimization": {"priority": "preferred", "source_type": "user-local", "install_source": null, "manual_fallback": "Optimize manually per the perf-benchmark remediation playbook ratchet.", "restart_required_if_installed": true, "min_version": "0.1.0"}`. Tests: both installed → performance lane `full`, selected `["perf-benchmark", "perf-optimization"]`; only perf-benchmark → `degraded` + exact warning `"Optimization skill missing; lane remains benchmark-first."` (code path pre-verified at `check_skill_requirements.py:626`). SKILL.md `0.3.0` → `0.3.1`; CHANGELOG `## 0.3.1`; `python3 scripts/check_release.py` pass; suite green (record count). Commit in repo-B: `feat(manifest): perf-optimization joins the performance lane (SP7 C4)`.

### Track C tail

- [ ] perf repo: README mention of the second skill dir; perf-optimization SKILL.md cross-references `references/perf-remediation-playbook.md` (SP6) as the execution discipline and this playbook as the technique catalogue. Perf repo suite green; repo-B suite green. **Track C DoD:** C1–C4 evidence (golden verdict outputs pasted, drift list from pre-flight re-verification, both repos' suite counts); nothing pushed in either repo.

---

# Global schedule & Definition of Done

```
batch 1 (5 concurrent sessions):  A1  A2  A3  A4  B
batch 2 (anytime; merges wait):   A5  A6
after A1–A4 report done:          INT   (serial: gate-harden→A1→A3→A2→A4→bump→A5→A6→0.4.0)
after human SP6-confirm + B done: C     (then C4 after B merged — serialized in repo-B)
```

**Global DoD (the human's acceptance checklist):**
1. repo-A at v0.4.0 with 16 skills, 17 suites, `npm run check` fully green, installer lists 16, root collection 461+3+Σ clean, baseline == snapshot under the hardened equality gate (104 − fixed + adjudicated-only freezes, each freeze individually justified), coverage baseline 2 (C-9).
2. SIGNALS = C-6 verbatim, vendored 16× byte-identical.
3. repo-B at v0.3.0 (then 0.3.1 after C4): stale_installed state, unreferenced-skills advisory, CI, run-report contract, RESTRUCTURE arch procedures, release gate + CHANGELOG, lanes for all six new leaves with min_version pins.
4. perf repo: perf-optimization 0.1.0 skill dir with playbook + deterministic select/verify scripts, all goldens green, zero real benchmarking in tests.
5. Every track's run report delivered; every commit local; NOTHING pushed, tagged, or released anywhere.
6. All six worktrees removed after their merges; branches retained.

---

# Launch blocks (paste ONE per fresh Opus session)

## Launch A1 — hotspot-audit

```
You are the ORCHESTRATOR (Opus) for SP7 leaf A1 hotspot-audit. You own ONLY worktree
/home/jakub/projects/ras-sp7-hotspot-audit on branch sp7/hotspot-audit, and within it ONLY
skills/hotspot-audit/**. Coordinate ONLY, never implement. Workers: OpenCode DeepSeek v4 Pro Max
via opencode-worker-bridge (one file-backed packet per worker, own git worktree each), cap 2.
Automatic ONE-WAY fallback to native Opus subagent workers ONLY on infrastructure dispatch
failure (credits/quota/auth/bridge unreachable); a gate-failing CHANGE is discard/retry, never a
backend switch. A worker's green is NOT evidence — re-run every gate yourself.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-10-sp7-parallel-skill-tracks.md
— sections "Contracts" (C-1..C-10, especially C-2/C-3/C-4/C-5) and "Task A1". Implement
VERBATIM via TDD. Also read skills/coverage-gap-audit/ and skills/structure-audit/ end-to-end as
the living pattern.

PRE-FLIGHT (any failure -> STOP and report): repo-audit-skills main clean; create the worktree:
git -C /home/jakub/projects/repo-audit-skills rev-parse HEAD   (expect 6938fb50..., record it)
git -C /home/jakub/projects/repo-audit-skills worktree add ../ras-sp7-hotspot-audit -b sp7/hotspot-audit
Then IN the worktree: npm install (jscpd devDep -> node_modules present; npm run check:selfaudit
baseline comparison meaningful — else duplication findings silently vanish); python3 -m pytest --collect-only -q -> 461 tests collected;
npm run check:selfaudit -> pass, baseline 104; git --version works.

IN-BRANCH CONTRACT (plan C-5): touch ONLY skills/hotspot-audit/**; no edits to shared/, scripts/,
package.json, baselines, leaf_registry.json, other skills. SKILL.md version: 0.3.0. Vendored
scripts/health_common.py byte-identical to shared/health_common.py (check:vendored green).
npm run check:coverage is EXPECTED RED in-branch (suite not registered yet) — the substitute is
the local coverage proof below. npm run check:selfaudit must stay at ZERO new findings; if one is
truly unavoidable, document <=3 candidates in skills/hotspot-audit/docs/sp7-freeze-candidates.md
and fix everything else — NEVER edit the frozen log or baseline.

WAVES: W1: fixtures(make_history, pinned git env)+failing tests || SKILL.md+vendored copy+docs
stub. W2: implementation to green || relpath+idempotence+coverage tests. Recompute the coupling
golden from the fixture before freezing (plan note in Task A1).

GATES (run yourself, from worktree root): leaf suite green from root AND from the leaf dir;
python3 -m pytest --collect-only -q = 461+leaf tests, zero errors;
python3 -m pytest skills/hotspot-audit/tests -q --cov=skills/hotspot-audit/scripts
--cov-report=term -> every file >=50%; check:vendored, check:fixtures, check:release,
check:selfaudit all pass. Commit per task. DO NOT push. DO NOT merge to main (INT does).
Final report: leaf test count, coverage table, gate outputs, freeze candidates (target: none).
```

## Launch A2 — dependency-audit

```
You are the ORCHESTRATOR (Opus) for SP7 leaf A2 dependency-audit. You own ONLY worktree
/home/jakub/projects/ras-sp7-dependency-audit on branch sp7/dependency-audit, within it ONLY
skills/dependency-audit/**. Coordinate ONLY, never implement. Workers: OpenCode DeepSeek v4 Pro
Max via opencode-worker-bridge (file-backed packets, own worktree each), cap 2. ONE-WAY fallback
to native Opus subagents ONLY on infrastructure dispatch failure; gate-failing changes are
discard/retry, never a backend switch. A worker's green is NOT evidence — re-run gates yourself.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-10-sp7-parallel-skill-tracks.md
— Contracts C-1..C-10 (note C-8 advisory shape) and "Task A2". Implement VERBATIM via TDD.
Pattern reference: skills/coverage-gap-audit/ end-to-end.

PRE-FLIGHT (failure -> STOP): main clean; rev-parse HEAD (expect 6938fb50..., record);
git -C /home/jakub/projects/repo-audit-skills worktree add ../ras-sp7-dependency-audit -b sp7/dependency-audit
In worktree: npm install (jscpd devDep -> node_modules present; npm run check:selfaudit
baseline comparison meaningful — else duplication findings silently vanish); collect-only = 461; check:selfaudit pass (104);
python3 -c "import tomllib" succeeds (leaf requires Python >=3.11 — document in SKILL.md).

IN-BRANCH CONTRACT (plan C-5): only skills/dependency-audit/**; SKILL.md version 0.3.0; vendored
health_common.py == shared (check:vendored green); check:coverage EXPECTED RED in-branch (suite
unregistered) — substitute = local coverage proof; check:selfaudit ZERO new findings (candidates,
if truly unavoidable, <=3 in skills/dependency-audit/docs/sp7-freeze-candidates.md; never touch
frozen log/baseline). CRITICAL semantics: no deps manifest found => zero findings, exit 0,
status "manifest": false (self-audit neutrality of the later registration depends on it).
Advisory findings use signal RESTRUCTURE, NOT SECURITY (pre-bump merge).

WAVES: W1: fixtures (dirty/clean/no_manifest trees + advisory.json per C-8) + failing tests ||
SKILL.md + vendored copy + docs stub. W2: implementation (MODULE_TO_DIST table, collect_imports,
declared_deps verbatim from the plan) || relpath+idempotence+advisory tests.

GATES (yourself, worktree root): leaf suite green (root AND leaf dir); collect-only 461+N zero
errors; pytest skills/dependency-audit/tests -q --cov=skills/dependency-audit/scripts
--cov-report=term -> all files >=50%; check:vendored/fixtures/release/selfaudit pass.
Commit per task. DO NOT push. DO NOT merge (INT does). Final report: test count, coverage,
gate outputs, freeze candidates (target none), honest mapping-table limits documented.
```

## Launch A3 — repo-hygiene-audit

```
You are the ORCHESTRATOR (Opus) for SP7 leaf A3 repo-hygiene-audit. You own ONLY worktree
/home/jakub/projects/ras-sp7-repo-hygiene-audit on branch sp7/repo-hygiene-audit, within it ONLY
skills/repo-hygiene-audit/**. Coordinate ONLY, never implement. Workers: OpenCode DeepSeek v4
Pro Max via opencode-worker-bridge, cap 2, file-backed packets, own worktree each. ONE-WAY
fallback to native Opus subagents ONLY on infrastructure dispatch failure; gate-failing changes
= discard/retry. A worker's green is NOT evidence — re-run gates yourself.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-10-sp7-parallel-skill-tracks.md
— Contracts C-1..C-10 and "Task A3". Implement VERBATIM via TDD. Pattern:
skills/structure-audit/ end-to-end.

PRE-FLIGHT (failure -> STOP): main clean; rev-parse HEAD (expect 6938fb50..., record);
git -C /home/jakub/projects/repo-audit-skills worktree add ../ras-sp7-repo-hygiene-audit -b sp7/repo-hygiene-audit
In worktree: npm install (jscpd devDep -> node_modules present; npm run check:selfaudit
baseline comparison meaningful — else duplication findings silently vanish); collect-only = 461; check:selfaudit pass (104).

IN-BRANCH CONTRACT (plan C-5): only skills/repo-hygiene-audit/**; SKILL.md version 0.3.0;
vendored health_common.py == shared; check:coverage EXPECTED RED in-branch — substitute = local
coverage proof; check:selfaudit ZERO new findings (<=3 candidates max in
skills/repo-hygiene-audit/docs/sp7-freeze-candidates.md; never edit frozen log/baseline).
CRITICAL semantics: with --source-prefix given, EVERY finding (including release-hygiene paths
like package.json/.github/LICENSE) is prefix-filtered — the dedicated test
test_prefixed_run_on_own_repo_shape_is_clean MUST pass (INT registers this leaf with
languages ["*"]; self-audit neutrality depends on the filter). Non-git roots degrade per the
plan's table; git missing -> ToolError exit 2.

WAVES: W1: fixture builders (make_dirty_repo/make_clean_repo, pinned git env) + failing tests ||
SKILL.md + vendored copy + docs stub. W2: implementation (all 8 check groups per the plan table)
|| relpath+idempotence+release-group tests.

GATES (yourself, worktree root): leaf suite green (root AND leaf dir); collect-only 461+N zero
errors; pytest skills/repo-hygiene-audit/tests -q --cov=skills/repo-hygiene-audit/scripts
--cov-report=term -> all files >=50%; check:vendored/fixtures/release/selfaudit pass.
Commit per task. DO NOT push. DO NOT merge (INT does). Final report: test count, coverage,
gate outputs, freeze candidates (target none).
```

## Launch A4 — docs-consistency-audit

```
You are the ORCHESTRATOR (Opus) for SP7 leaf A4 docs-consistency-audit. You own ONLY worktree
/home/jakub/projects/ras-sp7-docs-consistency-audit on branch sp7/docs-consistency-audit, within
it ONLY skills/docs-consistency-audit/**. Coordinate ONLY, never implement. Workers: OpenCode DeepSeek v4 Pro
Max via opencode-worker-bridge, cap 2, file-backed packets, own worktree each. ONE-WAY fallback
to native Opus subagents ONLY on infrastructure dispatch failure; gate-failing changes =
discard/retry. A worker's green is NOT evidence — re-run gates yourself.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-10-sp7-parallel-skill-tracks.md
— Contracts C-1..C-10 and "Task A4". Implement VERBATIM via TDD. Pattern:
skills/coverage-gap-audit/ end-to-end.

PRE-FLIGHT (failure -> STOP): main clean; rev-parse HEAD (expect 6938fb50..., record);
git -C /home/jakub/projects/repo-audit-skills worktree add ../ras-sp7-docs-consistency-audit -b sp7/docs-consistency-audit
In worktree: npm install (jscpd devDep -> node_modules present; npm run check:selfaudit
baseline comparison meaningful — else duplication findings silently vanish); collect-only = 461; check:selfaudit pass (104).

IN-BRANCH CONTRACT (plan C-5): only skills/docs-consistency-audit/**; SKILL.md version 0.3.0;
vendored health_common.py == shared; check:coverage EXPECTED RED in-branch — substitute = local
coverage proof; check:selfaudit ZERO new findings (<=3 candidates in
skills/docs-consistency-audit/docs/sp7-freeze-candidates.md; never edit frozen log/baseline).
CRITICAL semantics: (1) the import-introspection GUARD — only modules whose AST has
"import argparse" AND a top-level build_parser are ever imported; the fixture module with a
top-level raise MUST never execute (mandatory guard test in the plan). (2) docstring group is
OFF by default (docstring_min_percent: None) — only a --config run enables it. (3) all findings
signal LINT; CHANGELOG*.md excluded from version-pin checks.

WAVES: W1: fixtures (dirty/clean trees incl. tools/cli.py, tools/sideeffect.py) + failing tests
|| SKILL.md + vendored copy + docs stub. W2: implementation (4 groups per plan) ||
relpath+idempotence+docstring-config tests.

GATES (yourself, worktree root): leaf suite green (root AND leaf dir); collect-only 461+N zero
errors; pytest skills/docs-consistency-audit/tests -q --cov=skills/docs-consistency-audit/scripts
--cov-report=term -> all files >=50%; check:vendored/fixtures/release/selfaudit pass.
Commit per task. DO NOT push. DO NOT merge (INT does). Final report: test count, coverage, gate
outputs, freeze candidates (target none), the SKILL.md introspection caveat included verbatim.
```

## Launch A5 — security-audit

```
You are the ORCHESTRATOR (Opus) for SP7 leaf A5 security-audit. You own ONLY worktree
/home/jakub/projects/ras-sp7-security-audit on branch sp7/security-audit, within it ONLY
skills/security-audit/**. Coordinate ONLY, never implement. Workers: OpenCode DeepSeek v4 Pro
Max via opencode-worker-bridge, cap 2, file-backed packets, own worktree each. ONE-WAY fallback
to native Opus subagents ONLY on infrastructure dispatch failure; gate-failing changes =
discard/retry. A worker's green is NOT evidence — re-run gates yourself.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-10-sp7-parallel-skill-tracks.md
— Contracts C-1..C-10 (C-6 SIGNALS verbatim, C-8 advisory shape) and "Task A5". VERBATIM TDD.

PRE-FLIGHT (failure -> STOP): main clean; rev-parse HEAD (expect 6938fb50..., record);
git -C /home/jakub/projects/repo-audit-skills worktree add ../ras-sp7-security-audit -b sp7/security-audit
In worktree: npm install (jscpd devDep -> node_modules present; npm run check:selfaudit
baseline comparison meaningful — else duplication findings silently vanish); collect-only = 461; check:selfaudit pass (104);
pip install bandit==1.9.4; python3 -m bandit --version -> "bandit 1.9.4".

IN-BRANCH CONTRACT (plan C-5 + A5 specials): only skills/security-audit/**; SKILL.md version
0.3.0. THIS LEAF VENDORS THE POST-BUMP health_common: take shared/health_common.py and apply
EXACTLY the C-6 SIGNALS hunk (PERF + SECURITY appended) — nothing else. Therefore
npm run check:vendored FAILS IN-BRANCH BY DESIGN with exactly ONE defect naming
skills/security-audit/scripts/health_common.py; any other vendored defect is a real bug.
check:coverage EXPECTED RED too (unregistered suite) — substitute = local coverage proof.
check:selfaudit must still show ZERO new findings. Signal = SECURITY; severity/confidence per
the plan's bandit mapping table; metric_name = "bandit_<test_id>"; advisory mode per C-8 also
emits SECURITY. INT merges this branch only AFTER the schema-bump commit.

WAVES: W1: fixtures (planted B404/B105/B602 + clean + advisory.json) + failing tests incl.
test_vendored_signals_include_security || SKILL.md + POST-BUMP vendored copy + docs stub.
W2: implementation (find_spec probe, python -m bandit -r ... -f json -q, mapping) ||
relpath+idempotence+bandit-missing tests. Goldens from a real pinned-bandit run, verified
byte-stable across two runs BY YOU.

GATES (yourself): leaf suite green (root AND leaf dir); collect-only 461+N zero errors;
pytest skills/security-audit/tests -q --cov=skills/security-audit/scripts --cov-report=term ->
all files >=50%; check:fixtures/release/selfaudit pass; check:vendored = the expected single
defect (paste it). Commit per task. DO NOT push. DO NOT merge. Final report: test count,
coverage, gate outputs incl. the expected-red proof, freeze candidates (target none).
```

## Launch A6 — test-effectiveness-audit

```
You are the ORCHESTRATOR (Opus) for SP7 leaf A6 test-effectiveness-audit. You own ONLY worktree
/home/jakub/projects/ras-sp7-test-effectiveness-audit on branch sp7/test-effectiveness-audit,
within it ONLY skills/test-effectiveness-audit/**. Coordinate ONLY, never implement. Workers:
OpenCode DeepSeek v4 Pro Max via opencode-worker-bridge, cap 2, file-backed packets, own
worktree each. ONE-WAY fallback to native Opus subagents ONLY on infrastructure dispatch
failure; gate-failing changes = discard/retry. A worker's green is NOT evidence — re-run gates
yourself.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-10-sp7-parallel-skill-tracks.md
— Contracts C-1..C-10 and "Task A6" (the mutmut facts in Empirical pre-flight row 10 are
load-bearing). VERBATIM TDD.

PRE-FLIGHT (failure -> STOP): main clean; rev-parse HEAD (expect 6938fb50..., record);
git -C /home/jakub/projects/repo-audit-skills worktree add ../ras-sp7-test-effectiveness-audit -b sp7/test-effectiveness-audit
In worktree: npm install (jscpd devDep -> node_modules present; npm run check:selfaudit
baseline comparison meaningful — else duplication findings silently vanish); collect-only = 461; check:selfaudit pass (104);
pip install mutmut==3.6.0. KNOWN QUIRK: mutmut crashes even on --help unless CWD has
setup.cfg [mutmut] source_paths — confirm from a dummy dir.

IN-BRANCH CONTRACT (plan C-5): only skills/test-effectiveness-audit/**; SKILL.md version 0.3.0;
vendored health_common.py == CURRENT shared (NOT post-bump; this leaf emits TEST only) ->
check:vendored green; check:coverage EXPECTED RED in-branch — substitute = local coverage proof;
check:selfaudit ZERO new findings (<=3 candidates in docs/sp7-freeze-candidates.md). CRITICAL
semantics: REQUIRED scope (--paths + --tests-dir + --max-mutants) — refuses unscoped runs
(exit 2 + rationale); ALL mutmut invocations cwd=<sandbox under --out-dir>, NEVER the target
root (side-effect-free sandbox test mandatory); kill_rate per plan (survived + "no tests" =
problems; timeout/suspicious/skipped = killed).

WAVES: W1: weakpkg fixture + captured-output fixtures (one real run captures
results.txt/calc.py.meta/mutmut-cicd-stats.json; plan ground truth: total 5, killed 1,
no_tests 4, kill_rate 0.2) + failing parser tests || SKILL.md + vendored copy + docs stub.
W2: implementation (sandbox protocol, ast budget estimate, parse_results_text/module_totals/
key_to_module verbatim) || relpath+idempotence + ONE real-mutmut integration test (timeout 180).

GATES (yourself): leaf suite green (root AND leaf dir; mutmut installed so the integration
test RUNS); collect-only 461+N zero errors; pytest
skills/test-effectiveness-audit/tests -q --cov=skills/test-effectiveness-audit/scripts
--cov-report=term -> all files >=50%; check:vendored/fixtures/release/selfaudit pass.
Commit per task. DO NOT push. DO NOT merge (INT does post-bump). Final report: test count,
coverage, gate outputs, freeze candidates (target none).
```

## Launch B — repo-audit-refactor-optimize upgrades

```
You are the ORCHESTRATOR (Opus) for SP7 TRACK B in
/home/jakub/projects/repo-audit-refactor-optimize (main working tree — this track owns the whole
repo; no other SP7 session writes here until Track C's C4). Coordinate ONLY, never implement.
Workers: OpenCode DeepSeek v4 Pro Max via opencode-worker-bridge, cap 3, file-backed packets,
own git worktree each. ONE-WAY fallback to native Opus subagents ONLY on infrastructure dispatch
failure; gate-failing changes = discard/retry, never a backend switch. A worker's green is NOT
evidence — re-run every gate yourself and read real output. You own all merges; after each merge
run python3 -m pytest tests/ -q and read it.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-10-sp7-parallel-skill-tracks.md
— "Empirical pre-flight" row 8, Contracts C-1 (the six FROZEN leaf names B7 binds to by name)
and the whole "TRACK B" section. Tasks are implemented VERBATIM via TDD. Style/pattern
reference: docs/plans/2026-06-10-sp5-deterministic-skillset-rewire.md in this repo.

PRE-FLIGHT (any failure -> STOP and report): repo clean on main;
python3 -m pytest tests/ -q -> EXACTLY "53 passed"; scripts/skill_bootstrap_manifest.json has
16 skills / 6 lanes / "version": 1; no .github/ directory exists yet;
tests/test_check_skill_requirements.py defines write_skill/write_manifest helpers (read its
top 60 lines before dispatching B1).

WAVES (saturate, don't serialize):
  Wave 1: B1 (min_version + stale_installed, TDD) || B3 (CI workflow) || B5 (playbook
  RESTRUCTURE arch procedures — verbatim table from the plan).
  Wave 2 (B1 merged; B6 after B3): B2 (unreferenced-skills advisory, TDD) || B6 (check_release
  + CHANGELOG + CI step, TDD) || B4 (run-report contract — verbatim pipeline.md section).
  Wave 3 (B1+B2 merged): B7 (manifest lanes for the six frozen leaf names + "audit" lane
  evaluator, TDD; lane shapes are PINNED in the plan — do not redesign).
  Tail (you): SKILL.md 0.2.0 -> 0.3.0, CHANGELOG ## 0.3.0,
  python3 scripts/check_release.py -> pass.

GATES per merge: full suite green in the worker's worktree AND re-run by you after merge
(expected counts: 53 -> 57 after B1 -> 59 after B2 -> ~63 after B6 -> ~68 after B7; record
exact). Suite-green plus check_release pass at the tail. Any divergence from a plan Expected
line = STOP and surface; do not improvise.

DEFINITION OF DONE: Track B DoD in the plan — exact final test count, CI statically validated
(post-push verification is the human's), stale_installed + advisory + run-report + playbook +
release gate + B7 lanes all evidenced. Commits local only; do NOT push, tag, or release. Do NOT
touch repo-audit-skills or perf-benchmark-skill.
```

## Launch INT — serial integration in repo-audit-skills

```
You are the ORCHESTRATOR (Opus) for SP7 TRACK INT in /home/jakub/projects/repo-audit-skills
(main working tree). START CONDITION: A1-A4 reported done with C-5 evidence (A5/A6 may still
run; their merges come later). Coordinate ONLY; workers (OpenCode DeepSeek v4 Pro Max via
opencode-worker-bridge, cap 2, ONE-WAY infra-failure fallback to native Opus subagents) are for
surgical edits only; YOU run every gate and read real output. SERIAL: one merge at a time,
fully green before the next.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-10-sp7-parallel-skill-tracks.md
— Contracts C-6/C-7/C-9 and the whole "TRACK INT" section. PINNED ORDER: INT-1 gate-harden,
then merges A1 -> A3 -> A2 -> A4 -> schema bump -> A5 -> A6 -> release 0.4.0 (C-1 dirs).

PRE-FLIGHT (failure -> STOP): main clean; npm install; npm run check fully green;
python3 -m pytest --collect-only -q -> 461 tests collected; baseline 104; SUITES length 11;
the four A1-A4 sp7/<leaf-dir> branches exist (names per C-1). Before INT-7: pip install
bandit==1.9.4. Before INT-8: pip install mutmut==3.6.0.

INT-1 FIRST, BEFORE ANY MERGE (TDD): harden scripts/check_self_audit.py
(+ tests/test_check_self_audit.py verbatim from the plan): stale baseline entries now FAIL;
thereafter any fix removing baselined findings shrinks scripts/self_audit_baseline.json in
the SAME commit.

PER-MERGE PROTOCOL (plan INT-2..5, verbatim): merge --no-ff sp7/<leaf> (any conflict = contract
breach -> STOP) -> leaf suite green -> append "skills/<leaf>/tests", to SUITES -> leaf-specific
registration per C-7 (A1 none; A3 registry entry languages ["*"] PLUS the select_leaves wildcard
change with its umbrella test; A2/A4 registry entries) -> adjudicate freeze candidates (PREFER
FIX; a freeze = per-finding frozen-log entry + baseline entry; >10 from one registration = STOP,
never blanket-freeze) -> npm run check FULLY green -> commit.

THEN: INT-6 schema bump (TDD: PERF/SECURITY asserts in tests/test_health_common.py; apply C-6
hunk verbatim to shared/health_common.py; re-vendor all 14 leaf copies; check:vendored green)
-> INT-7 merge A5 (verify cmp shared vs its vendored copy = IDENTICAL, else STOP; CI pip +=
bandit==1.9.4) -> INT-8 merge A6 (registry entry with requires {"mutation_scope": true} +
umbrella skip-test; CI pip += mutmut==3.6.0; SUITES -> 17) -> INT-9 release 0.4.0 atomically
(package.json + ALL 16 SKILL.md; check_release both dicts += 6; installer skills array += 6;
README/description) -> INT-10 run report at
docs/self-audit/2026-06-sp7-integration-run-report.md.

FINAL NUMBERS (C-9, evidence each): version 0.4.0; installer --list = 16 skills;
SUITES = 17; baseline == snapshot (104 - fixed + adjudicated freezes, target 0; INT-1 equality
gate); coverage baseline = 2; root collection = 461 + 3 (INT-1) + sum of leaf tests, zero
errors; npm run check fully green. Remove worktrees after merges; keep branches. Commits
local only — do NOT push, tag, or publish.
```

## Launch C — perf-optimization (GATED)

```
You are the ORCHESTRATOR (Opus) for SP7 TRACK C in /home/jakub/projects/perf-benchmark-skill.
HARD GATE — verify before any work, else STOP: (1) the human has EXPLICITLY confirmed the SP6
run in this repo converged (never infer from git state); (2) SP7 Track B is merged in
/home/jakub/projects/repo-audit-refactor-optimize (suite ~68 passed; check_release.py passes).
Coordinate ONLY, never implement. Workers: OpenCode
DeepSeek v4 Pro Max via opencode-worker-bridge, cap 2, file-backed packets, own worktree each;
ONE-WAY infra-failure fallback to native Opus subagents; gate-failing changes = discard/retry.
A worker's green is NOT evidence — re-run gates yourself.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-10-sp7-parallel-skill-tracks.md
— "Empirical pre-flight" row 9 and the whole "TRACK C" section; then
docs/plans/2026-06-10-sp6-perf-bench-v0.2.md T5/T6/T7 in THIS repo.

PRE-FLIGHT = the plan's C-0 SP6 DRIFT GATE (pinned values live there; files under
scripts/perf_benchmark/): (1) git log -3; python3 -m pytest tests/ -q green, record exact
count. (2) findings.py: diff findings-out key set, leaf "perf-benchmark", signal "PERF",
sha1 id recipe, sort order vs the C-0 pins. (3) ledger.py: JSONL record keys +
vs_last/vs_best. (4) reporting.py + python3 scripts/perf_benchmark_pipeline.py --help: diff
flags --baseline-ledger/--max-cv/--findings-out, summary keys environment/
wall_time_percentiles/ledger_regressions, tier string "N/A (noise)", Algorithmic Scaling
dimension + metric name (-> ALGORITHMIC_METRIC_SUBSTRINGS, C2). (5) ANY material drift
(key/flag/signal/tier-string change) -> STOP: pinned-vs-found diff with file:line + EXPLICIT
human sign-off BEFORE any C2/C3 fixture or constants block. Cosmetic drift recorded, not
gating.

SCOPE: create ONLY perf-optimization/** in this repo (SKILL.md v0.1.0, references/
optimization-playbook.md with the plan's verbatim technique table,
scripts/{select_candidate,verify_win}.py, tests with synthetic fixtures). NO real benchmarking
in tests — golden verdicts only (clean win/noisy CV/fingerprint mismatch/regression+tier-drop/
suite-red).
Never modify perf-benchmark's own scripts/, references/, tests/.

WAVES: W1: C1 (scaffold + playbook) || C2 (select_candidate, TDD goldens incl. algorithmic STOP
gate). W2: C3 (verify_win, TDD — five golden verdicts; fingerprint compare excludes
timestamp_utc/load_avg_1m). Tail, serialized in repo-B AFTER its gate: C4 — performance
lane fallback ["perf-optimization"] + skill entry + tests (expected warning
"Optimization skill missing; lane remains benchmark-first."), SKILL.md 0.3.0 -> 0.3.1,
CHANGELOG, check_release pass.

GATES (yourself): perf repo full suite green (SP6 count + new, record exact); all goldens
byte-deterministic; repo-B suite green + check_release pass after C4. Commits local in BOTH
repos; do NOT push, tag, or release anywhere. Final report: drift list, golden verdict
outputs, both repos' final test counts.
```
