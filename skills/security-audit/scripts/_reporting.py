"""Markdown report rendering and threshold loading for security-audit.

Provides two helpers used by the thin CLI: ``load_thresholds`` (optional
JSON config overlay) and ``render_report`` (human-readable markdown grouping
findings by signal).
"""

from __future__ import annotations

import json
from pathlib import Path

import health_common as hc  # noqa: E402

from _bandit import ToolError

# Empty by default: every Finding is emitted regardless of severity
# or metric value.  Downstream tooling can supply a JSON file via
# --config to suppress or filter findings.
DEFAULT_THRESHOLDS: dict = {}


def load_thresholds(config_path: str | None) -> dict:
    """Return DEFAULT_THRESHOLDS overlaid with *config_path* JSON, if given."""
    thresholds = dict(DEFAULT_THRESHOLDS)
    if not config_path:
        return thresholds
    try:
        overrides = json.loads(Path(config_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolError(f"invalid --config: {exc}") from exc
    thresholds.update(overrides)
    return thresholds


def render_report(findings: list[hc.Finding]) -> str:
    """Group findings by signal into a short markdown summary.

    Output structure:

    - ``# security-audit report`` title.
    - One ``## <SIGNAL> (N)`` section per distinct signal, with
      one bullet per finding showing severity/confidence, path,
      line, symbol, metric name, and metric value.
    - ``No findings.`` placeholder when the list is empty.
    """
    out = ["# security-audit report", ""]
    if not findings:
        out.append("No findings.")
        return "\n".join(out) + "\n"
    grouped: dict[str, list[hc.Finding]] = {}
    for finding in findings:
        grouped.setdefault(finding.signal, []).append(finding)
    for signal in sorted(grouped):
        bucket = grouped[signal]
        out.append(f"## {signal} ({len(bucket)})")
        out.extend(
            f"- [{f.severity}/{f.confidence}] {f.path}:{f.line_start} "
            f"{f.symbol} ({f.metric_name} = {f.metric_value:g})"
            for f in bucket
        )
        out.append("")
    return "\n".join(out) + "\n"
