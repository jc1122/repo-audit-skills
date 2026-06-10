"""Version-mismatch checks for repo-hygiene-audit.

Collects version strings from canonical source files (pyproject.toml,
package.json, CHANGELOG, __init__.py) and emits RESTRUCTURE findings
when more than one distinct version is discovered.
"""

from __future__ import annotations

from pathlib import Path

import health_common as hc  # noqa: E402
import _version_sources  # noqa: E402

LEAF = "repo-hygiene"


def _collect_versions(root: Path) -> list[tuple[str, str | None]]:
    """Return (source_path, version) tuples in deterministic order.

    Sources are checked in this priority: pyproject.toml, package.json,
    CHANGELOG*.md, and top-level */__init__.py.
    """
    sources: list[tuple[str, str | None]] = []
    sources.extend(_version_sources._versions_from_pyproject(root))
    sources.extend(_version_sources._versions_from_package_json(root))
    sources.extend(_version_sources._versions_from_changelogs(root))
    sources.extend(_version_sources._versions_from_init_files(root))
    return sources


def _check_version_mismatch(root: Path) -> list[hc.Finding]:
    """Emit RESTRUCTURE when multiple distinct version strings coexist.

    The first collected version is treated as canonical; every subsequent
    source whose version differs from it receives a finding.
    """
    findings: list[hc.Finding] = []
    sources = _collect_versions(root)
    # Need at least two sources to detect a mismatch.
    if len(sources) < 2:
        return findings
    versions = {v for _, v in sources if v is not None}
    if len(versions) < 2:
        return findings
    canonical = sources[0][1]
    distinct_count = len(versions)
    evidence_entries = [f"{path}={ver}" for path, ver in sources]
    evidence_raw = (
        f"Found {distinct_count} distinct versions: {', '.join(evidence_entries)}"
    )
    # Emit a finding for every non-canonical source.
    for path, ver in sources[1:]:
        if ver != canonical:
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="RESTRUCTURE",
                    severity="medium",
                    path=path,
                    line_start=1,
                    line_end=1,
                    symbol="version",
                    metric_name="version_mismatch",
                    metric_value=float(distinct_count),
                    metric_threshold=1.0,
                    evidence_tool="filesystem",
                    evidence_raw=evidence_raw,
                    confidence="high",
                    suggested_action=(
                        "Align version strings across all sources: "
                        f"{', '.join(evidence_entries)}"
                    ),
                )
            )
    return findings
