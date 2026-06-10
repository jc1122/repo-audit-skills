"""Finding emission for test-effectiveness-audit.

Translates raw mutmut results into TEST findings under the shared
code-health schema (health_common.Finding).  This module handles:

- collecting problem entries per module (_collect_module_problems)
- building individual findings (_make_finding)
- the main findings_from_mutmut pipeline entry point

Key accounting rule (A6 contract): only 'survived' and 'no tests'
statuses create TEST findings.  Timeout, suspicious, and skipped
mutants count as killed and do NOT drag down the kill rate.
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402 (vendored leaf helper)
from _parse import module_totals, parse_results_text  # noqa: E402
from _evidence import (  # noqa: E402
    _resolve_module_for_key,
    _read_results_text,
    _format_evidence,
    _append_mutmut_show,
)


# Mutmut statuses that indicate a test-suite weakness.
# All other statuses (timeout, suspicious, skipped, killed) count as
# successful kills for kill-rate calculation purposes.
PROBLEM_STATUSES = {"survived", "no tests"}

# Leaf identifier used in finding metadata and output filenames.
LEAF = "test-effectiveness"


class ToolError(RuntimeError):
    """Fatal tool error — reported to CLI with exit code 2."""


def _collect_module_problems(
    problem_entries: dict[str, str],
    totals: dict[str, int],
) -> dict[str, dict[str, str]]:
    """Map problem keys to their owning modules (PROBLEM_STATUSES only).

    Each problem key (e.g. 'pkg.mod.x_func__mutmut_1') is resolved to
    a module total key via _resolve_module_for_key.  Non-problem
    statuses (timeout, suspicious, etc.) are silently dropped.
    """
    module_problems: dict[str, dict[str, str]] = {m: {} for m in totals}
    for problem_key, status in problem_entries.items():
        if status not in PROBLEM_STATUSES:
            continue
        matched = _resolve_module_for_key(problem_key, totals)
        if matched:
            module_problems[matched][problem_key] = status
    return module_problems


def _make_finding(
    module_path: str,
    kill_rate: float,
    evidence_raw: str,
    threshold: float,
) -> hc.Finding:
    """Build a TEST finding from pre-computed values.

    The *threshold* parameter carries the configured min_kill_rate from
    --config (or DEFAULT_THRESHOLDS), ensuring the emitted finding
    faithfully records the threshold that was in effect at analysis time
    rather than a hardcoded constant.
    """
    severity = "high" if kill_rate < 0.5 else "medium"
    return hc.Finding(
        leaf=LEAF,
        signal="TEST",
        severity=severity,
        path=module_path,
        line_start=1,
        line_end=1,
        symbol="<module>",
        metric_name="mutation_kill_rate",
        metric_value=round(kill_rate, 3),
        metric_threshold=round(threshold, 3),
        evidence_tool="mutmut",
        evidence_raw=evidence_raw,
        confidence="high",
        suggested_action=(
            f"Strengthen assertions/cases for {module_path}: "
            "surviving mutants listed in evidence"
        ),
    )


def findings_from_mutmut(
    work: Path,
    thresholds: dict,
    root_rel_prefix: str = "",
) -> list:
    """Produce TEST findings for modules below the kill-rate threshold.

    This is the main entry point for mutation-testing analysis.  It:
    1. Reads module totals from mutmut .meta files
    2. Collects problem entries from mutmut results (captured or live)
    3. Computes per-module kill rates
    4. Emits findings for any module below *min_kill_rate*

    The *thresholds* dict must contain at least 'min_kill_rate'.
    *root_rel_prefix* is reserved for future scoping and currently unused.
    """
    min_kill_rate = float(thresholds["min_kill_rate"])

    totals = module_totals(work)
    if not totals:
        return []

    results_text = _read_results_text(work)
    problem_entries = parse_results_text(results_text)
    module_problems = _collect_module_problems(problem_entries, totals)

    # In captured-fixture mode (results.txt present), skip mutmut show
    # subprocess calls — evidence is already complete.
    run_mutmut_show = (
        not (work / "results.txt").exists() and (work / "setup.cfg").exists()
    )

    findings: list = []
    for module_path in sorted(totals):
        total = totals[module_path]
        problems = module_problems[module_path]
        if total == 0:
            continue
        kill_rate = (total - len(problems)) / total
        if kill_rate >= min_kill_rate:
            continue

        evidence_raw = _format_evidence(problems)
        evidence_raw = _append_mutmut_show(
            evidence_raw,
            sorted(problems.keys()),
            work,
            run_mutmut_show,
        )
        findings.append(
            _make_finding(module_path, kill_rate, evidence_raw, min_kill_rate)
        )

    return findings
