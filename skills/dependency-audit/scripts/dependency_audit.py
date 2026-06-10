#!/usr/bin/env python3
"""Dependency-audit CLI shim."""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _impl import (  # noqa: E402
    DEFAULT_THRESHOLDS,
    LEAF,
    MODULE_TO_DIST,
    ToolError,
    analyze_tree,
    build_parser,
    collect_imports,
    declared_deps,
    load_thresholds,
    main,
    render_report,
)

__all__ = [
    "DEFAULT_THRESHOLDS",
    "LEAF",
    "MODULE_TO_DIST",
    "ToolError",
    "analyze_tree",
    "build_parser",
    "collect_imports",
    "declared_deps",
    "load_thresholds",
    "main",
    "render_report",
]


if __name__ == "__main__":
    sys.exit(main())
