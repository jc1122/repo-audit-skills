---
name: docs-consistency-audit
version: 0.5.7
description: >
  Deterministic, advisory docs-vs-reality audit for Python docs and command docs
  that emits LINT findings. Compares documented CLI flags against actual
  argparse parsers, checks doc paths for dead references, flags stale version
  pins, and optionally reports docstring coverage. Never mutates source.
---

# docs-consistency-audit

## Overview

A code-health leaf skill that audits `*.md` files for consistency with the
codebase and emits `LINT` findings for documented CLI flags missing from
argparse parsers, dead doc paths, stale version pins, and optional public-symbol
docstring coverage.

## Quick Start

```bash
python3 scripts/docs_consistency_audit.py \
  --root /path/to/repo \
  --source-prefix src/pkg/ \
  --out-dir /tmp/docs-consistency
```

Docstring coverage is off by default. Enable it with `--config
/path/to/thresholds.json` containing `{"docstring_min_percent": 80}`.

## Flags

| Flag | Required | Repeatable | Description |
|---|---|---|---|
| ``--root`` | yes | no | Repository root to audit |
| ``--source-prefix`` | no | yes | Prefix filter for in-scope files (default ``[]`` = everything) |
| ``--exclude-prefix`` | no | yes | Root-relative prefix filter excluded after inclusion |
| ``--out-dir`` | yes | no | Directory for output files |
| ``--config`` | no | no | JSON file overriding ``DEFAULT_THRESHOLDS`` |
| ``--format`` | no | no | Output format: ``json`` (default) or ``md`` |
| ``--filesystem-paths`` | no | no | Resolve doc path tokens against the filesystem instead of git-tracked paths |

Scope is inclusion first, exclusion second: repeat ``--source-prefix`` to limit
the root-relative file set, then repeat ``--exclude-prefix`` to remove matching
root-relative prefixes from that included set.

## Exit Codes

- ``0`` -- clean: no findings.
- ``1`` -- advisory findings present.
- ``2`` -- tool or config error.

## Output

- ``docs-consistency_findings.json`` -- sorted findings (shared schema, signal ``LINT``).
- ``docs-consistency_report.md`` -- human-readable summary, including skipped token counts.
- stdout status JSON -- includes ``status``, ``findings``, ``leaf``,
  ``path_resolution``, and ``skipped_placeholder_tokens`` /
  ``skipped_output_path_tokens`` on success.

## Thresholds

``DEFAULT_THRESHOLDS = {"docstring_min_percent": None}``

Docstring coverage runs only when ``--config`` sets numeric
``docstring_min_percent``. Scoped ``*.py`` modules below threshold emit
``metric_name="docstring_percent"``.

## Finding Groups

### Unknown flags in documented commands

Confidence: ``medium``. Parse fenced ``bash``/``sh``/``shell``/``console``
blocks and ``$ `` prompt lines with ``shlex.split``. For ``python``/``python3``
commands targeting an existing script, import only modules whose AST contains
``import argparse`` and a top-level ``def build_parser``. Enumerate
``parser._actions``; documented flags absent from parser option strings produce
findings.

### Dead doc paths

Confidence: ``medium``. Inline code spans matching ``^[A-Za-z0-9_.\-/]+$`` that
contain ``/``, exclude ``://``, and have a source-file suffix are checked
against git-tracked paths when ``--root`` is in a git repository. Directory
tokens ending in ``/`` resolve when any tracked file exists below the directory.
Non-git roots and ``--filesystem-paths`` use filesystem existence instead.
Missing normal paths emit ``doc_path_missing``. Tokens containing ``<>{}$*`` are
skipped and counted in ``skipped_placeholder_tokens``. Tokens under
generated-output roots ``.self_audit_out/`` and ``/tmp/`` are skipped and
counted in ``skipped_output_path_tokens``. Other hidden or source-like missing
paths are not suppressed.

### Stale version pins

Confidence: ``high``. Package name/version are read from ``pyproject.toml``
``[project]`` or ``package.json``; if neither exists, skip the group.
``CHANGELOG*.md`` files are excluded. Mismatches produce findings.

### Docstring coverage

Confidence: ``medium``. Off by default; enabled only via ``--config``. See
Thresholds.

## Honest Limits

- Markdown heuristics are best-effort and miss non-standard formatting.
- The argparse guard uses private ``parser._actions`` after verifying it exists;
  guard tests should fail loudly if a future argparse release renames it.
- Targets are imported; only modules defining ``build_parser`` and importing
  argparse are eligible. Never point ``--root`` at untrusted code.
- Absolute path tokens resolving outside ``--root`` are skipped because they are
  environment-dependent and cannot be made root-relative.
- Exclude output-path/runtime references and immutable historical records with
  ``--exclude-prefix`` or freeze and justify them in docs.
- In git repositories, docs should reference tracked reality. Refer to
  generated artifacts by basename, placeholders, or an excluded generated-output
  section rather than depending on local untracked files.
- Placeholder suppression is only ``<>{}$*``; generated-output suppression is
  only ``.self_audit_out/`` and ``/tmp/``. Other missing paths still emit
  ``doc_path_missing``.
