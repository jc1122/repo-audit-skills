"""Release-hygiene checks for repo-hygiene-audit."""

from __future__ import annotations

from pathlib import Path

import health_common as hc  # noqa: E402

LEAF = "repo-hygiene"


def _check_missing_ci(root: Path) -> list[hc.Finding]:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return [_ci_finding()]
    yml_files = list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml"))
    if not yml_files:
        return [_ci_finding()]
    return []


def _ci_finding() -> hc.Finding:
    return hc.Finding(
        leaf=LEAF,
        signal="RESTRUCTURE",
        severity="low",
        path=".github",
        line_start=1,
        line_end=1,
        symbol="<ci>",
        metric_name="ci_missing",
        metric_value=1.0,
        metric_threshold=0.0,
        evidence_tool="filesystem",
        evidence_raw="No .github/workflows/*.yml or .github/workflows/*.yaml found",
        confidence="high",
        suggested_action="Add a CI workflow under .github/workflows/",
    )


def _check_missing_license(root: Path) -> list[hc.Finding]:
    license_files = list(root.glob("LICENSE*"))
    if not license_files:
        return [
            hc.Finding(
                leaf=LEAF,
                signal="RESTRUCTURE",
                severity="low",
                path="LICENSE",
                line_start=1,
                line_end=1,
                symbol="<license>",
                metric_name="license_missing",
                metric_value=1.0,
                metric_threshold=0.0,
                evidence_tool="filesystem",
                evidence_raw="No LICENSE file found at repository root",
                confidence="high",
                suggested_action="Add a LICENSE file to the repository root",
            )
        ]
    return []
