# dependency-audit detailed usage

## Purpose

This leaf compares declared dependencies against imported dependencies discovered
from AST. It emits advisory findings when those sets diverge.

Audit groups:

1. **Unused declared** — declared but not used. Signal `DELETE`, severity
   `low`, confidence `medium`, metric `declared_unused`.
2. **Undeclared imported** — imported third-party distribution not declared.
   Signal `RESTRUCTURE`, metric `import_undeclared`, confidence high/medium by
   mapping heuristics.
3. **Runtime test-only** — runtime dependency used only under `tests` paths or
   `test_*.py` files. Signal `RESTRUCTURE`, metric `runtime_dep_test_only`,
   confidence `medium`.
4. **Advisory mode enrichments** — optional C-8 report input adds
   `dependency_vulnerabilities` and `dependency_outdated` findings. Signal
   `RESTRUCTURE`.

## Finding shape

```json
{
  "id": "<sha1[:16]>",
  "leaf": "dependency",
  "signal": "RESTRUCTURE",
  "severity": "medium",
  "path": "src/app.py",
  "location": {
    "line_start": 5,
    "line_end": 5,
    "symbol": "yaml"
  },
  "metric": {
    "name": "import_undeclared",
    "value": 1.0,
    "threshold": 0.0
  },
  "evidence": {
    "tool": "ast",
    "raw": "import yaml at src/app.py:5"
  },
  "confidence": "high",
  "suggested_action": "Add pyyaml to project dependencies"
}
```

## CLI table

| Flag | Required | Repeatable | Description |
|---|---|---|---|
| `--root` | yes | no | Audit root path |
| `--source-prefix` | no | yes | Root-relative import-scan prefix filter |
| `--out-dir` | yes | no | Output directory for report files |
| `--config` | no | no | Optional JSON threshold override (currently no-op) |
| `--format` | no | no | `json` (default) or `md` |
| `--advisory-report` | no | no | Optional C-8 advisory report input |

## Exit contract

- `0` (`EXIT_CLEAN`) — no findings or no manifest.
- `1` (`EXIT_FINDINGS`) — at least one finding.
- `2` (`EXIT_ERROR`) — bad args, manifest parse errors, advisory parse errors.

## Manifest and no-manifest behavior

The manifest is root `pyproject.toml` with `[project]` and/or any root
`requirements*.txt`. If missing, dependency comparisons are skipped and the run is
reported as clean:

```json
{"status": "ok", "findings": 0, "leaf": "dependency", "manifest": false}
```

Stdout on success with findings:

```json
{"status": "ok", "findings": 3, "leaf": "dependency"}
```

## Runtime-declared-only test-scope rule

Only names from `[project.dependencies]` (not optional dependencies, not
`requirements*.txt`) are eligible for `runtime_dep_test_only`. If every usage
site for such a dependency falls inside test paths (`tests` path component) or
`test_*.py`, it is flagged as test-only.

## Advisory report (C-8 shape)

`--advisory-report` reads a single JSON blob once at startup without any network
activity. Malformed/unreadable reports are fatal (`EXIT_ERROR`).

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
        {
          "id": "PYSEC-2018-28",
          "severity": "high",
          "fix_versions": ["2.20.0"]
        }
      ]
    }
  ]
}
```

### Advisory severity mapping

| C-8 severity | Finding severity |
|---|---|
| `critical` | `high` |
| `high` | `high` |
| `medium` | `medium` |
| `low` | `low` |
| `null` | `medium` with medium confidence |

Advisory signal remains `RESTRUCTURE` by contract. `latest_version: null`
means unknown; no `dependency_outdated` finding is emitted.

## Import mapping rules

Heuristic mapping is exact for a small builtin table and otherwise normalizes
`_` to `-` and lowercases the import root module.

| Import name | Distribution |
|---|---|
| `PIL` | `pillow` |
| `cv2` | `opencv-python` |
| `yaml` | `pyyaml` |
| `sklearn` | `scikit-learn` |
| `bs4` | `beautifulsoup4` |
| `dateutil` | `python-dateutil` |
| `dotenv` | `python-dotenv` |
| `jwt` | `pyjwt` |
| `OpenSSL` | `pyopenssl` |
| `Crypto` | `pycryptodome` |
| `git` | `gitpython` |
| `fitz` | `pymupdf` |
| `attr` | `attrs` |
| `pkg_resources` | `setuptools` |
| `serial` | `pyserial` |
| `usb` | `pyusb` |
| `websocket` | `websocket-client` |
| `zmq` | `pyzmq` |
| `magic` | `python-magic` |
| `docx` | `python-docx` |
| `pptx` | `python-pptx` |

Matches from the table are high-confidence; normalized fallbacks are medium.
`sys.stdlib_module_names` are excluded and never trigger findings.

## Local module skip

Top-level imports are skipped when they resolve to local code:

- `<root>/<name>.py` exists
- `<root>/<name>/__init__.py` exists
- `<root>/<source-prefix>/<name>/` exists

## Honest limits

- Dynamic imports (`importlib`, custom loaders) are not captured.
- Heuristic import mapping can mis-map names.
- `requirements*.txt` parsing ignores complex syntax.
- Editable installs and install metadata are not modeled.
