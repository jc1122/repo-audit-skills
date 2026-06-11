# SP8: Total Self-Audit — Three-Repo Dogfooding & Loop-2 Gate Extension

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.
>
> **For every SP8 orchestrator (G, H, P):** this plan is the single authority. You coordinate ONLY, never implement. Workers = OpenCode DeepSeek v4 Pro Max via opencode-worker-bridge (file-backed packets, one per worker; session-unique run dir). Automatic ONE-WAY fallback to native Opus subagent workers ONLY on infrastructure dispatch failure (credits/quota/auth/bridge unreachable) — a gate-failing CHANGE is discard/retry, never a backend switch. A worker's "green" is NOT evidence: re-run every gate yourself and read real output. Commit locally per task. Do NOT push, tag, or release — the human reviews everything.

**Goal:** the v0.4.0 toolkit dogfoods itself across all three repos, concurrently and with zero shared writes. TRACK G (repo-A, the core): bootstrap evidence → full parallel diagnosis wave → four new Loop-2 ratchet gates (`check:security`, `check:hygiene`, `check:docs`, `check:dependency`) cloning the hardened `check_self_audit.py` pattern → coverage ratchet 2→1 → serial Phase-2 burn-down with disciplined baseline seeding → B4-compliant run report; `npm run check` ends at **9 gates green**. TRACK H (repo-B): bootstrap probe on itself + all-applicable-lanes diagnosis + mechanical-only remediation + prioritized SP9 backlog + B4 run report. TRACK P (perf repo): bootstrap probe + diagnosis + the first full performance-lane exercise (perf-benchmark `--tier fast` → `select_candidate` → ONE bounded optimization attempt → `verify_win`; honest no-win is a valid outcome) + B4 run report.

**Architecture (FIXED — do not redesign):** three concurrent orchestrator sessions, one per repo, zero shared writes; the human reviewer verifies at the end. Tracks never write outside their own repo. Caps: G = 4 workers, H = 2, P = 2.

**Repos (verified 2026-06-11):**
- repo-A = `/home/jakub/projects/repo-audit-skills` — main at `14fc35b` (v0.4.0 released + pushed, CI green), clean. 16 skills; `npm run check` = 5 gates green; root `python3 -m pytest --collect-only -q` → **645 tests, zero errors**; self-audit baseline **107 == snapshot 107** under the equality gate (bee4502); coverage-gap baseline **2**, snapshot **1** (one stale entry — `scripts/check_self_audit.py` is now covered; the coverage gate is a one-way ratchet so it still passes). KNOWN, pre-existing, NOT a regression: full unfiltered `python3 -m pytest` has a `helpers.py` basename collision failure (`test_umbrella_requires.py::test_real_registry_smoke`); gates never run unfiltered pytest, neither does this plan.
- repo-B = `/home/jakub/projects/repo-audit-refactor-optimize` — `cbf12ab` (v0.3.1, pushed, CI green), clean; `python3 -m pytest tests/ -q` → **79 passed**. Manifest v2: 8 lanes (`bootstrap, code-health-python, coverage-python, hygiene, orchestration, performance, security, test-python`), 23 skill entries.
- repo-P = `/home/jakub/projects/perf-benchmark-skill` — `ceff6b7` (pushed, CI green), clean; **151 tests**. Root IS the perf-benchmark skill (v0.2.0); `perf-optimization/` (v0.1.0) is the second skill dir. Valgrind ABSENT on this machine → `--tier fast` ONLY.
- Installed skills root `~/.claude/skills` is current: 16 repo-A skills @ 0.4.0, repo-audit-refactor-optimize 0.3.1, perf-benchmark 0.2.0, perf-optimization 0.1.0.

## Out of scope (deliberately deferred)

- **`check:hotspot` gate:** churn metrics are non-stationary — every commit changes the snapshot, so an equality baseline can never converge. Hotspot stays a prioritization input (G1 ranks Phase-2 rounds with it), never a gate.
- **`check:test-effectiveness` gate:** mutation runs cost minutes-to-hours per file; a gate must run on every `npm run check`. Test-effectiveness stays a budgeted dogfood-round tool (G1, scoped to top-3 hotspot files).
- **Security advisory mode in the gate:** `--advisory-report` needs a pip-audit-shaped artifact produced out-of-band (network). The gate runs bandit-only, deterministic, offline. Advisory ingestion stays a diagnosis-wave option only where an artifact already exists.
- **Gate extension in repo-B:** structural findings there go to the SP9 backlog; repo-B gets NO new gates this round.
- **Perf tiers beyond `fast`:** valgrind is absent on this machine; medium/deep/asm tiers are unrunnable here. Honest tier limitation is recorded in Track P's run report.
- **New leaves, schema changes, releases, pushes:** none anywhere.

---

## Empirical pre-flight (verified 2026-06-11 at the SHAs above; every orchestrator re-verifies its own rows before dispatching)

1. **Gate pattern to clone — `scripts/check_self_audit.py` (69 lines, commit bee4502):** `_identities(findings)` = set of `tuple(sorted(d.items()))` over 4-key dicts `{leaf, path, symbol, metric}`; `_load_snapshot(snapshot)` returns the `--snapshot` file when given (testing) else re-runs `scripts/self_audit.py` and reads `scripts/self_audit_snapshot.json`; `_verdict(current, baseline)` → regressions first (`{"status":"fail","new_findings":[...]}`, exit 1), then stale baseline entries (`{"status":"fail","stale_baseline":[...],"message":"...remove them from <baseline> in the same commit"}`, exit 1), else `{"status":"pass","count":N,"baseline":M}`, exit 0. argparse flags `--snapshot` / `--baseline` (testing only). JSON printed to stdout, `indent=2`.
2. **Gate test pattern — `tests/test_check_self_audit.py`:** loads the script via `importlib.util.spec_from_file_location`, calls `mod.main(["--snapshot", ..., "--baseline", ...])` IN-PROCESS with `capsys`; three tests: stale-fails-with-"same commit"-message, equality-passes, new-finding-fails. This in-process style is what gives the script ≥50% coverage under `check:coverage` (subprocess runs are not traced).
3. **Production scope — `scripts/self_audit.py:23-28` `_prefixes()`:** `["shared", "scripts"] + sorted("skills/<d>/scripts" for d in skills/* if scripts/ exists)` = 18 prefixes today (16 skills have `scripts/`). Identical helper in `scripts/check_coverage_gap.py:42-47`. Snapshot identity carries NO line numbers, but duplication-finding SYMBOLS embed line ranges → those baseline entries are LINE-PINNED: any edit to a clone-pair file = stale+new swap, ratcheted in the same commit (enforced by the equality gate).
4. **Wiring today — `package.json`:** `check` = `check:vendored && check:fixtures && check:release && check:selfaudit && check:coverage`; `files` excludes `!**/self_audit_snapshot.json` and `!**/coverage_gap_snapshot.json`; `.gitignore` ignores `.self_audit_out/` and both snapshots (snapshots are NOT git-tracked). `check_release.py` `REQUIRED_SCRIPTS`/`REQUIRED_SKILLS` are hardcoded allowlists — unlisted files are invisible to it.
5. **Coverage gate — `scripts/check_coverage_gap.py`:** 17 `SUITES`, each run separately under `pytest --cov --cov-append --cov-config=.coveragerc` with `COVERAGE_FILE=.self_audit_out/coverage/.coverage`; combined JSON written to **`.self_audit_out/coverage/coverage.json`** (the G1 umbrella's `--coverage-json` input — no extra coverage run needed); leaf threshold `min_file_coverage: 50.0`; one-way ratchet (no stale detection — that asymmetry is why the 2-entry baseline passes with a 1-entry snapshot).
6. **Leaf CLI invocations (verified via `--help` on the installed copies; in-repo copies are identical at 0.4.0):**
   - `hotspot_audit.py --root R --out-dir O [--rev SHA] [--max-commits N] [--source-prefix P]...`
   - `dependency_audit.py --root R --out-dir O [--source-prefix P]... [--advisory-report PATH]`
   - `repo_hygiene_audit.py --root R --out-dir O [--source-prefix P]...` — threshold `max_tracked_file_bytes: 1048576`
   - `docs_consistency_audit.py --root R --out-dir O [--source-prefix P]...` — docstring group OFF by default (`docstring_min_percent: None`, config-gated)
   - `security_audit.py --root R --out-dir O [--source-prefix P]... [--advisory-report PATH]` — requires bandit==1.9.4 on the running interpreter (**verified installed locally**, and pinned in repo-A CI)
   - `test_effectiveness_audit.py --root R --out-dir O [--paths FILE] [--tests-dir D] [--max-mutants N] [--config C]` — thresholds `{min_kill_rate: 0.8, mutmut_timeout_seconds: 600, estimated_mutants_per_def: 8}`; sandboxes mutmut itself (mutmut crashes without `[mutmut]` config in CWD — NEVER run mutmut at a repo root).
7. **Dry-run pre-seed counts (2026-06-11, repo-A @ 14fc35b, out-dirs in /tmp — read-only):**
   - **security** over the 18 production prefixes: **64 findings** — by symbol (= bandit `test_name`, NOT line-pinned): `subprocess_without_shell_equals_true` 26, `blacklist` 17, `hashlib` 13 (= ALL 13 high-severity findings; the sha1 finding-id idiom — fixable with `usedforsecurity=False`), `start_process_with_partial_path` 4, `hardcoded_password_string` 2, `hardcoded_tmp_directory` 1, `try_except_continue` 1. Severity: 50 low / 1 medium / 13 high.
   - **repo-hygiene** full repo (NO prefixes): **0 findings**, `"git": true` — empty baseline expected.
   - **docs-consistency** full repo (NO prefixes): **CRASHES** — `ValueError: '/tmp/che-install/complexity-audit/scripts/complexity_audit.py' is not in the subpath of '/home/jakub/projects/repo-audit-skills'`. Cause: historical docs (`docs/superpowers/IMPLEMENTATION-PROMPT.md`, `ORCHESTRATOR-PROMPT.md`, `plans/2026-06-10-code-health-skills-foundation.md`) reference absolute `/tmp/che-install/...` paths; that directory happens to EXIST on this machine; the leaf resolves the token and `_rel()` (`relative_to`) throws. Genuine dogfooding find: G2-1 hardens the leaf (out-of-root resolution must never crash); the gate ALSO pins a living-docs scope (C-4) so immutable historical records never enter the baseline.
   - **docs-consistency** with the C-4 living-docs prefixes: **18 findings, all `doc_path_missing`** — `skills/test-quality-assurance/SKILL.md` 7, `skills/code-health-audit-pipeline/SKILL.md` 3, `skills/test-redundancy-triage/SKILL.md` 2, `docs/self-audit/2026-06-sp7-integration-run-report.md` 1, and 1 each in `complexity/dead-code/duplication/structure/test-effectiveness` SKILL.mds. All look mechanically fixable.
   - **dependency** over production prefixes: `{"status":"ok","findings":0,"leaf":"dependency","manifest":false}` — repo-A has no pyproject/requirements; empty baseline, gate is a tripwire for the day a manifest appears. (repo-P DOES have `pyproject.toml` → its dependency lane is a real run.)
   - `check:vendored`, `check:fixtures`, `check:release` re-verified green locally today (read-only gates).
8. **Docs leaf mechanics (`skills/docs-consistency-audit/scripts/docs_consistency_audit.py`):** `_in_scope(rel, prefixes)` = `not prefixes or any(rel.startswith(p))` (lines 44-46 — plain startswith, so file-path prefixes like `README.md` and `skills/<n>/SKILL.md` work); `analyze_tree` globs `*.md` + `*.py` under root filtered by prefixes (lines 511-512); checked extensions set at line 31; the crash path is `_check_dead_paths`/`_script_for_tokens` → `_rel` (line 49-51, `relative_to`).
9. **Hygiene leaf mechanics (`skills/repo-hygiene-audit/scripts/repo_hygiene_audit.py:30-62`):** ALL checks run unconditionally (tracked-tree group needs git; conflicting-configs, version-mismatch, missing-CI, missing-LICENSE always); `source_prefixes` filter is applied POST-HOC over all findings — prefixing would silently drop root-level release findings. Therefore the gate runs UNPREFIXED (full repo) to keep the release-hygiene group ON.
10. **B4 run-report contract (`~/.claude/skills/repo-audit-refactor-optimize/references/pipeline.md:93-114`; enforced fail-closed per `references/verification.md:80` and `SKILL.md:163`):** every orchestration run MUST commit, in the AUDITED repo, `docs/audits/<YYYYMMDDTHHMMSSZ>/run_report.json` + `run_report.md` (timestamp = run start, UTC, compact ISO). JSON keys, ALL required: `schema_version` (1), `repo_root`, `started_utc`, `finished_utc`, `orchestrator_skill_version` (0.3.1), `lanes` ({lane: state} from the bootstrap report), `findings_totals` ({signal: count} across diagnosis lanes), `backlog` ({"accepted": N, "deferred": N, "coverage_gated": N}), `batches` ([{"id","signal","files","result":"accepted"|"discarded","evidence"}]), `verification` ([{"command","exit_code"}]), `warnings` ([str]). `run_report.md` = human rendering of the same content. Absence of either file or any key = gate failure, not a warning.
11. **Bootstrap checker:** `python3 ~/.claude/skills/repo-audit-refactor-optimize/scripts/check_skill_requirements.py --repo <repo> --out-dir <dir> --extra-root ~/.claude/skills` writes `<dir>/bootstrap/{bootstrap_report.json, bootstrap_report.md, install_plan.md}` (verified, `write_bootstrap_outputs` lines 984-999). LIVE probe on repo-A today: lanes code-health-python / coverage-python / hygiene / security / test-python = **FULL**; performance = manual (no benchmark surface — correct); orchestration = manual (verification-before-completion not mirrored — known); bootstrap = degraded (helper skills absent — known); `stop_before_discovery` false. B2 unreferenced-skills advisory present (`check_skill_requirements.py:864-952`).
12. **Perf pipeline (verified `--help`):** `perf_benchmark_pipeline.py --root R --out-dir O --target "CMD {SIZE}" --tier {fast,medium,deep,asm} --sizes S1,S2,... [--expected-complexity {linear,nlogn,quadratic}] [--baseline-ledger JSONL] [--max-cv F] [--findings-out PATH] [--env ...]`. `select_candidate.py --findings PERF_findings.json --out candidate.json` (algorithmic STOP gate built in). `verify_win.py --before before/benchmark_summary.json --after after/... --suite-exit-code N [--min-win 5.0] [--ledger JSONL] --out verdict.json` — accept = ≥5% median win + CV ≤ 5% both runs + matching env fingerprints + suite green. Bench target: `benchmarks/bench_parse_massif.py` takes SIZE as argv[1] → target string `python3 benchmarks/bench_parse_massif.py {SIZE}`. No root ledger exists yet in repo-P (only test fixtures) — P2 creates `docs/perf/baseline_ledger.jsonl`.
13. **Frozen-log format (`scripts/self_audit_frozen.md`):** header rationale + `Each entry: path :: leaf/metric :: reason.` + `## Round log` (dated, per-round: what was fixed, what was frozen, baseline before→after) + per-section frozen entries with individual justifications. Zero blanket freezes is the standing rule (the SP4 retirement note is explicit). New frozen logs clone this format.
14. **Orchestration gotchas (encode in every launch):** backgrounded `npm run check | tail` reports tail's exit code, not npm's — grep the printed gate JSON (`"status": "pass"` / `"fail"`) instead of trusting `$?`; duplication baseline entries are line-pinned (row 3); mutmut never at repo root (row 6); `npm install` before any `check:*` in a fresh clone/worktree (jscpd is an npm devDependency — not needed here since work happens in the existing checkouts, which already have `node_modules/`).

---

## Contracts (FROZEN — deviation = STOP and report)

### C-1. The four new gates (names, files, npm scripts)

| Gate | npm script | Check script | Baseline (committed) | Snapshot (gitignored) | Frozen log (only if ≥1 freeze) | Runbook |
|---|---|---|---|---|---|---|
| security | `check:security` | `scripts/check_security_audit.py` | `scripts/security_baseline.json` | `scripts/security_snapshot.json` | `scripts/security_frozen.md` | `docs/self-audit/security.md` |
| hygiene | `check:hygiene` | `scripts/check_repo_hygiene.py` | `scripts/repo_hygiene_baseline.json` | `scripts/repo_hygiene_snapshot.json` | `scripts/repo_hygiene_frozen.md` | `docs/self-audit/repo-hygiene.md` |
| docs | `check:docs` | `scripts/check_docs_consistency.py` | `scripts/docs_consistency_baseline.json` | `scripts/docs_consistency_snapshot.json` | `scripts/docs_consistency_frozen.md` | `docs/self-audit/docs-consistency.md` |
| dependency | `check:dependency` | `scripts/check_dependency_audit.py` | `scripts/dependency_baseline.json` | `scripts/dependency_snapshot.json` | `scripts/dependency_frozen.md` | `docs/self-audit/dependency.md` |

Final chain (the wiring commit, G4-R1 seed): `"check": "npm run check:vendored && npm run check:fixtures && npm run check:release && npm run check:selfaudit && npm run check:security && npm run check:hygiene && npm run check:docs && npm run check:dependency && npm run check:coverage"` — **9 gates**, `check:coverage` stays last (heaviest). Same commit: `.gitignore` += the 4 snapshot paths; `package.json` `files` += 4 `!**/<class>_snapshot.json` exclusions; `check_release.py` `REQUIRED_SCRIPTS` += the 4 check scripts, `scripts/gate_common.py`, and the 4 baselines. CI is unchanged (it runs `npm run check`; bandit==1.9.4 already pinned there).

### C-2. Gate behavior contract (clone of the hardened `check_self_audit.py` semantics)

Each check script: (a) runs its leaf CLI (the IN-REPO copy under `skills/<leaf>/scripts/`, never `~/.claude/skills`) over its C-4 scope with `--out-dir <ROOT>/.self_audit_out/<class>`; (b) normalizes findings to sorted 4-key dicts `{leaf, path, symbol, metric}` (`symbol` = `location.symbol`, `metric` = `metric.name`), sorted by `(path, leaf, metric, symbol)`; (c) writes the snapshot file; (d) compares against the baseline with EXACTLY the `_verdict` semantics of pre-flight row 1: new findings → fail+`new_findings`; stale baseline entries → fail+`stale_baseline`+same-commit ratchet message naming the gate's own baseline path; equality → pass. Exit 0/1; JSON `indent=2` on stdout. argparse `--snapshot` / `--baseline` overrides for testing, exactly like `check_self_audit.py`. Identity coarseness is inherited and documented in each runbook: two same-symbol findings in one file collapse to one identity (set semantics) — same limitation as the self-audit gate. A leaf exit of 2 (tool error) → gate prints `{"status":"error",...}` and exits 1 (fail closed).

### C-3. `scripts/gate_common.py` — shared verdict library (the anti-clone measure)

Four near-copies of `check_self_audit.py` would hand `check:selfaudit` a pile of new `duplicate_tokens` findings (the ratchet-idiom clone is already a known frozen class). Gate scripts are repo infrastructure, NOT standalone vendored skills — the vendoring rationale that forbids `shared/` hoisting for leaves does NOT apply here. So: `scripts/gate_common.py` owns `identities()`, `verdict()`, `normalize_findings()` (raw leaf findings JSON → 4-key dicts), and `gate_main(argv, *, leaf_cmd, findings_file, snapshot_path, baseline_path, description)`; each check script is a thin (<25-line) wrapper defining its leaf command + scope and calling `gate_main`. `check_self_audit.py` is refactored onto `gate_common.verdict`/`identities` in the same task with `tests/test_check_self_audit.py` UNCHANGED and green (regression lock). New-gate code must be finding-clean under `check:selfaudit` — a new self-audit finding caused by gate code is a FIX (push more logic into `gate_common`), never a freeze.

### C-4. Scopes (the production-scope definition, reused)

- **Production scope** = `_prefixes()` exactly as `scripts/self_audit.py:23-28`: `["shared","scripts"] + ["skills/<d>/scripts" for d in sorted(skills/*) if scripts/ exists]`. Gate scripts re-implement this 6-line helper (3rd copy in the tree; the existing two coexist below jscpd's token threshold — verify the gate stays clone-free; if jscpd fires, hoist the helper into `gate_common` and import it from nowhere else).
- **check:security:** production scope (18 prefixes). bandit-only; NO `--advisory-report` in the gate.
- **check:hygiene:** full repo, NO `--source-prefix` (pre-flight row 9: post-hoc filtering would drop root-level release findings; release-hygiene group must stay ON).
- **check:docs:** LIVING-DOCS scope, built dynamically by the check script: static `["README.md", "AGENTS.md", "docs/self-audit", "shared", "scripts", "bin"]` + for each `skills/<d>/`: `skills/<d>/SKILL.md`, plus `skills/<d>/scripts` and `skills/<d>/docs` when they exist. EXCLUDED by omission: `docs/superpowers/**` and `docs/audits/**` (immutable point-in-time records — "fixing" their references would falsify history, and pre-flight row 7 shows they crash-or-flood; the runbook records this rationale), `skills/*/tests/**` (deliberately dirty fixtures — `check:fixtures` owns fixture integrity), `tests/`, `node_modules/`. Docstring group stays OFF (default). This exact scope produced the verified 18-finding pre-seed.
- **check:dependency:** production scope (matches the security gate; `manifest:false` ⇒ empty snapshot ⇒ green, by design — record honestly in the runbook).

### C-5. Baseline seeding discipline (NON-NEGOTIABLE)

Baselines are seeded ONLY at the END of Phase-2 round 1 (G4-R1): fix everything fixable FIRST, then freeze the residual PER-FINDING with an individual justification in the gate's frozen log (clone the `self_audit_frozen.md` format, pre-flight row 13). NEVER seed a baseline from the raw first snapshot. Zero blanket freezes. Empty residual (expected for hygiene + dependency) ⇒ baseline `[]` and NO frozen log. Gates enter the `npm run check` chain in the same commit that seeds their baselines (the wiring commit), so every commit in history keeps `npm run check` green. After seeding: shrink-only; ANY baseline growth = STOP and report to the human.

### C-6. Run artifacts & timestamps

One session-unique run dir per track, fixed at run start: `RUN=docs/audits/$(date -u +%Y%m%dT%H%M%SZ)` inside the AUDITED repo. G0/H0/P0 bootstrap artifacts land in `$RUN/bootstrap/` (the checker writes that subdir itself). Diagnosis lanes get disjoint subdirs (`$RUN/code-health`, `$RUN/security`, ...). The run report (pre-flight row 10 schema, ALL keys) lands at `$RUN/run_report.{json,md}` and is committed. Do NOT commit raw `coverage.json` (can approach the 1 MiB hygiene threshold; commit the coverage-gap findings + report instead, and note the omission under `warnings`).

### C-7. Bounded-round caps

Phase-2 (G4): ≤ 4 serial rounds, orchestrator-driven (you adjudicate; workers only execute mechanical fix lists). Hotspot ranking from G1 prioritizes round content. Mutation budget (G1): top-3 hotspot production files, one leaf invocation per file, `--max-mutants 150` each (≤450 total), `--config` raising `mutmut_timeout_seconds` to 1800. Hotspot window: `--rev <recorded HEAD SHA> --max-commits 500` (covers the full history; the pinned rev makes the run reproducible). Track H remediation: mechanical lint-class ONLY. Track P optimization: ONE bounded attempt.

### C-8. Expected final numbers (record actuals in the run reports)

| Item | Expected |
|---|---|
| repo-A `npm run check` | 9 gates green, in the C-1 chain order |
| `check:selfaudit` | equality holds; baseline 107 ± same-commit line-pin swaps/ratchets from Phase-2 edits (record final) |
| `check:security` baseline | ≈ 64 − fixes (13 hashlib + 1 tmp expected fixed; ~47–50 individually-justified freezes — record exact) |
| `check:hygiene` baseline | `[]` (0 pre-seed) |
| `check:docs` baseline | ≈ 0–5 (18 pre-seed, all `doc_path_missing`, mostly fixable) |
| `check:dependency` baseline | `[]` (`manifest:false`) |
| `check:coverage` | green; baseline ratcheted 2 → 1 (`scripts/self_audit.py` remains) |
| repo-A collect-only | 645 + new gate/leaf tests, zero errors (record exact) |
| repo-B suite | 79 passed (unchanged unless a mechanical fix adds none) |
| repo-P suite | 151 passed |
| Run reports | committed in ALL THREE repos, B4 schema complete |
| Pushes/tags/releases | ZERO anywhere |

---

# TRACK G — repo-A total self-audit (cap 4)

## Task G0 — bootstrap evidence

- [ ] Record `git -C /home/jakub/projects/repo-audit-skills rev-parse HEAD` (expect `14fc35b...`; if main moved, record the new SHA, run `npm run check` (5 gates) and proceed only if green).
- [ ] Fix the run dir: `TS=$(date -u +%Y%m%dT%H%M%SZ); RUN=docs/audits/$TS` (one TS for the whole track; write it down).
- [ ] `python3 ~/.claude/skills/repo-audit-refactor-optimize/scripts/check_skill_requirements.py --repo /home/jakub/projects/repo-audit-skills --out-dir /home/jakub/projects/repo-audit-skills/$RUN --extra-root ~/.claude/skills`
  - Expected: exit 0; `$RUN/bootstrap/{bootstrap_report.json,bootstrap_report.md,install_plan.md}` exist; lanes per pre-flight row 11 (5 FULL, performance/orchestration manual, bootstrap degraded). Deviations: record honestly, do not chase.
- [ ] Commit: `docs(audits): SP8 G0 bootstrap evidence for repo-A`.

## Task G1 — diagnosis wave (parallel, read-only, disjoint out dirs)

All jobs read-only w.r.t. source; each writes ONLY its own `$RUN/<lane>` dir. Dispatch in parallel (cap 4). Build the production-prefix flags once:

```bash
PFX=$(python3 - <<'EOF'
from pathlib import Path
pres = ["shared", "scripts"]
for d in sorted(Path("skills").iterdir()):
    if (d / "scripts").is_dir():
        pres.append(f"skills/{d.name}/scripts")
print(" ".join(f"--source-prefix {p}" for p in pres))
EOF
)
```

- [ ] **Coverage artifact first** (the umbrella depends on it): `npm run check:coverage` → expect pass (snapshot 1 < baseline 2 pre-G3); combined JSON now at `.self_audit_out/coverage/coverage.json`. Copy the leaf findings (`.self_audit_out/coverage/leaf/`) into `$RUN/coverage/`; do NOT commit the raw coverage.json (C-6).
- [ ] **Umbrella code-health** (with coverage passthrough): `python3 skills/code-health-audit-pipeline/scripts/code_health_pipeline.py --root . --out-dir $RUN/code-health --coverage-json .self_audit_out/coverage/coverage.json $PFX` — Expected: exit 1 (findings); `code_health_summary.json` findings ⊇ the 107 baseline identities plus coverage-leaf TEST findings; record the supervisor decision verbatim.
- [ ] **Hotspot**: `python3 skills/hotspot-audit/scripts/hotspot_audit.py --root . --out-dir $RUN/hotspot --rev $(git rev-parse HEAD) --max-commits 500` — Expected: exit 0/1, deterministic findings; extract the top-3 PRODUCTION files (in `_prefixes()` scope) by `churn_complexity_product` → this is the Phase-2 priority list AND the mutation target list.
- [ ] **Security**: `python3 skills/security-audit/scripts/security_audit.py --root . --out-dir $RUN/security $PFX` — Expected: exit 1, **64 findings** matching pre-flight row 7 (if the count drifted, record why before Phase 2).
- [ ] **Hygiene**: `python3 skills/repo-hygiene-audit/scripts/repo_hygiene_audit.py --root . --out-dir $RUN/hygiene` — Expected: exit 0, 0 findings, `"git": true`.
- [ ] **Docs-consistency** (living-docs scope; this job runs AFTER G2-1's leaf hardening if the wave is re-run, but the first pass uses the C-4 prefixes which avoid the crash): build the C-4 prefix flags the same heredoc way, then `python3 skills/docs-consistency-audit/scripts/docs_consistency_audit.py --root . --out-dir $RUN/docs <C4-PREFIXES>` — Expected: exit 1, **18 `doc_path_missing` findings** per pre-flight row 7.
- [ ] **Dependency**: `python3 skills/dependency-audit/scripts/dependency_audit.py --root . --out-dir $RUN/dependency $PFX` — Expected: exit 0, `{"findings": 0, "manifest": false}` — record honestly; this is the correct answer for a manifest-less repo, not a failure.
- [ ] **Scoped test-effectiveness** (budgeted, C-7; serial within one worker — mutation runs are heavy): for each of the top-3 hotspot files `F` with owning suite `S` (root `tests` for `scripts/*` and `shared/*`; `skills/<x>/tests` for `skills/<x>/scripts/*`): write `$RUN/test-effectiveness/paths_<i>.txt` containing `F`; run `python3 skills/test-effectiveness-audit/scripts/test_effectiveness_audit.py --root . --out-dir $RUN/test-effectiveness/<i> --paths $RUN/test-effectiveness/paths_<i>.txt --tests-dir S --max-mutants 150 --config <(echo '{"mutmut_timeout_seconds": 1800}')` (if process substitution misbehaves, write the config JSON to `$RUN/test-effectiveness/config.json` and pass that path). Expected: exit 0/1 per file, kill-rate findings or clean; a refusal (estimate > 150) is recorded honestly, not retried with a bigger budget.
- [ ] Commit the wave: `docs(audits): SP8 G1 diagnosis wave artifacts` (findings JSONs + reports + lane summaries; no source changes).

## Task G2 — Loop-2 gate extension (the heart; TDD each step; after EVERY commit `npm run check` (current 5 gates) must be green)

**G2-0: `scripts/gate_common.py` + refactor `check_self_audit.py` onto it (C-3).**
- [ ] RED: write `tests/test_gate_common.py` — in-process (importlib pattern, pre-flight row 2): `identities` dedupes same-symbol dicts; `verdict` equality→(0, pass payload); new finding→(1, `new_findings`); stale→(1, `stale_baseline` + message containing "same commit" and the baseline path); `normalize_findings` maps a sample raw leaf findings list (use 2-3 dicts shaped like real findings: `leaf`, `path`, `location.symbol`, `metric.name`) to sorted 4-key dicts; `gate_main` with `--snapshot`/`--baseline` tmp files returns the right codes without invoking any leaf. Run: `python3 -m pytest tests/test_gate_common.py -q` → fails (module absent).
- [ ] GREEN: implement `scripts/gate_common.py` (stdlib only; small functions — this file is in self-audit scope).
- [ ] REFACTOR: rewire `scripts/check_self_audit.py` to import `gate_common` for `_identities`/`_verdict`; `tests/test_check_self_audit.py` byte-UNCHANGED and green.
- [ ] Gates: `python3 -m pytest tests -q` green; `npm run check` green. EXPECTED side effect: if the rewrite dissolves a line-pinned duplication baseline entry (ratchet-idiom clone), `check:selfaudit` fails STALE — remove the stale entries from `scripts/self_audit_baseline.json` in the SAME commit and note it in `scripts/self_audit_frozen.md`'s round log. `check:coverage`: the new `scripts/gate_common.py` must be ≥50% covered by the in-process tests (it will be) — verify by re-running `npm run check:coverage`.
- [ ] Commit: `feat(gates): gate_common verdict library; check_self_audit rewired (SP8 G2-0)`.

**G2-1: harden the docs leaf against out-of-root path resolution (the pre-flight row 7 crash).**
- [ ] RED: in `skills/docs-consistency-audit/tests/`, add a test: build a tmp fixture repo whose `.md` references an ABSOLUTE path that EXISTS but lies OUTSIDE the fixture root (create `tmp_path/"outside"/"x.py"` and reference its absolute string); run `mod.main(["--root", <fixture>, "--out-dir", ...])` in-process → currently raises `ValueError`. Assert instead: exit in {0,1}, no traceback, and the out-of-root token does NOT appear as a finding path (decision: tokens resolving outside `--root` are SKIPPED — they are environment-dependent and can't be root-relative; document in SKILL.md "Limits").
- [ ] GREEN: guard the `relative_to` call (catch `ValueError` → skip token) in `_check_dead_paths`/`_script_for_tokens`/`_rel` usage — minimal diff.
- [ ] Gates: leaf suite green from repo root AND from the leaf dir; `npm run check` green (leaf script edits may line-shift duplication entries → same-commit ratchet swap per C-5 discipline; SKILL.md version stays 0.4.0 — `check:release` unchanged).
- [ ] Commit: `fix(docs-consistency-audit): never crash on out-of-root path tokens (SP8 G2-1)`.

**G2-2..G2-5: the four check scripts (one commit each; identical TDD shape).** For each row of C-1:
- [ ] RED: `tests/test_check_<class>.py` (basenames unique repo-wide), cloning `tests/test_check_self_audit.py`: equality-passes, new-finding-fails, stale-fails-with-same-commit-message (message must name THIS gate's baseline file), all via `mod.main(["--snapshot",...,"--baseline",...])` in-process; plus one test that `build_leaf_cmd()` (or equivalent) embeds the C-4 scope (e.g. hygiene: NO `--source-prefix`; security/dependency: the production prefixes; docs: the living-docs prefixes incl. `README.md` and 16 `skills/*/SKILL.md`).
- [ ] GREEN: implement the <25-line wrapper calling `gate_common.gate_main` with `leaf_cmd` = the IN-REPO leaf script + C-4 scope, `findings_file` = `.self_audit_out/<class>/<LEAF>_findings.json`, snapshot/baseline per C-1.
- [ ] VERIFY live (no baseline yet — run the script directly, expect a controlled FAIL or PASS, never a crash): `python3 scripts/check_security_audit.py --baseline <(echo '[]')` style smoke is NOT required; instead run `python3 scripts/check_<class>.py --baseline /dev/null` only if `/dev/null` parses — otherwise create a throwaway empty-array file under `/tmp`. Expected: security → fail with 64 `new_findings`; hygiene → pass 0; docs → fail with 18; dependency → pass 0. Record outputs.
- [ ] Gates: `python3 -m pytest tests -q` green; `npm run check` (still the 5-gate chain) green — the new script is in self-audit + coverage scope, so it must be finding-clean and ≥50% covered NOW.
- [ ] Commit: `feat(gates): check:<class> ratchet script + tests (SP8 G2-<n>)` (npm wiring deliberately NOT here — C-5).

**G2-6: runbooks.**
- [ ] Write the four runbooks (C-1 paths), cloning `docs/self-audit/coverage-gap.md` structure: what the gate runs (exact command + scope and WHY — including the hygiene unprefixed rationale, the docs living-docs rationale + crash story, dependency `manifest:false` semantics), ratchet discipline (equality, stale ⇒ same-commit baseline edit), identity coarseness note (C-2), seeding record (filled in at G4-R1), and the freeze policy pointer.
- [ ] Commit: `docs(self-audit): runbooks for the four SP8 gates (SP8 G2-6)`.

## Task G3 — coverage ratchet 2→1

- [ ] Edit `scripts/coverage_gap_baseline.json`: remove the `scripts/check_self_audit.py` entry (cleared by the SP7-era in-process tests; pre-flight row 5 verified the snapshot no longer contains it). Keep `scripts/self_audit.py`.
- [ ] `npm run check:coverage` → Expected: `pass`, snapshot 1 == baseline 1.
- [ ] Commit: `chore(coverage): ratchet baseline 2->1 — check_self_audit.py is covered (SP8 G3)`.

## Task G4 — Phase-2 burn-down (serial, ≤4 rounds, ORCHESTRATOR adjudicates; C-5 + C-7)

Round order is FIXED: mechanical first, then security adjudication, then structural. Every fix commit keeps the current `npm run check` chain green (self-audit line-pin swaps ratcheted same-commit). Each round ends with a per-round table (class | fixed | frozen | residual | gate state) appended to the relevant frozen log's round log and mirrored in the G5 report.

**R1 — fix-first sweep + SEED (the only seeding round, C-5):**
- [ ] Docs (mechanical): fix the 18 `doc_path_missing` outright — correct each dead reference in the 8 SKILL.mds + the SP7 run report to the real path, or delete the reference if the target is gone. A reference that is deliberately illustrative (documents a file the USER's repo would have, not this repo) is a freeze candidate, not a fix. Re-run the docs leaf (C-4 scope) → expect ≈0 findings.
- [ ] Hygiene: nothing to fix (0 pre-seed). Re-run to confirm 0.
- [ ] Security PREFER-FIX list (from the G1 snapshot; re-verify each path before editing):
  - 13 × `hashlib` (all highs): the sha1 finding-id idiom — add `usedforsecurity=False`. If the hit is in `shared/health_common.py`, fix it ONCE there and re-vendor byte-identical into every leaf copy (`npm run check:vendored` green); expect line-pin churn on the vendored-clone baseline entry → same-commit stale+new swap (the INT-6 pattern).
  - 1 × `hardcoded_tmp_directory`: replace the `/tmp` literal with `tempfile.gettempdir()` (or freeze if it is a documented artifact-path default — adjudicate on sight).
  - `shell=True` or unpinned-tool subprocess hits: NONE appeared in the pre-seed (no B602) — if any shows up on re-run, it is a MUST-FIX.
  - 1 × `try_except_continue`: narrow the exception or comment-justify; fix if ≤5-line diff, else freeze with justification.
- [ ] Security adjudication (the residual): 26 × `subprocess_without_shell_equals_true` + 17 × `blacklist` + 4 × `start_process_with_partial_path` + 2 × `hardcoded_password_string` — audit tools that legitimately shell out to pinned tools. PREFER FIX where cheap (absolute tool resolution, constant renames); freeze the rest PER-FINDING in `scripts/security_frozen.md` with justifications of the form "deliberate subprocess wrapper, list-args, no shell, pinned tool (<tool>==<ver>)" — each entry names its path :: leaf/metric :: reason. Target: zero unjustified entries.
- [ ] Structural: attempt nothing speculative in R1 (history: clone-extraction in this tree is net-negative — see `self_audit_frozen.md` R2/SP4-R3 evidence). Only take structural fixes the hotspot ranking marks high-value AND that the self-audit gate proves finding-neutral.
- [ ] **SEED + WIRE (one commit):** re-run all four leaves fresh over their C-4 scopes; write the four baselines from the POST-FIX snapshots (hygiene + dependency expected `[]`); create `scripts/security_frozen.md` (and `scripts/docs_consistency_frozen.md` only if docs residual > 0) per pre-flight row 13 format; apply ALL C-1 wiring (package.json `check` chain + `files` exclusions, `.gitignore`, `check_release.py` REQUIRED_SCRIPTS additions). Run `npm run check` → **9 gates green**. Commit: `feat(gates): seed SP8 baselines + wire 4 gates into npm run check (SP8 G4-R1)`.
- [ ] R1 table committed (in the frozen logs' round logs).

**R2 — security/docs residual shrink (optional but attempt):** pick ≤5 frozen entries with the weakest justifications; attempt real fixes; every cleared entry = baseline ratchet-down in the same commit. STOP the round on any gate regression you cannot ratchet honestly.

**R3 — structural, hotspot-ranked:** ≤3 attempts at the top hotspot/code-health intersections; the equality gate adjudicates — any net-positive finding delta = discard the attempt (worktree-local, never committed). Document discarded attempts in the round table (that evidence is valuable: it is the SP4-R3 "extraction is net-negative" ledger continued).

**R4 — convergence buffer:** only if R2/R3 left a started-but-unfinished ratchet. Otherwise skip and declare convergence after R3. Growth anywhere after seeding = STOP + report.

## Task G5 — run report + final verification

- [ ] Final gate sweep, read real output (gotcha row 14 — never trust a piped exit code): `npm run check` → 9 × `"status": "pass"` (or documented expected payloads); `python3 -m pytest --collect-only -q` → 645 + N, zero errors; `python3 -m pytest tests -q` green.
- [ ] Write `$RUN/run_report.json` + `$RUN/run_report.md` per pre-flight row 10 — ALL keys: `lanes` from G0's bootstrap report; `findings_totals` summed per signal across `$RUN/*/`; `backlog` = {accepted: <fixes done>, deferred: <frozen count>, coverage_gated: 0}; `batches` = one entry per Phase-2 round (+ one per G2 task), each with evidence (commit SHA + gate output); `verification` = the exact commands + exit codes from this task; `warnings` (e.g. raw coverage.json not committed; performance/orchestration lanes manual).
- [ ] Final numbers table (C-8 actuals) inside `run_report.md`.
- [ ] Commit: `docs(audits): SP8 Track G run report (B4 contract)`. **Track G DoD:** G0–G5 all checked with evidence; 9 gates green; equality holds everywhere; zero unjustified baseline entries; NOTHING pushed.

---

# TRACK H — repo-B self-audit (cap 2; repo = `/home/jakub/projects/repo-audit-refactor-optimize`)

## Task H0 — bootstrap probe on itself

- [ ] Record `git rev-parse HEAD` (expect `cbf12ab...`); `python3 -m pytest tests/ -q` → 79 passed. `TS=$(date -u +%Y%m%dT%H%M%SZ); RUN=docs/audits/$TS`.
- [ ] `python3 ~/.claude/skills/repo-audit-refactor-optimize/scripts/check_skill_requirements.py --repo /home/jakub/projects/repo-audit-refactor-optimize --out-dir /home/jakub/projects/repo-audit-refactor-optimize/$RUN --extra-root ~/.claude/skills` — record lane states + the B2 unreferenced-skills advisory verbatim; commit.

## Task H1 — diagnosis wave (all applicable lanes; installed leaf copies from `~/.claude/skills/<leaf>/scripts/`)

- [ ] Coverage artifact: `python3 -m pytest tests/ -q --cov=scripts --cov-report=json:/tmp/sp8-h/coverage.json` → suite green; then coverage lane: `python3 ~/.claude/skills/coverage-gap-audit/scripts/coverage_gap_audit.py --root . --coverage-json /tmp/sp8-h/coverage.json --source-prefix scripts --out-dir $RUN/coverage`.
- [ ] Umbrella: `python3 ~/.claude/skills/code-health-audit-pipeline/scripts/code_health_pipeline.py --root . --out-dir $RUN/code-health --coverage-json /tmp/sp8-h/coverage.json --source-prefix scripts`.
- [ ] Security: `... security_audit.py --root . --out-dir $RUN/security --source-prefix scripts`; Hygiene: `... repo_hygiene_audit.py --root . --out-dir $RUN/hygiene` (no prefixes); Docs: `... docs_consistency_audit.py --root . --out-dir $RUN/docs --source-prefix README.md --source-prefix SKILL.md --source-prefix CHANGELOG.md --source-prefix references --source-prefix docs --source-prefix agents --source-prefix scripts` (fixtures under `tests/` excluded by omission — same rationale as repo-A's C-4); Dependency: `... dependency_audit.py --root . --out-dir $RUN/dependency --source-prefix scripts`; Hotspot: `... hotspot_audit.py --root . --out-dir $RUN/hotspot --rev $(git rev-parse HEAD) --max-commits 500`.
- [ ] Playbook-driven triage: per the skill's own SKILL.md workflow + `references/prioritization.md`, synthesize `$RUN/backlog.md` — every finding classified accepted-mechanical / deferred-structural (SP9) / coverage-gated, with the playbook rule cited per row. Honest manual notes for manual lanes (performance: no benchmark surface; orchestration: self-referential).
- [ ] Commit artifacts + backlog.

## Task H2 — mechanical-only remediation

- [ ] Apply ONLY mechanical lint-class fixes from the accepted list (formatting, unused imports, dead references in docs). After EACH fix: `python3 -m pytest tests/ -q` → 79 passed (a fix that changes test count or behavior is NOT mechanical — revert it to the backlog). Structural findings: backlog ONLY, no gate extension in repo-B this round (out-of-scope table).
- [ ] Commit per fix batch with the finding ids in the message.

## Task H3 — run report (B4, fail-closed)

- [ ] `$RUN/run_report.{json,md}` with ALL pre-flight row 10 keys (`orchestrator_skill_version: "0.3.1"`; `lanes` from H0; `backlog` counts from H1; `batches` = H2 batches with evidence; `verification` = pytest + any re-run lanes). Commit. **Track H DoD:** probe + all-lane artifacts + backlog + run report committed; suite 79 green; nothing pushed.

---

# TRACK P — perf repo self-audit + first performance-lane exercise (cap 2; repo = `/home/jakub/projects/perf-benchmark-skill`)

## Task P0 — bootstrap probe

- [ ] Record `git rev-parse HEAD` (expect `ceff6b7...`); `python3 -m pytest -q` → 151 passed. `TS=$(date -u +%Y%m%dT%H%M%SZ); RUN=docs/audits/$TS`.
- [ ] Run the checker (`--repo /home/jakub/projects/perf-benchmark-skill --out-dir .../$RUN --extra-root ~/.claude/skills`); expect the performance lane ≠ manual here (this repo HAS a benchmark surface) — record actual states; commit.

## Task P1 — diagnosis lanes

- [ ] Coverage artifact: `python3 -m pytest -q --cov=scripts --cov=perf-optimization/scripts --cov-report=json:/tmp/sp8-p/coverage.json`; coverage lane + umbrella as in H1 but with `--source-prefix scripts --source-prefix perf-optimization/scripts`.
- [ ] Security / hygiene / docs / dependency / hotspot as in H1, adapted: security+dependency prefixes = `scripts`, `perf-optimization/scripts`; docs prefixes = `README.md SKILL.md references docs perf-optimization/SKILL.md perf-optimization/references` (+ `scripts`, `perf-optimization/scripts` for the py side); hygiene unprefixed; hotspot `--rev HEAD --max-commits 500`. NOTE: `pyproject.toml` EXISTS here → the dependency lane is a REAL manifest run (expect `manifest:true`; findings possible — record, do not auto-fix).
- [ ] Commit artifacts.

## Task P2 — performance lane, first full exercise (tier fast; valgrind absent)

- [ ] Baseline run: `python3 scripts/perf_benchmark_pipeline.py --root . --out-dir $RUN/perf-before --target "python3 benchmarks/bench_parse_massif.py {SIZE}" --tier fast --sizes 1000,4000,16000 --expected-complexity linear --max-cv 5.0 --baseline-ledger docs/perf/baseline_ledger.jsonl --findings-out $RUN/perf-before/perf_findings.json`
  - Expected: exit 0; `benchmark_summary.json` with `environment` fingerprint + `wall_time_percentiles`; ledger created at `docs/perf/baseline_ledger.jsonl` (first line; `vs_last`/`vs_best` empty-history behavior recorded); PERF findings file written (possibly empty if all dimensions green — record either way). If CV > 5% on a noisy box: re-run once; if still noisy, record `N/A (noise)` dimensions honestly.
- [ ] Commit: bench artifacts + the new ledger.

## Task P3 — ONE bounded optimization attempt (accept or documented no-win — both valid; SP6 Phase 2 already found no-win, so no-win is LIKELY and fine)

- [ ] `python3 perf-optimization/scripts/select_candidate.py --findings $RUN/perf-before/perf_findings.json --out $RUN/opt/candidate.json` — Expected: a deterministic candidate, or the algorithmic STOP gate / empty-findings refusal. If STOP/refusal: record verbatim, skip to P4 with verdict "no candidate" (valid outcome).
- [ ] If a candidate exists: apply ONE bounded change per the `perf-optimization/references/optimization-playbook.md` discipline (single commit, revertable); re-measure with the IDENTICAL P2 command into `$RUN/perf-after` (same sizes, same tier, same ledger); `python3 -m pytest -q` → record exit code.
- [ ] `python3 perf-optimization/scripts/verify_win.py --before $RUN/perf-before/benchmark_summary.json --after $RUN/perf-after/benchmark_summary.json --suite-exit-code <code> --ledger docs/perf/baseline_ledger.jsonl --out $RUN/opt/verdict.json` — accept ⇒ keep the commit; reject ⇒ `git revert` the change commit (keep the evidence), verdict committed either way.

## Task P4 — run report

- [ ] `$RUN/run_report.{json,md}`, ALL B4 keys; performance lane evidence = ledger lines + verdict; `verification` includes the final `python3 -m pytest -q` → 151 passed. Commit. **Track P DoD:** probe + diagnosis + ledger + verdict (win or honest no-win) + run report committed; suite 151 green; nothing pushed.

---

# Global schedule & Definition of Done

```
concurrent, zero shared writes:   G (repo-A)   H (repo-B)   P (repo-P)
within G, serial:                 G0 -> G1 -> G2 -> G3 -> G4 (R1..R4) -> G5
within H, serial:                 H0 -> H1 -> H2 -> H3
within P, serial:                 P0 -> P1 -> P2 -> P3 -> P4
```

**Global DoD (the human's acceptance checklist):**
1. repo-A: `npm run check` = **9 gates green** in the C-1 chain; `check:selfaudit` equality holds; coverage baseline = 1; four new baselines seeded with **zero unjustified entries** (every freeze individually justified in its frozen log); collect-only 645+N zero errors; per-track evidence list in the G5 run report (bootstrap artifacts, 8 diagnosis lanes, per-round tables, final numbers per C-8 actuals).
2. repo-A docs-consistency leaf no longer crashes on out-of-root absolute path tokens (G2-1 test proves it).
3. repo-B: probe + all-lane diagnosis artifacts + prioritized SP9 backlog + B4-complete run report committed; 79 passed; mechanical-only diffs.
4. repo-P: probe + diagnosis artifacts + `docs/perf/baseline_ledger.jsonl` + select/verify evidence (accept or documented no-win) + B4-complete run report committed; 151 passed.
5. Run reports committed in ALL THREE repos, every pre-flight row 10 key present (the B4 contract fails closed — verify key-by-key).
6. NOTHING pushed, tagged, or released anywhere — the human reviews all three repos.

---

# Launch blocks (paste ONE per fresh Opus session)

## Launch G — repo-audit-skills total self-audit

```
You are the ORCHESTRATOR (Opus) for SP8 TRACK G in /home/jakub/projects/repo-audit-skills
(repo-A, main, NO worktree — you own the whole repo; tracks H/P run in OTHER repos, zero shared
writes). Coordinate ONLY, never implement. Workers: OpenCode DeepSeek v4 Pro Max via
opencode-worker-bridge (file-backed packets), cap 4. Automatic ONE-WAY fallback to native Opus
subagent workers ONLY on infrastructure dispatch failure (credits/quota/auth/bridge unreachable);
a gate-failing CHANGE is discard/retry, never a backend switch. A worker's green is NOT evidence
— re-run every gate yourself and read real output.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-11-sp8-total-self-audit.md
— "Empirical pre-flight", "Contracts" C-1..C-8, Tasks G0–G5. Implement VERBATIM via TDD. Pattern
files: scripts/check_self_audit.py + tests/test_check_self_audit.py (the gate pattern you clone),
scripts/self_audit.py (_prefixes = production scope), scripts/self_audit_frozen.md (frozen-log
format), docs/self-audit/coverage-gap.md (runbook format).

PRE-FLIGHT (any failure -> STOP and report): git status clean; rev-parse HEAD (expect 14fc35b...,
else record + npm run check must be green); npm run check -> 5 passes; python3 -m pytest
--collect-only -q -> 645, zero errors; python3 -c "import bandit" works.

ORDER: G0 bootstrap evidence (commit) -> G1 diagnosis wave (parallel cap 4, read-only, disjoint
$RUN subdirs; coverage artifact FIRST, then umbrella w/ --coverage-json; hotspot --rev HEAD
--max-commits 500; expect security 64 / hygiene 0 / docs 18 / dependency manifest:false 0;
mutation: top-3 hotspot files, --max-mutants 150 each, NEVER mutmut at repo root) -> G2 gates,
TDD, one commit each (G2-0 gate_common + check_self_audit rewire with its tests UNCHANGED; G2-1
docs-leaf out-of-root crash fix; G2-2..5 four <25-line check scripts; G2-6 runbooks; after EVERY
commit npm run check green) -> G3 coverage ratchet 2->1 -> G4 Phase-2 (serial, <=4 rounds, YOU
adjudicate: R1 fix-first [18 docs refs; 13 hashlib usedforsecurity=False — if in
shared/health_common.py fix once + re-vendor byte-identical; tmp-dir literal] then per-finding
security freezes with justifications, THEN seed all 4 baselines + wire npm chain to 9 gates in
ONE commit; R2-R4 shrink-only; growth = STOP) -> G5 B4 run report ($RUN/run_report.{json,md},
ALL schema keys) + final numbers.

HARD RULES: baselines seeded ONLY at end of R1, never from a raw first snapshot; zero blanket
freezes; duplication baseline entries are LINE-PINNED — any clone-pair file edit = stale+new swap
ratcheted in the SAME commit; backgrounded `npm run check | tail` reports tail's exit — grep the
gate JSON instead; do NOT commit raw coverage.json; DO NOT push/tag/release. Final report:
per-task evidence, C-8 actuals table, frozen-entry count with zero unjustified.
```

## Launch H — repo-audit-refactor-optimize self-audit

```
You are the ORCHESTRATOR (Opus) for SP8 TRACK H in
/home/jakub/projects/repo-audit-refactor-optimize (repo-B, main — you own this repo ONLY; tracks
G/P run elsewhere, zero shared writes). Coordinate ONLY, never implement. Workers: OpenCode
DeepSeek v4 Pro Max via opencode-worker-bridge (file-backed packets), cap 2. ONE-WAY fallback to
native Opus subagents ONLY on infrastructure dispatch failure; gate-failing changes are
discard/retry, never a backend switch. A worker's green is NOT evidence — re-run gates yourself.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-11-sp8-total-self-audit.md
— "Empirical pre-flight" rows 6/10/11, Contracts C-5/C-6, Tasks H0–H3. Also read THIS repo's own
SKILL.md + references/pipeline.md ("Run Report" section — the B4 contract you must satisfy in
your own repo) + references/prioritization.md (playbook triage rules).

PRE-FLIGHT (failure -> STOP): git status clean; rev-parse HEAD (expect cbf12ab...);
python3 -m pytest tests/ -q -> 79 passed.

ORDER: H0 bootstrap probe ON ITSELF via
python3 ~/.claude/skills/repo-audit-refactor-optimize/scripts/check_skill_requirements.py
--repo <this repo> --out-dir <this repo>/$RUN --extra-root ~/.claude/skills
(RUN=docs/audits/$(date -u +%Y%m%dT%H%M%SZ), ONE timestamp for the whole track; record lane
states + the unreferenced-skills advisory verbatim; commit) -> H1 diagnosis wave using INSTALLED
leaf copies (~/.claude/skills/<leaf>/scripts/): coverage artifact first (pytest --cov=scripts
--cov-report=json), then umbrella/security/hygiene/docs/dependency/hotspot per Task H1's exact
commands and scopes (fixtures excluded from docs scope by omission); playbook-driven triage into
$RUN/backlog.md — every finding classified accepted-mechanical / deferred-structural-SP9 /
coverage-gated with the playbook rule cited; honest manual notes for manual lanes; commit -> H2
remediation: ONLY mechanical lint-class fixes; after EACH batch python3 -m pytest tests/ -q must
stay 79 passed (anything that changes behavior or test count goes back to the backlog);
structural findings -> backlog ONLY, NO gate extension in repo-B this round -> H3 run report
$RUN/run_report.{json,md} with ALL B4 schema keys (schema_version 1, repo_root, started/finished
UTC, orchestrator_skill_version 0.3.1, lanes, findings_totals, backlog counts, batches with
evidence, verification command+exit list, warnings). The contract fails closed on any missing
key — verify key-by-key before committing.

HARD RULES: write ONLY inside this repo; commit per task; DO NOT push. Final report: lane
artifact list, backlog summary (counts per class), suite evidence 79 green, run-report paths.
```

## Launch P — perf repo self-audit + performance lane

```
You are the ORCHESTRATOR (Opus) for SP8 TRACK P in /home/jakub/projects/perf-benchmark-skill
(repo-P, main — you own this repo ONLY; tracks G/H run elsewhere, zero shared writes). Coordinate
ONLY, never implement. Workers: OpenCode DeepSeek v4 Pro Max via opencode-worker-bridge
(file-backed packets), cap 2. ONE-WAY fallback to native Opus subagents ONLY on infrastructure
dispatch failure; gate-failing changes are discard/retry, never a backend switch. A worker's
green is NOT evidence — re-run gates yourself. Valgrind is ABSENT on this machine: --tier fast
ONLY, record the limitation honestly.

READ FIRST, authoritative:
/home/jakub/projects/repo-audit-skills/docs/superpowers/plans/2026-06-11-sp8-total-self-audit.md
— "Empirical pre-flight" rows 6/10/11/12, Contracts C-6/C-7, Tasks P0–P4. Also
perf-optimization/references/optimization-playbook.md (bounded-change discipline) and
~/.claude/skills/repo-audit-refactor-optimize/references/pipeline.md "Run Report" (B4 contract).

PRE-FLIGHT (failure -> STOP): git status clean; rev-parse HEAD (expect ceff6b7...);
python3 -m pytest -q -> 151 passed; benchmarks/bench_parse_massif.py exists.

ORDER: P0 bootstrap probe (check_skill_requirements.py --repo <this repo> --out-dir
<this repo>/$RUN --extra-root ~/.claude/skills; RUN=docs/audits/$(date -u +%Y%m%dT%H%M%SZ), one
timestamp; performance lane expected != manual here; commit) -> P1 diagnosis lanes per Task P1
(installed leaves; prefixes scripts + perf-optimization/scripts; pyproject.toml EXISTS so the
dependency lane is a real manifest:true run — record findings, do NOT auto-fix; commit) -> P2
first full performance-lane exercise per Task P2's exact command (tier fast, sizes
1000,4000,16000, --max-cv 5.0, --baseline-ledger docs/perf/baseline_ledger.jsonl, --findings-out;
commit artifacts + ledger) -> P3 ONE bounded optimization attempt: select_candidate.py on the
PERF findings (its algorithmic STOP gate or empty-findings refusal = valid "no candidate"
outcome, record verbatim and skip to P4); if a candidate: ONE revertable change commit, identical
re-measure into $RUN/perf-after, pytest exit recorded, verify_win.py with --ledger; accept ->
keep, reject -> git revert (keep evidence). SP6 Phase 2 already found no-win, so no-win is LIKELY
and FINE -> P4 run report $RUN/run_report.{json,md} with ALL B4 keys (fails closed; verify
key-by-key), verification includes final python3 -m pytest -q -> 151 passed.

HARD RULES: ONE optimization attempt max; never fabricate a win — verify_win's verdict is the
only authority; write ONLY inside this repo; commit per task; DO NOT push. Final report: lane
artifacts, ledger lines, candidate + verdict JSONs, suite evidence, run-report paths.
```

## Codex orchestrator variant

To run any block under a Codex orchestrator, apply the SP7 plan's transformation rule verbatim (`docs/superpowers/plans/2026-06-10-sp7-parallel-skill-tracks.md`, "Codex orchestrator variant"): swap the identity line, swap the fallback target to native Codex subagents (same one-way infra-failure-only rule), and append the ignore-Claude-sub-skill-notes line. Nothing else changes.

## Status notes (2026-06-11, plan time)

- Pre-seed dry-runs in pre-flight row 7 were executed read-only (out-dirs in /tmp) at 14fc35b on 2026-06-11; Track G re-verifies them in G1 before Phase 2 and treats drift as a finding, not a blocker.
- The docs-consistency crash (row 7) is the first material bug found by SP8 dogfooding, before the sprint even launched. G2-1 fixes it with TDD; the C-4 docs-gate scope is independently justified (immutable historical records stay out of baselines) — the fix is NOT a substitute for the scope, nor vice versa.
- bandit==1.9.4 turned out to be already installed on the local interpreter (SP7 pre-flight row 10 said otherwise — it was installed during SP7 A5 development); repo-A CI already pins it, so the new `check:security` gate changes nothing in CI dependencies.
