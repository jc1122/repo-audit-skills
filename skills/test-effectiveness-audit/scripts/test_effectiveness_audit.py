#!/usr/bin/env python3
"""test-effectiveness-audit leaf — public entry point.

This module is intentionally thin.  All logic lives in private helpers:
  _parse.py    — mutmut output parsers and AST helpers
  _sandbox.py  — isolated mutmut work-directory setup
  _evidence.py — problem resolution and evidence formatting
  _emission.py — TEST finding emission (the core mutation pipeline)
  _pipeline.py — end-to-end analysis orchestration
  _report.py   — report rendering and threshold loading
  _cli.py      — argument parsing and main() entry point

The public API re-exports below preserve the A6 contract so existing
tests can continue importing from this module via load_module().
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402, F401 (vendored, re-exported)
from _cli import build_parser, main  # noqa: E402, F401
from _emission import (  # noqa: E402, F401
    LEAF,
    ToolError,
    findings_from_mutmut,
)
from _evidence import (  # noqa: E402, F401
    _append_mutmut_show,
    _format_evidence,
)
from _parse import (  # noqa: E402, F401
    estimate_mutants,
    key_to_module,
    module_totals,
    parse_results_text,
    read_scope_paths,
)
from _pipeline import analyze_tree  # noqa: E402, F401
from _report import (  # noqa: E402, F401
    DEFAULT_THRESHOLDS,
    load_thresholds,
    render_report,
)
from _sandbox import prepare_sandbox  # noqa: E402, F401


if __name__ == "__main__":
    sys.exit(main())
