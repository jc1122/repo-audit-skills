"""bandit invocation and result-to-finding mapping for security-audit."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

TOOL_TIMEOUT = 300

# Bandit issue_severity labels are uppercase; we map to the shared schema
# four-level scale (info/low/medium/high) used across all code-health leaves.
_BANDIT_SEVERITY = {"LOW": "low", "MEDIUM": "medium", "HIGH": "high"}
# Bandit issue_confidence labels likewise map to the shared schema scale.
_BANDIT_CONFIDENCE = {"LOW": "low", "MEDIUM": "medium", "HIGH": "high"}
# Floating-point severity values for numeric metric recording:
# 1.0 = low, 2.0 = medium, 3.0 = high  (info=0, unused here).
_SEVERITY_VALUE = {"low": 1.0, "medium": 2.0, "high": 3.0}


class ToolError(RuntimeError):
    """Fatal tool/config error; the CLI maps it to a JSON error status (exit 2)."""


def _relpath(filename: str, root: Path) -> str:
    """Return *filename* relative to *root* as a POSIX path (absolute-safe).

    Two cases:
    - If *filename* is already relative, return it as-is (posix-form).
    - If *filename* is absolute, try to make it relative to *root*;
      fall back to the absolute posix form when it sits outside *root*.
    """
    candidate = Path(filename)
    if not candidate.is_absolute():
        return candidate.as_posix()
    base = root.resolve()
    try:
        return candidate.resolve().relative_to(base).as_posix()
    except ValueError:
        return candidate.as_posix()


def _targets(root: str, source_prefixes: list[str]) -> list[str]:
    """Existing --source-prefix dirs under *root*, or *root* itself.

    Bandit needs one or more filesystem roots to scan.  The optional
    ``--source-prefix`` arguments restrict the scan to subdirectories,
    but if none of those subdirectories actually exist we fall back to
    scanning the entire *root* tree.
    """
    base = Path(root)
    chosen = [base / p for p in source_prefixes if (base / p).exists()]
    if not chosen:
        chosen = [base]
    return [str(p) for p in chosen]


def _run(root: str, source_prefixes: list[str]) -> list[dict]:
    """Invoke pinned bandit and return its parsed ``results`` list.

    Bandit flags used here:
    - ``-r``: recursive scan under the target directories.
    - ``-f json``: machine-readable JSON output so we can parse the results
      programmatically (the default text output is for humans only).
    - ``-q``: quiet mode — suppresses progress and stats lines, leaving
      clean JSON on stdout.

    Exit-code handling: bandit returns 0 when it finds no issues and 1
    when it finds issues; both are "successful invocations" from our
    perspective.  Any other exit code (e.g. 2 for fatal error) means
    the tool itself failed and we raise ``ToolError``.

    We also route ``FileNotFoundError`` (the ``bandit`` module is not
    installed) and ``TimeoutExpired`` into ``ToolError`` so the CLI can
    surface a clean JSON error rather than a traceback.
    """
    if importlib.util.find_spec("bandit") is None:
        raise ToolError("bandit is not installed; pip install bandit==1.9.4")
    cmd = [
        sys.executable,
        "-m",
        "bandit",
        "-r",
        *_targets(root, source_prefixes),
        "-f",
        "json",
        "-q",
    ]
    try:
        proc = subprocess.run(
            cmd, text=True, capture_output=True, check=False, timeout=TOOL_TIMEOUT
        )
    except FileNotFoundError as exc:
        raise ToolError("bandit is not installed; pip install bandit==1.9.4") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"bandit timed out after {TOOL_TIMEOUT}s") from exc
    try:
        report = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        report = None
    # Exit codes 0 (clean) and 1 (issues found) are both valid results.
    # Anything else, or unparseable stdout, is a tool failure.
    if proc.returncode not in (0, 1) or report is None:
        detail = report.get("errors") if isinstance(report, dict) else None
        raise ToolError(
            f"bandit failed (exit {proc.returncode}); errors={detail}; "
            f"stderr={proc.stderr.strip()}"
        )
    return report.get("results", [])


def scan(root: str, source_prefixes: list[str]) -> list[hc.Finding]:
    """Bandit findings for *root* mapped to the shared SECURITY schema.

    Mapping details (one Finding per bandit result item):

    - ``severity``: bandit's ``issue_severity`` (LOW/MEDIUM/HIGH) mapped
      to the shared lower-case scale via ``_BANDIT_SEVERITY``.
    - ``metric_value``: the numeric equivalent of the severity
      (low=1.0, medium=2.0, high=3.0) stored in ``_SEVERITY_VALUE``.
    - ``metric_name``: ``"bandit_<test_id>"`` — embeds the bandit test
      identifier so consumers can filter or suppress specific tests.
    - ``line_end``: taken from bandit's ``line_range`` array (if
      present), otherwise defaults to ``line_start``.  ``line_range``
      may contain multiple line numbers; we take the maximum so the
      reported span covers the entire issue.
    - ``confidence``: bandit's ``issue_confidence`` mapped via
      ``_BANDIT_CONFIDENCE`` (same LOW/MEDIUM/HIGH → low/medium/high).
    - ``evidence_raw``: the bandit issue text concatenated with the
      test-id in brackets, e.g. ``"Possible hardcoded password [B105]"``.
    """
    findings: list[hc.Finding] = []
    base = Path(root)
    for item in _run(root, source_prefixes):
        rel = _relpath(item["filename"], base)
        severity = _BANDIT_SEVERITY[item["issue_severity"]]
        start = int(item["line_number"])
        # line_range may be absent or contain a single value; always
        # take the maximum to faithfully span the problematic region.
        end = max(int(n) for n in (item.get("line_range") or [start]))
        test_id = item["test_id"]
        findings.append(
            hc.Finding(
                leaf="security",
                signal="SECURITY",
                severity=severity,
                path=rel,
                line_start=start,
                line_end=end,
                symbol=item["test_name"],
                metric_name=f"bandit_{test_id}",
                metric_value=_SEVERITY_VALUE[severity],
                metric_threshold=0.0,
                evidence_tool="bandit",
                evidence_raw=f"{item['issue_text']} [{test_id}]",
                confidence=_BANDIT_CONFIDENCE[item["issue_confidence"]],
                suggested_action=(f"Review and remediate {test_id} at {rel}:{start}"),
            )
        )
    return findings
