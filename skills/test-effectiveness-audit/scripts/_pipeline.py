"""Main analysis pipeline for test-effectiveness-audit.

This module orchestrates the end-to-end mutation-testing flow:
  1. Read scope paths and estimate mutant budget
  2. Probe for mutmut availability
  3. Set up the isolated sandbox
  4. Run mutmut, export CI/CD stats
  5. Generate TEST findings from results
  6. Optionally filter by source prefixes

Consumed by the CLI entry point (test_effectiveness_audit.py).
"""

from __future__ import annotations
import importlib.util
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402
from _parse import estimate_mutants, module_totals, read_scope_paths  # noqa: E402
from _sandbox import prepare_sandbox  # noqa: E402
from _evidence import _in_scope  # noqa: E402
from _emission import ToolError, findings_from_mutmut  # noqa: E402


# Expose ToolError at pipeline level for CLI error handling.
# (Re-exported from _emission where it is defined.)
__all__ = ["ToolError", "analyze_tree"]


def _run_mutmut(work: Path, timeout: int) -> None:
    """Run mutmut and normalize tool failures into a CLI-safe ToolError."""
    try:
        subprocess.run(
            [sys.executable, "-m", "mutmut", "run"],
            cwd=str(work),
            timeout=timeout,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(
            f"mutmut run timed out after {timeout}s; increase "
            "mutmut_timeout_seconds or narrow --paths",
        ) from None
    except subprocess.CalledProcessError as exc:
        output = "\n".join(part for part in (exc.stdout, exc.stderr) if part)
        tail = "\n".join(output.strip().splitlines()[-20:]) or "<no output>"
        raise ToolError(f"mutmut run failed (exit {exc.returncode}): {tail}") from None


def analyze_tree(config: dict) -> tuple[list[hc.Finding], int]:
    """Run the full test-effectiveness pipeline.

    *config* is a dict with keys:
      root, source_prefixes, thresholds, paths_file, tests_dir,
      max_mutants, out_dir.

    Returns (findings, actual_total) where actual_total is the true
    number of mutants produced by mutmut (may differ from the estimate).

    Raises ToolError on budget violation, missing mutmut, or timeout.
    """
    root = config["root"]
    out_dir = config["out_dir"]

    # --- Phase 1: scope & budget validation ---
    rel_paths = read_scope_paths(root, config["paths_file"])
    if not rel_paths:
        return [], 0

    est = estimate_mutants(
        root,
        rel_paths,
        int(config["thresholds"]["estimated_mutants_per_def"]),
    )
    if est > config["max_mutants"]:
        raise ToolError(
            f"scope too large: ~{est} mutants > --max-mutants "
            f"{config['max_mutants']}; narrow --paths",
        )

    # --- Phase 2: tool availability ---
    if importlib.util.find_spec("mutmut") is None:
        raise ToolError("mutmut is not installed; pip install mutmut==3.6.0")

    # --- Phase 3: sandbox setup ---
    work = prepare_sandbox(root, rel_paths, config["tests_dir"], out_dir)

    # --- Phase 4: run mutmut ---
    timeout = int(config["thresholds"]["mutmut_timeout_seconds"])
    _run_mutmut(work, timeout)

    # Export CI/CD stats (best-effort, not critical)
    subprocess.run(
        [sys.executable, "-m", "mutmut", "export-cicd-stats"],
        cwd=str(work),
        check=False,
        capture_output=True,
        text=True,
    )

    # --- Phase 5: produce findings ---
    findings = findings_from_mutmut(work, config["thresholds"])
    actual_total = sum(module_totals(work).values())

    # --- Phase 6: source-prefix filtering ---
    source_prefixes = config["source_prefixes"]
    if source_prefixes:
        findings = [f for f in findings if _in_scope(f.path, list(source_prefixes))]

    return hc.sort_findings(findings), actual_total
