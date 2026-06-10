"""pip-audit advisory-report ingestion for security-audit.

Translates a pip-audit-shaped JSON advisory report into SECURITY findings
focusing on dependency vulnerabilities.  Each package that lists at least
one vulnerability produces a single Finding.
"""

from __future__ import annotations

import json
from pathlib import Path

import health_common as hc  # noqa: E402

from _bandit import ToolError

# CVE scoring uses a four-tier base severity (CVSS v3 style) while the
# shared schema uses three (low/medium/high).  We collapse "critical"
# into "high" so the data fits the schema; the numeric rank ordering
# (1=low, 2=medium, 3=high, 4=critical) is preserved during the
# worst-severity computation.
_C8_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
_RANK_SEVERITY = {1: "low", 2: "medium", 3: "high", 4: "high"}


def _load(path: str) -> dict:
    """Read and parse the advisory JSON, or raise ToolError."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolError(f"unreadable advisory report {path}: {exc}") from exc


def _severity(vulns: list[dict]) -> str:
    """Worst C-8 severity across *vulns* (null ranks as medium).

    For each vulnerability we look up its severity string in ``_C8_RANK``,
    defaulting to rank 2 (medium) when the field is absent or unrecognised.
    The highest rank across all vulnerabilities determines the Finding's
    overall severity after mapping back through ``_RANK_SEVERITY``.
    """
    worst = max(
        (_C8_RANK.get(str(v.get("severity") or ""), 2) for v in vulns),
        default=2,
    )
    return _RANK_SEVERITY[worst]


def scan(advisory_report: str, root: str) -> list[hc.Finding]:
    """One SECURITY finding per advisory package that lists vulnerabilities.

    Field mapping:

    - ``path``: ``"pyproject.toml"`` when a pyproject.toml exists at
      *root*, otherwise ``"<advisory>"`` (symbolic path for projects
      that declare dependencies differently).
    - ``metric_value``: the count of vulnerabilities attached to the
      package, so a package with 3 vulns gets ``metric_value=3.0``.
    - ``evidence_raw``: a comma-joined string of ``"<id> (fix:
      <version>)"`` entries, one per vulnerability.
    - ``confidence``: always ``"high"`` because advisory data is
      sourced from a curated vulnerability database.
    - ``severity``: the worst vulnerability severity in the package,
      computed via ``_severity()`` above.
    """
    report = _load(advisory_report)
    where = (
        "pyproject.toml" if (Path(root) / "pyproject.toml").exists() else "<advisory>"
    )
    findings: list[hc.Finding] = []
    for pkg in report.get("packages", []):
        vulns = pkg.get("vulns") or []
        if not vulns:
            continue
        name = pkg.get("name", "")
        raw = ", ".join(
            f"{v.get('id')} (fix: {','.join(v.get('fix_versions') or []) or 'none'})"
            for v in vulns
        )
        findings.append(
            hc.Finding(
                leaf="security",
                signal="SECURITY",
                severity=_severity(vulns),
                path=where,
                line_start=1,
                line_end=1,
                symbol=name,
                metric_name="dependency_vulnerabilities",
                metric_value=float(len(vulns)),
                metric_threshold=0.0,
                evidence_tool="advisory-report",
                evidence_raw=raw,
                confidence="high",
                suggested_action=(
                    f"Upgrade {name} to a patched release "
                    f"({len(vulns)} vulnerabilities reported)"
                ),
            )
        )
    return findings
