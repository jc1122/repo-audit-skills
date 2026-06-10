"""Test helpers for test-redundancy-triage golden suite."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
TR_SCRIPT = SCRIPTS_DIR / "triage_redundancy.py"


def load_module(name: str = "triage_redundancy") -> Any:
    """Import triage_redundancy.py as a Python module in-process.

    Returns the module object.
    """
    spec = importlib.util.spec_from_file_location(name, str(TR_SCRIPT))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {TR_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_cli(args: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run triage_redundancy.py as a subprocess (not for coverage).

    Returns a CompletedProcess with stdout/stderr captured.
    """
    python = sys.executable
    return subprocess.run(
        [python, str(TR_SCRIPT)] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV into a list of dicts (calls read_csv_rows from the module)."""
    from triage_redundancy import read_csv_rows

    return read_csv_rows(path)


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file."""
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    """Read a text file."""
    return path.read_text(encoding="utf-8")
