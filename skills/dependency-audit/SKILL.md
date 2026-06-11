---
name: dependency-audit
version: 0.4.0
description: >
  Deterministic, advisory dependency audit for Python. Compiles declared
  dependencies (pyproject.toml [project] or requirements*.txt) against
  AST-collected imports and flags unused declared deps, undeclared imported
  deps, and runtime dependencies that are only exercised by tests. Accepts an
  optional external advisory report (C-8 shape) for vulnerability and
  outdated-package signal enrichment. Uses stdlib only; requires Python >=3.11
  (tomllib). Never mutates source.
---

# dependency-audit

Deterministic, advisory Python dependency audit. Never mutates source.

## Purpose

Compares the set of *declared* dependencies (from a project manifest) against
*imported* dependencies (collected via AST walk of all `.py` files under the
audit root). Produces actionable findings when the two diverge.

**Audit groups:**

1. **Unused declared** — a dependency is declared in the manifest but no import
   maps to it. Signal `DELETE`, confidence `medium` (dynamic imports and
   plugins are invisible to AST analysis).
2. **Undeclared imported** — an import resolves to a third-party distribution
   that is not declared in the manifest. Signal `RESTRUCTURE`.
3. **Runtime dependency only used in tests** — a dependency declared in
   `[project.dependencies]` (not optional-dependencies) whose every import site
   lies inside test directories or `test_*.py` files. Signal `RESTRUCTURE`.
4. **Advisory mode** (optional, requires `--advisory-report`) — enriches the
   audit with vulnerability and outdated-package findings from an external
   advisory report in C-8 shape. Signal `RESTRUCTURE` (never `SECURITY`;
   that signal is reserved for the security-audit leaf).

## Requirements

- **Python >= 3.11** — the leaf uses `tomllib` (stdlib) to parse
  `pyproject.toml`. No other dependencies beyond the Python standard library.

## Manifest rule

A *dependency manifest* is defined as:

- A root-level `pyproject.toml` containing a `[project]` table, OR
- Any root-level `requirements*.txt` file.

If **no manifest exists** in the audit root, all offline analysis groups are
skipped. The audit produces zero findings, exits 0, and the stdout status line
includes `"manifest": false`. Repositories that lack a dependency manifest are
reported explicitly instead of producing dependency findings.

## CLI

```
usage: dependency_audit.py [-h] [--root ROOT] [--source-prefix SOURCE_PREFIX]
                           [--out-dir OUT_DIR] [--config CONFIG]
                           [--format {json,md}] [--advisory-report PATH]
```

| Flag | Description |
|---|---|
| `--root` | Root directory of the target repository (required). |
| `--source-prefix` | Path prefix relative to `--root` to include. Repeatable. When given, only files whose root-relative path starts with one of the prefixes are scanned for imports. |
| `--out-dir` | Directory for output artifacts (required). |
| `--config` | JSON file overriding `DEFAULT_THRESHOLDS` (currently a no-op; the dict is empty). |
| `--format` | Output format for the report file: `json` (default) or `md`. |
| `--advisory-report` | Path to an external advisory report JSON file in C-8 shape (optional). See below. |

## Exit codes

| Code | Constant | Meaning |
|---|---|---|
| 0 | `EXIT_CLEAN` | No findings; or no manifest present. |
| 1 | `EXIT_FINDINGS` | At least one finding was produced. |
| 2 | `EXIT_ERROR` | Tool error (missing required args, unreadable manifest, malformed advisory report, etc.). |

## Outputs

Written to `--out-dir`:

- **`dependency_findings.json`** — JSON array of findings in the shared
  `health_common.Finding` shape (see below). Byte-deterministic across runs on
  the same tree.
- **`dependency_report.md`** — human-readable summary grouped by signal.

Stdout: one JSON status line.

On success with findings:
```json
{"status": "ok", "findings": 3, "leaf": "dependency"}
```

On success with no manifest:
```json
{"status": "ok", "findings": 0, "leaf": "dependency", "manifest": false}
```

On error:
```json
{"status": "error", "message": "<description>"}
```

## Finding shape

All findings use the shared schema defined in `health_common.Finding`:

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

| Finding group | signal | severity | confidence | metric_name |
|---|---|---|---|---|
| Unused declared | `DELETE` | `low` | `medium` | `declared_unused` |
| Undeclared imported | `RESTRUCTURE` | `medium` | high or medium (per mapping table) | `import_undeclared` |
| Runtime dep test-only | `RESTRUCTURE` | `low` | `medium` | `runtime_dep_test_only` |
| Advisory vulnerability | `RESTRUCTURE` | per C-8 severity mapping | `high` | `dependency_vulnerabilities` |
| Advisory outdated | `RESTRUCTURE` | `info` | `medium` | `dependency_outdated` |

## Thresholds

```python
DEFAULT_THRESHOLDS = {}
```

This leaf is rule-based; the empty dict exists for C-2 contract compatibility.
The `--config` flag accepts a JSON file but has no effect with current thresholds.

## Import-name to distribution mapping

The offline core maps top-level import names to distribution (PyPI) names using
a hardcoded 21-entry lookup table:

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

**Honest limit:** import-name to distribution mapping is heuristic beyond this
table. An exact table hit yields **high** confidence; any other import name is
normalized (lowercased, `_` → `-`) and treated as a **medium**-confidence guess.
There is no PyPI name resolver; simple normalization is often wrong (e.g.,
`redis` → `redis`, correct; `scipy` → `scipy`, correct; but `Image` → `image`,
incorrect — it should be `pillow`).

Standard-library modules are excluded via `sys.stdlib_module_names` and never
trigger findings.

## Local-module rule

A top-level import name is considered **local** (and thus skipped) when any of
the following exist under the audit root:

- `<root>/<name>.py`
- `<root>/<name>/__init__.py`
- `<name>` is a directory directly under any `--source-prefix` entry.

Local-module imports are never flagged as undeclared or mapped to a distribution.

## Test-only runtime dependency rule

When a dependency is declared in `[project.dependencies]` (NOT in
`[project.optional-dependencies]` or `requirements*.txt`) and every import site
for that dependency lies within test directories (paths containing `tests` as a
component) or files named `test_*.py`, the dependency is flagged as
`runtime_dep_test_only`. The rationale: a runtime dependency should be imported
at least once from production code; test-only use suggests it should be moved to
an optional or dev dependency group.

## Advisory report (C-8 shape)

The `--advisory-report` flag accepts a path to a JSON file in the C-8 shape,
shared with the security-audit leaf. The report is read once at startup; no
network calls are made. Malformed or unreadable reports produce a `ToolError`
(exit 2).

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

### Severity mapping

| C-8 `severity` | Finding severity |
|---|---|
| `"critical"` | `high` |
| `"high"` | `high` |
| `"medium"` | `medium` |
| `"low"` | `low` |
| `null` | `medium` (confidence `medium`) |

`latest_version` → `null` means unknown; no outdated finding is produced.

### Advisory signal

Advisory findings use signal `RESTRUCTURE`, **not** `SECURITY`. The
dependency-audit leaf merges before the SP7 schema bump; `SECURITY` is reserved
for the security-audit leaf (Track A5). This is a deliberate design choice:
dependency-audit is a structure/hygiene checker, not a security scanner.

## Umbrella registration

This leaf is registered in the code-health umbrella (`leaf_registry.json`) with:

- `languages: ["python"]`
- No `requires` key (the offline core needs no special artifacts)

The `--advisory-report` flag is standalone-only; the umbrella never passes it.

## Determinism

All offline findings are byte-deterministic across runs on the same tree:
imports are collected via AST walk in sorted path order; declared deps are
sorted; findings are sorted by `(path, line_start, signal, metric_name, symbol)`
before writing. The advisory report is read as-is; its contents are not
canonicalized.

## Limitations

- **Dynamic imports** (`importlib.import_module`, `__import__`, plugin systems,
  entry-point loading) are invisible to static AST analysis. The `declared_unused`
  finding uses `confidence: medium` for this reason and lists it in `evidence_raw`.
- **Import-name to dist mapping** is a heuristic (see table above). False
  negatives are possible for non-table imports.
- **`requirements*.txt` parsing** is line-split naive (splits on whitespace and
  `[<>=!~;`); complex pip flags (`-r`, `-e`, `--hash`) are not handled.
- **Editable installs** (`pip install -e .`) are not modeled — the audit
  operates on the source tree, not an installed environment.

## See also

- **security-audit** (`skills/security-audit`) — bandit-based security scanning
  with `SECURITY` signal and the same C-8 advisory-report contract.
- **code-health-audit-pipeline** — umbrella orchestrator that runs registered
  leaves including this one.
