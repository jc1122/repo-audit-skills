---
name: docs-consistency-audit
version: 0.4.0
description: >
  Deterministic, advisory docs-vs-reality audit for Python docs and command docs
  that emits LINT findings. Compares documented CLI flags against actual
  argparse parsers, checks doc paths for dead references, flags stale version
  pins, and optionally reports docstring coverage. Never mutates source.
---

# docs-consistency-audit

## Overview

A code-health leaf skill that audits documentation files (``*.md``) for
consistency with the codebase. It checks four groups:

1. **Unknown flags in documented commands** -- extracts fenced shell blocks,
   introspects target scripts via ``argparse``, and flags flags present in docs
   but absent from the parser.
2. **Dead doc paths** -- finds inline code spans referencing files that do not
   exist on disk.
3. **Stale version pins** -- detects version strings in docs that lag behind
   ``pyproject.toml`` or ``package.json``.
4. **Docstring coverage** -- reports the percentage of public symbols with
   docstrings (opt-in via ``--config``).

All findings emit the ``LINT`` signal.

## Quick Start

```bash
python3 scripts/docs_consistency_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/docs-consistency
```

For docstring coverage (off by default):

```bash
python3 scripts/docs_consistency_audit.py \
  --root /path/to/repo \
  --config /path/to/thresholds.json \
  --out-dir /tmp/docs-consistency
```

Where ``thresholds.json`` contains:

```json
{"docstring_min_percent": 80}
```

## Flags

| Flag | Required | Repeatable | Description |
|---|---|---|---|
| ``--root`` | yes | no | Repository root to audit |
| ``--source-prefix`` | no | yes | Prefix filter for in-scope files (default ``[]`` = everything) |
| ``--out-dir`` | yes | no | Directory for output files |
| ``--config`` | no | no | JSON file overriding ``DEFAULT_THRESHOLDS`` |
| ``--format`` | no | no | Output format: ``json`` (default) or ``md`` |

## Exit Codes

- ``0`` -- clean: no findings.
- ``1`` -- advisory findings present.
- ``2`` -- tool or config error.

## Output

- ``docs-consistency_findings.json`` -- sorted findings (shared schema, signal ``LINT``).
- ``docs-consistency_report.md`` -- human-readable summary.

## Thresholds

``DEFAULT_THRESHOLDS = {"docstring_min_percent": None}``

The docstring group is **off by default**. It is only enabled when ``--config``
sets a numeric ``docstring_min_percent``. When enabled, any scoped ``*.py``
module whose public-symbol docstring percentage falls below the threshold
produces a finding with ``metric_name="docstring_percent"``.

## Finding Groups

### Group 1 -- Unknown flags in documented commands
Confidence: ``medium``. Fenced blocks tagged ``bash``, ``sh``, ``shell``, or
``console`` are parsed; lines beginning with ``$ `` are split via
``shlex.split``. When the command is ``python``/``python3`` referencing an
existing script, the script is introspected with a guard: only modules whose
**AST** contains both ``import argparse`` **and** a top-level ``def
build_parser`` are ever imported. Flags are enumerated from
``parser._actions`` (a documented argparse private-API pin; the attribute is
tested to fail loudly if it vanishes). Doc flags not in the parser's known
option strings produce a finding.

### Group 2 -- Dead doc paths
Confidence: ``medium``. Inline code spans matching
``^[A-Za-z0-9_.\-/]+$`` containing ``/`` (but not ``://``) with a source-file
suffix are checked for existence on disk. Missing paths produce a finding.

### Group 3 -- Stale version pins
Confidence: ``high``. Package name and version are read from
``pyproject.toml`` ``[project]`` or ``package.json``; if neither exists the
group is skipped. ``CHANGELOG*.md`` files are **excluded** from version-pin
checks. Mismatches produce a finding.

### Group 4 -- Docstring coverage
Confidence: ``medium``. Off by default; enabled only via ``--config``. See
Thresholds above.

## Honest Limits

Markdown heuristics (fenced-block language tags, inline-code-span regex) are
best-effort and will miss non-standard formatting. The argparse flag-introspection
guard uses ``parser._actions``, a private attribute pinned after verifying it
exists on the current ``argparse`` version; a future ``argparse`` release could
rename it, and the guard test is written to fail loudly if that happens.

**Import-introspection caveat:** targets are imported; only modules defining build_parser and importing argparse are eligible; never point --root at untrusted code you would not import.

Absolute path tokens that resolve outside ``--root`` are skipped (environment-dependent, cannot be made root-relative).
