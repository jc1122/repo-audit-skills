"""Counted finding suppressions for security-audit policies.

The leaf keeps emitted findings in the shared schema unchanged. Policy matches
are removed from that finding list only when explicitly configured, and every
removed row is written to ``security_summary.json`` so suppressions stay
auditable.

Contract:
- default configuration suppresses nothing;
- policy records include class, rule, path, line, symbol, and metric;
- summary output is sorted for byte-identical repeat runs;
- markdown rendering consumes only the counted records, not hidden state.
"""

from __future__ import annotations

import json
from fnmatch import fnmatch
from pathlib import Path

import health_common as hc


def _bandit_rule(finding: hc.Finding) -> str:
    """Return the Bandit rule id from a finding metric, or an empty string."""
    prefix = "bandit_"
    if not finding.metric_name.startswith(prefix):
        return ""
    return finding.metric_name[len(prefix) :]


def _suppressed_record(finding: hc.Finding, rule: str) -> dict:
    """Build the counted suppression record stored in summary JSON."""
    return {
        "class": "trusted_subprocess",
        "rule": rule,
        "path": finding.path,
        "line_start": finding.line_start,
        "symbol": finding.symbol,
        "metric": finding.metric_name,
    }


def apply_suppressions(
    findings: list[hc.Finding], thresholds: dict
) -> tuple[list[hc.Finding], list[dict]]:
    """Apply the trusted-subprocess policy and return kept plus counted rows."""
    policy = thresholds.get("trusted_subprocess") or {}
    if not policy.get("enabled"):
        return findings, []
    rules = set(policy.get("rules") or [])
    path_globs = list(policy.get("path_globs") or [])
    kept: list[hc.Finding] = []
    suppressed: list[dict] = []
    for finding in findings:
        rule = _bandit_rule(finding)
        matched = rule in rules and any(
            fnmatch(finding.path, glob) for glob in path_globs
        )
        if matched:
            suppressed.append(_suppressed_record(finding, rule))
        else:
            kept.append(finding)
    return kept, suppressed


def suppression_counts(suppressed_findings: list[dict]) -> dict[str, int]:
    """Count suppressed rows by policy class."""
    counts: dict[str, int] = {}
    for item in suppressed_findings:
        key = item["class"]
        counts[key] = counts.get(key, 0) + 1
    return counts


def _sort_key(item: dict) -> tuple:
    """Stable ordering for byte-identical summary output."""
    return (
        item["class"],
        item["path"],
        item["line_start"],
        item["rule"],
        item["symbol"],
    )


def write_summary(
    out_dir: str | Path, findings_count: int, suppressed_findings: list[dict]
) -> dict:
    """Write ``security_summary.json`` and return its payload."""
    summary = {
        "findings": findings_count,
        "suppressed_findings": sorted(suppressed_findings, key=_sort_key),
    }
    summary["suppression_counts"] = suppression_counts(
        summary["suppressed_findings"]
    )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "security_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary
