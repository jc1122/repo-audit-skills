# SP9 K5 Convergence Run - repo-audit-skills

Schema: v2

## Release

- Version: `0.5.0`
- Release commit: `8fa2d14`
- Installer readback: 16 skills at `0.5.0`

## Verification

| Command | Result |
| --- | --- |
| `npm run check` | Pass; final coverage JSON `{"status":"pass","count":0,"baseline":0,"suites":17}` |
| `node bin/install-repo-audit-skills.js --list` | Pass; package `repo-audit-skills`, version `0.5.0`, 16 skills |
| direct wave run 2 vs run 3 | Pass; both had 2423 raw findings, 1015 normalized identities, 0 new/stale |

## Notes

The direct wave is advisory for repo-A because repo-A does not have a wave
baseline checker. The two consecutive wave outputs were identity-identical.

`python3 -m pytest -q` is not the repo-A suite gate; it failed from cross-suite
helper module name collisions. The official `check_coverage_gap.py` gate ran 17
suites in isolation and passed.
