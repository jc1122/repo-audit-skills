"""Report rendering for repo-hygiene-audit."""

from __future__ import annotations

import health_common as hc  # noqa: E402


def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# repo-hygiene-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    by_signal: dict[str, list[hc.Finding]] = {}
    for f in findings:
        by_signal.setdefault(f.signal, []).append(f)
    for signal in sorted(by_signal):
        lines.append(f"## {signal} ({len(by_signal[signal])})")
        for f in by_signal[signal]:
            lines.append(
                f"- `{f.path}:{f.line_start}` {f.symbol} \u2014 "
                f"{f.metric_name}={f.metric_value:g} [{f.severity}]"
            )
        lines.append("")
    return "\n".join(lines) + "\n"
