"""Evidence formatting helpers for test-effectiveness-audit findings.

These functions translate raw mutmut output into human-readable
evidence strings and resolve problem keys to their owning modules.
They are consumed by _emission.py during finding generation.
"""

from __future__ import annotations
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _parse import key_to_module  # noqa: E402


def _in_scope(rel: str, prefixes: list[str]) -> bool:
    """True when *rel* matches a source prefix (or no prefixes given)."""
    return not prefixes or any(rel.startswith(p) for p in prefixes)


def _resolve_module_for_key(problem_key: str, totals: dict[str, int]) -> str | None:
    """Map a mutmut problem key to its module total key.

    Uses key_to_module for the primary match; falls back to suffix
    matching when the totals dict uses a different path prefix than
    what key_to_module produces.
    """
    km = key_to_module(problem_key)
    if km in totals:
        return km
    candidates = [k for k in totals if k.endswith("/" + km)]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _read_results_text(work: Path) -> str:
    """Return mutmut results text from a captured file or via subprocess.

    If work/results.txt exists (captured fixture mode), reads it directly.
    Otherwise spawns 'mutmut results' in the work directory.
    """
    captured = work / "results.txt"
    if captured.exists():
        return captured.read_text(encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "mutmut", "results"],
        cwd=str(work),
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout


def _format_evidence(problems: dict[str, str]) -> str:
    """Format problem key=status pairs into a compact evidence string.

    Outputs up to 10 key=status pairs separated by '; '.
    If there are more than 10 survivors, appends a '+N more' trailer.
    Survivor keys are sorted for deterministic output.
    """
    survivor_keys = sorted(problems.keys())
    parts = [f"{k}={problems[k]}" for k in survivor_keys[:10]]
    evidence = "; ".join(parts)
    if len(survivor_keys) > 10:
        evidence += f" ...(+{len(survivor_keys) - 10} more)"
    return evidence


def _append_mutmut_show(
    evidence: str,
    survivor_keys: list[str],
    work: Path,
    run_mutmut_show: bool,
) -> str:
    """Append @@ hunk headers from 'mutmut show' for the first 3 survivors.

    Each survivor key spawns a short-lived 'mutmut show' subprocess.
    Only lines starting with '@@' (unified-diff hunk headers) are kept;
    everything else (full diffs, timing) is discarded.  Timeouts and
    OS errors are silently swallowed — evidence is best-effort.

    When *run_mutmut_show* is False (captured fixture mode), the
    original evidence is returned unchanged.
    """
    if not run_mutmut_show:
        return evidence
    extra_lines: list[str] = []
    for survivor_key in survivor_keys[:3]:
        try:
            show = subprocess.run(
                [sys.executable, "-m", "mutmut", "show", survivor_key],
                cwd=str(work),
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            for line in show.stdout.splitlines() + show.stderr.splitlines():
                stripped = line.strip()
                if stripped.startswith("@@"):
                    extra_lines.append(stripped)
        except (subprocess.TimeoutExpired, OSError):
            pass  # best-effort enrichment — skip on any failure
    if extra_lines:
        evidence += "\n" + "\n".join(extra_lines)
    return evidence
