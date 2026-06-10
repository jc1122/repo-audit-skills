"""Mutmut output parsers and AST helpers for test-effectiveness-audit.

These stateless functions parse mutmut's text output and filesystem
layout. They form the foundation layer consumed by _evidence, _emission,
and _pipeline modules.  No mutmut subprocess calls happen here.

Public API (A6 contract):
  parse_results_text  — key=status dict from mutmut results output
  module_totals       — {module: total_mutants} from .meta files
  key_to_module       — convert mutmut key to module path
  estimate_mutants    — projected mutant count for budget checking
  read_scope_paths    — read root-relative paths from a scope file
"""

from __future__ import annotations
import ast
import json
import sys
from pathlib import Path

# Ensure vendored health_common and sibling helpers are importable
sys.path.insert(0, str(Path(__file__).resolve().parent))


def parse_results_text(text: str) -> dict[str, str]:
    """Parse mutmut results text -> {key: status}.

    Only lines containing '__mutmut_' are considered; everything else
    (timing info, mutmut header lines) is silently ignored.
    """
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if ": " in line and "__mutmut_" in line:
            key, _, status = line.partition(": ")
            out[key] = status.strip()
    return out


def module_totals(work: Path) -> dict[str, int]:
    """Map meta files to {module_rel_path: total_mutants}.

    Scans work/mutants/**/*.py.meta, reads each JSON, and counts
    entries in exit_code_by_key to determine the total mutant count
    per module.
    """
    totals: dict[str, int] = {}
    mutants_dir = work / "mutants"
    if not mutants_dir.is_dir():
        return totals
    for meta in sorted(mutants_dir.rglob("*.py.meta")):
        rel = meta.relative_to(mutants_dir).as_posix()[: -len(".meta")]
        data = json.loads(meta.read_text(encoding="utf-8"))
        totals[rel] = len(data.get("exit_code_by_key", {}))
    return totals


def key_to_module(key: str) -> str:
    """Convert mutmut key like 'pkg.mod.x_func__mutmut_1' to 'pkg/mod.py'.

    Strips the '.x_<name>__mutmut_<N>' suffix and replaces dots with
    forward slashes, appending '.py'.
    """
    dotted = key.split(".x_", 1)[0]
    return dotted.replace(".", "/") + ".py"


def _count_defs_in_file(path: Path) -> int:
    """Count FunctionDef + AsyncFunctionDef nodes in a .py file.

    Used by estimate_mutants to project the total mutant budget before
    running the expensive mutation pass.  Syntax errors are treated as
    zero definitions (the file likely has no importable functions).
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        return sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
    except SyntaxError:
        return 0


def estimate_mutants(
    root: Path,
    rel_paths: list[str],
    estimated_mutants_per_def: int,
) -> int:
    """Count function defs across scoped files/dirs, multiply by estimate.

    The result is used for the --max-mutants budget check before any
    mutation run is started, preventing accidental hours-long runs on
    overly broad scopes.
    """
    total_defs = 0
    for rel in rel_paths:
        p = root / rel
        if p.is_file() and p.suffix == ".py":
            total_defs += _count_defs_in_file(p)
        elif p.is_dir():
            for py_file in sorted(p.rglob("*.py")):
                total_defs += _count_defs_in_file(py_file)
    return total_defs * estimated_mutants_per_def


def read_scope_paths(root: Path, paths_file: Path) -> list[str]:
    """Read root-relative .py files/dirs from *paths_file*.

    Blank lines and lines starting with '#' are ignored.
    The caller is responsible for validating that the returned paths
    exist under *root*.
    """
    text = paths_file.read_text(encoding="utf-8", errors="replace")
    rels: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            rels.append(line)
    return rels
