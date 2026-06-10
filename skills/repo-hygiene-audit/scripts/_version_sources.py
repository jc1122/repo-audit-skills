"""Version-string extraction helpers for repo-hygiene-audit.

Each function collects candidate ``(path, version)`` tuples from a
single source file or file pattern.  The caller
(``_version_checks._collect_versions``) concatenates them in
deterministic order and hands them off to the mismatch detector.
"""

from __future__ import annotations

import ast
import json
import re
import tomllib
from pathlib import Path

# Regex for the first ``## X.Y.Z`` heading in a CHANGELOG-style file.
_VERSION_RE = re.compile(r"^##\s+(\d+\.\d+\.\d+)\b")


def _versions_from_pyproject(root: Path) -> list[tuple[str, str | None]]:
    """Extract version from ``pyproject.toml`` ``[project].version``.

    Returns a single-element list or an empty list.
    """
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return []
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return []
    project = data.get("project")
    if isinstance(project, dict) and "version" in project:
        return [("pyproject.toml", str(project["version"]))]
    return []


def _versions_from_package_json(root: Path) -> list[tuple[str, str | None]]:
    """Extract version from ``package.json`` ``"version"`` field.

    Returns a single-element list or an empty list.
    """
    pjson = root / "package.json"
    if not pjson.exists():
        return []
    try:
        data = json.loads(pjson.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, dict) and "version" in data:
        return [("package.json", str(data["version"]))]
    return []


def _versions_from_changelogs(root: Path) -> list[tuple[str, str | None]]:
    """Extract version from first ``## X.Y.Z`` heading in ``CHANGELOG*.md``.

    Files are processed in sorted-glob order for determinism.
    """
    sources: list[tuple[str, str | None]] = []
    for changelog in sorted(root.glob("CHANGELOG*.md")):
        try:
            for line in changelog.read_text(encoding="utf-8").splitlines():
                m = _VERSION_RE.match(line)
                if m:
                    sources.append((changelog.name, m.group(1)))
                    break
        except OSError:
            pass
    return sources


def _versions_from_init_files(root: Path) -> list[tuple[str, str | None]]:
    """Extract version from ``__version__ = "X.Y.Z"`` in ``*/__init__.py``.

    Only top-level packages (one directory deep) are scanned.
    """
    sources: list[tuple[str, str | None]] = []
    for init in sorted(root.glob("*/__init__.py")):
        try:
            tree = ast.parse(init.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "__version__"
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                sources.append(
                    (
                        str(init.relative_to(root).as_posix()),
                        node.value.value,
                    )
                )
                break
    return sources
