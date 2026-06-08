# Repo Audit Skills

Umbrella package for deterministic repository audit skills:

- `repo-audit-refactor-optimize`
- `test-audit-pipeline`
- `test-quality-assurance`
- `test-redundancy-triage`
- `perf-benchmark`

The package is a source-of-truth bundle for release, reinstall, and installed-copy parity. It keeps development checkouts under `/home/jakub/projects` separate from runtime-installed skill copies under `$CODEX_HOME/skills`, `~/.codex/skills`, or `~/.agents/skills`.

## Relations

`test-quality-assurance` scores the quality of a test suite: behavior focus, contract coverage, assertion quality, pyramid balance, coverage/mutation gates, and prioritized improvements.

`test-redundancy-triage` classifies test cleanup candidates as keep, merge, or delete-safe using empirical deselection, similarity, branch-equivalence, coverage, mutation, and strict gate evidence.

`test-audit-pipeline` orchestrates both test skills. It collects coverage, runs quality scoring and redundancy triage, then merges the outputs into one report.

`perf-benchmark` is the performance lane. It profiles Python and C workloads across scaling, cache, branch, memory, and ASM signals.

`repo-audit-refactor-optimize` is the higher-level repository audit orchestrator. It can use the test audit pipeline, redundancy triage, code-quality/style skills, and performance lanes when available.

## Install

Install the latest GitHub version:

```bash
npx github:jc1122/repo-audit-skills
```

Install a pinned release:

```bash
npx github:jc1122/repo-audit-skills#v0.1.0
```

Install to a custom skills root:

```bash
npx github:jc1122/repo-audit-skills -- --dest /absolute/path/to/skills --force
```

From a local checkout:

```bash
node bin/install-repo-audit-skills.js --dest /absolute/path/to/skills --force
```

Useful installer commands:

```bash
node bin/install-repo-audit-skills.js --list
node bin/install-repo-audit-skills.js --version
node bin/install-repo-audit-skills.js --dry-run
```

The default destination is `$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise `~/.codex/skills`.

## Validation

Run the full local check:

```bash
npm run check
```

Run release-only checks:

```bash
npm run check:release
```

Check package contents:

```bash
npm run pack:dry-run
```

Before release, use `python3 scripts/check_release.py --require-clean` to verify the git tree is clean.

## Release Flow

1. Edit source files in this repository.
2. Run `npm run check`.
3. Run `npm run pack:dry-run`.
4. Commit the release changes.
5. Push `main`.
6. Tag `vX.Y.Z` matching `package.json`.
7. Create the GitHub release.
8. Reinstall into `/home/jakub/.agents/skills`.
9. Verify installed `SKILL.md` names, versions, and script help output.
