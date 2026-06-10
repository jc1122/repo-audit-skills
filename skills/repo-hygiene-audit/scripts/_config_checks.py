"""Conflicting-configuration checks for repo-hygiene-audit.

Detects when a repository defines pytest or ruff settings in multiple
places simultaneously (e.g.  ``pytest.ini`` **and** ``pyproject.toml``).
Each extra source beyond the first triggers a RESTRUCTURE finding.

Deterministic ordering:
  - pytest: pytest.ini, setup.cfg, pyproject.toml
  - ruff:  ruff.toml, .ruff.toml, pyproject.toml
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import health_common as hc  # noqa: E402

LEAF = "repo-hygiene"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _check_conflicting_configs(root: Path) -> list[hc.Finding]:
    """Detect multiple pytest or ruff configuration sources."""
    ppt_data = _try_load_pyproject(root)
    findings: list[hc.Finding] = []
    findings.extend(_pytest_config_findings(root, ppt_data))
    findings.extend(_ruff_config_findings(root, ppt_data))
    return findings


# ---------------------------------------------------------------------------
# Pytest config detection
# ---------------------------------------------------------------------------


def _pytest_config_findings(root: Path, ppt_data: dict | None) -> list[hc.Finding]:
    """Emit findings when pytest is configured in more than one place.

    Priority order: pytest.ini > setup.cfg > pyproject.toml.
    The first source is accepted; every subsequent source gets a finding.
    """
    # Collect sources in deterministic priority order.
    sources: list[str] = []
    if (root / "pytest.ini").exists():
        sources.append("pytest.ini")
    if _setup_cfg_has_pytest(root):
        sources.append("setup.cfg")
    if _pyproject_has_pytest(ppt_data):
        sources.append("pyproject.toml")

    if len(sources) <= 1:
        return []
    return _emit_config_findings(sources, "pytest-config", "pytest")


def _setup_cfg_has_pytest(root: Path) -> bool:
    """Check whether setup.cfg contains a [tool:pytest] section."""
    setup_cfg = root / "setup.cfg"
    if not setup_cfg.exists():
        return False
    try:
        return "[tool:pytest]" in setup_cfg.read_text(encoding="utf-8")
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Ruff config detection
# ---------------------------------------------------------------------------


def _ruff_config_findings(root: Path, ppt_data: dict | None) -> list[hc.Finding]:
    """Emit findings when ruff is configured in more than one place.

    Priority order: ruff.toml > .ruff.toml > pyproject.toml.
    """
    sources: list[str] = []
    if (root / "ruff.toml").exists():
        sources.append("ruff.toml")
    if (root / ".ruff.toml").exists():
        sources.append(".ruff.toml")
    if _pyproject_has_ruff(ppt_data):
        sources.append("pyproject.toml")

    if len(sources) <= 1:
        return []
    return _emit_config_findings(sources, "ruff-config", "ruff")


# ---------------------------------------------------------------------------
# Shared finding constructor
# ---------------------------------------------------------------------------


def _emit_config_findings(
    sources: list[str], symbol: str, label: str
) -> list[hc.Finding]:
    """Build a RESTRUCTURE finding for every source except the first."""
    count = len(sources)
    findings: list[hc.Finding] = []
    for src in sources[1:]:
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="RESTRUCTURE",
                severity="medium",
                path=src,
                line_start=1,
                line_end=1,
                symbol=symbol,
                metric_name="conflicting_configs",
                metric_value=float(count),
                metric_threshold=1.0,
                evidence_tool="filesystem",
                evidence_raw=(
                    f"Found {count} {label} configs (limit 1): {', '.join(sources)}"
                ),
                confidence="high",
                suggested_action=(
                    f"Consolidate {label} configuration into a single file"
                ),
            )
        )
    return findings


# ---------------------------------------------------------------------------
# pyproject.toml helpers
# ---------------------------------------------------------------------------


def _try_load_pyproject(root: Path) -> dict | None:
    """Load pyproject.toml as a dict, returning None on any error."""
    pyproject = root / "pyproject.toml"
    try:
        return tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError, FileNotFoundError):
        return None


def _pyproject_has_pytest(data: dict | None) -> bool:
    """Return True when pyproject.toml declares [tool.pytest.ini_options]."""
    return (
        data is not None
        and isinstance(data.get("tool"), dict)
        and isinstance(data["tool"].get("pytest"), dict)
        and "ini_options" in data["tool"]["pytest"]
    )


def _pyproject_has_ruff(data: dict | None) -> bool:
    """Return True when pyproject.toml declares [tool.ruff]."""
    return (
        data is not None
        and isinstance(data.get("tool"), dict)
        and isinstance(data["tool"].get("ruff"), dict)
    )
