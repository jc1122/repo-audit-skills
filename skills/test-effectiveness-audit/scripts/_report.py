"""Report rendering and threshold loading for test-effectiveness-audit.

These are the output-formatting functions consumed by the CLI entry
point.  They are separated from the pipeline to keep the mutation
logic cleanly decoupled from presentation concerns.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402
from _emission import ToolError  # noqa: E402


# Default thresholds applied when no --config file is provided.
# These values are tuned for mutmut==3.6.0 on typical Python projects.
DEFAULT_THRESHOLDS = {
    "min_kill_rate": 0.8,
    "mutmut_timeout_seconds": 600,
    "estimated_mutants_per_def": 8,
}


def load_thresholds(config_path: str | None) -> dict:
    """Load thresholds, merging JSON config over DEFAULT_THRESHOLDS.

    When *config_path* is None, returns a copy of DEFAULT_THRESHOLDS.
    JSON decode errors and missing files are surfaced as ToolError.
    """
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        try:
            thresholds.update(
                json.loads(Path(config_path).read_text(encoding="utf-8")),
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"invalid --config: {exc}") from exc
    return thresholds


def render_report(findings: list[hc.Finding]) -> str:
    """Render findings as a Markdown report grouped by severity tier.

    Outputs a header with the total count and two sections:
      - HIGH severity (kill rate < 0.5)
      - MEDIUM severity (kill rate >= 0.5, < threshold)

    An empty findings list produces a single-line 'No findings' report.
    """
    if not findings:
        return "# test-effectiveness-audit report\n\nNo findings.\n"

    lines = [
        "# test-effectiveness-audit report",
        "",
        f"## Mutation testing ({len(findings)} modules below threshold)",
        "",
    ]

    for title, sev in [
        ("HIGH severity (kill rate < 0.5)", "high"),
        ("MEDIUM severity", "medium"),
    ]:
        group = [f for f in findings if f.severity == sev]
        if not group:
            continue
        lines.append(f"### {title} ({len(group)})")
        lines.append("")
        for f in group:
            lines.append(
                f"- `{f.path}` — kill_rate={f.metric_value:.3f} "
                f"(threshold={f.metric_threshold}) [{f.confidence}]",
            )
        lines.append("")

    return "\n".join(lines) + "\n"
