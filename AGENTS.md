# Agent Start

Read `README.md` before broad repository scans. This package mirrors the release/install shape of `codex-goal-orchestration-skills`: source edits belong in this checkout, installed copies live under the configured skills root.

Use generated command output, script `--help`, and release-check failures before opening implementation source. Do not edit installed copies under `~/.agents/skills` or `~/.codex/skills` directly.

For release-oriented work, run:

```bash
npm run check
npm run pack:dry-run
```

For install verification, prefer a dry run first:

```bash
node bin/install-repo-audit-skills.js --dry-run --dest /home/jakub/.agents/skills --force
```

Then install only after confirming no dirty installed copy would be overwritten:

```bash
node bin/install-repo-audit-skills.js --dest /home/jakub/.agents/skills --force
```
