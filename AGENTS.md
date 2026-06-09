# Agent Start

Read `README.md` before broad repository scans. Source edits belong in this checkout;
installed copies live under the configured skills root.

`shared/health_common.py` is the source of truth for the leaf helper. Each leaf vendors
a byte-identical copy at `skills/<leaf>/scripts/health_common.py`. After editing the
source, re-sync the copies and run `npm run check` (the vendored-copy check will fail if
they drift).

For release work:

```bash
npm run check
npm run pack:dry-run
```

Do not edit installed copies under `~/.agents/skills` or `~/.codex/skills` directly.
