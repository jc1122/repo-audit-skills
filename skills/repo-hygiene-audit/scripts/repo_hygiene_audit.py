#!/usr/bin/env python3
"""Repo hygiene audit: tracked-tree hygiene + release hygiene checks."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "repo-hygiene"

DEFAULT_THRESHOLDS = {"max_tracked_file_bytes": 1048576}

_CACHE_DIRS = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})
_VERSION_RE = re.compile(r"^##\s+(\d+\.\d+\.\d+)\b")


class ToolError(RuntimeError):
    pass


def _git(root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolError("git is not installed") from exc
    if proc.returncode != 0:
        raise ToolError(f"git {args[0]} failed: {proc.stderr.strip()}")
    return proc.stdout


def _is_git_repo(root: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--git-dir"],
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError:
        raise ToolError("git is not installed")
    return proc.returncode == 0


def _tracked_paths(root: Path) -> set[str]:
    out = _git(root, "ls-files", "-z")
    return {p for p in out.split("\0") if p}


def _tracked_ignored_paths(root: Path) -> set[str]:
    out = _git(root, "ls-files", "-ci", "--exclude-standard", "-z")
    return {p for p in out.split("\0") if p}


def _normalize_prefixes(prefixes: list[str]) -> list[str]:
    return [p.removeprefix("./") for p in prefixes]


def _in_scope(path: str, prefixes: list[str]) -> bool:
    if not prefixes:
        return True
    return any(path.startswith(p) for p in prefixes)


def _check_tracked_artifacts(
    root: Path, tracked: set[str]
) -> list[hc.Finding]:
    findings: list[hc.Finding] = []
    for rel in sorted(tracked):
        parts = tuple(Path(rel).parts)
        name = parts[-1] if parts else ""
        is_artifact = False
        reason = ""
        cache_hit = any(p in _CACHE_DIRS for p in parts)
        if cache_hit:
            is_artifact = True
            cache_part = next(p for p in parts if p in _CACHE_DIRS)
            reason = f"path contains {cache_part}"
        elif (
            name.endswith(".pyc")
            or name.endswith(".pyo")
            or name == ".coverage"
            or name.startswith(".coverage.")
            or name == ".DS_Store"
            or name.endswith(".orig")
            or name.endswith(".rej")
        ):
            is_artifact = True
            reason = f"filename matches artifact pattern: {name}"
        if is_artifact:
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="DELETE",
                    severity="medium",
                    path=rel,
                    line_start=1,
                    line_end=1,
                    symbol=rel,
                    metric_name="tracked_artifact",
                    metric_value=1.0,
                    metric_threshold=0.0,
                    evidence_tool="git",
                    evidence_raw=f"Tracked build artifact: {reason}",
                    confidence="high",
                    suggested_action="Remove from git tracking and add to .gitignore if appropriate",
                )
            )
    return findings


def _check_tracked_ignored(
    root: Path, tracked_ignored: set[str]
) -> list[hc.Finding]:
    findings: list[hc.Finding] = []
    for rel in sorted(tracked_ignored):
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="DELETE",
                severity="medium",
                path=rel,
                line_start=1,
                line_end=1,
                symbol=rel,
                metric_name="tracked_ignored",
                metric_value=1.0,
                metric_threshold=0.0,
                evidence_tool="git",
                evidence_raw="Tracked by git but excluded by .gitignore patterns",
                confidence="high",
                suggested_action=f"Remove from git tracking: git rm --cached {rel}",
            )
        )
    return findings


def _check_oversized_tracked(
    root: Path, tracked: set[str], max_bytes: int
) -> list[hc.Finding]:
    findings: list[hc.Finding] = []
    for rel in sorted(tracked):
        fpath = root / rel
        try:
            st_size = fpath.stat().st_size
        except OSError:
            continue
        if st_size > max_bytes:
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="RESTRUCTURE",
                    severity="medium",
                    path=rel,
                    line_start=1,
                    line_end=1,
                    symbol=rel,
                    metric_name="tracked_file_bytes",
                    metric_value=float(st_size),
                    metric_threshold=float(max_bytes),
                    evidence_tool="git",
                    evidence_raw=f"File size {st_size} bytes exceeds threshold {max_bytes} bytes",
                    confidence="high",
                    suggested_action="Move large file out of the repository or use Git LFS",
                )
            )
    return findings


def _check_broken_symlinks(
    root: Path, tracked: set[str]
) -> list[hc.Finding]:
    findings: list[hc.Finding] = []
    for rel in sorted(tracked):
        fpath = root / rel
        try:
            if fpath.is_symlink() and not fpath.exists():
                target = os.readlink(str(fpath))
                findings.append(
                    hc.Finding(
                        leaf=LEAF,
                        signal="DELETE",
                        severity="low",
                        path=rel,
                        line_start=1,
                        line_end=1,
                        symbol=rel,
                        metric_name="broken_symlink",
                        metric_value=1.0,
                        metric_threshold=0.0,
                        evidence_tool="git",
                        evidence_raw=f"Broken symlink: {rel} -> {target}",
                        confidence="high",
                        suggested_action="Remove the broken symlink or fix its target",
                    )
                )
        except OSError:
            continue
    return findings


def _check_conflicting_configs(root: Path) -> list[hc.Finding]:
    findings: list[hc.Finding] = []

    # pytest: deterministic plan order = pytest.ini, setup.cfg, pyproject.toml
    pytest_sources: list[str] = []
    if (root / "pytest.ini").exists():
        pytest_sources.append("pytest.ini")
    setup_cfg = root / "setup.cfg"
    if setup_cfg.exists():
        try:
            text = setup_cfg.read_text(encoding="utf-8")
            if "[tool:pytest]" in text:
                pytest_sources.append("setup.cfg")
        except OSError:
            pass
    try:
        ppt_data = tomllib.loads(
            (root / "pyproject.toml").read_text(encoding="utf-8")
        )
    except (tomllib.TOMLDecodeError, OSError, FileNotFoundError):
        ppt_data = None
    if (
        ppt_data is not None
        and isinstance(ppt_data.get("tool"), dict)
        and isinstance(ppt_data["tool"].get("pytest"), dict)
        and "ini_options" in ppt_data["tool"]["pytest"]
    ):
        pytest_sources.append("pyproject.toml")

    if len(pytest_sources) > 1:
        count = len(pytest_sources)
        for src in pytest_sources[1:]:
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="RESTRUCTURE",
                    severity="medium",
                    path=src,
                    line_start=1,
                    line_end=1,
                    symbol="pytest-config",
                    metric_name="conflicting_configs",
                    metric_value=float(count),
                    metric_threshold=1.0,
                    evidence_tool="filesystem",
                    evidence_raw=f"Found {count} pytest configs (limit 1): "
                    f"{', '.join(pytest_sources)}",
                    confidence="high",
                    suggested_action="Consolidate pytest configuration into a single file",
                )
            )

    # ruff: deterministic plan order = ruff.toml, .ruff.toml, pyproject.toml
    ruff_sources: list[str] = []
    if (root / "ruff.toml").exists():
        ruff_sources.append("ruff.toml")
    if (root / ".ruff.toml").exists():
        ruff_sources.append(".ruff.toml")
    if (
        ppt_data is not None
        and isinstance(ppt_data.get("tool"), dict)
        and isinstance(ppt_data["tool"].get("ruff"), dict)
    ):
        ruff_sources.append("pyproject.toml")

    if len(ruff_sources) > 1:
        count = len(ruff_sources)
        for src in ruff_sources[1:]:
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="RESTRUCTURE",
                    severity="medium",
                    path=src,
                    line_start=1,
                    line_end=1,
                    symbol="ruff-config",
                    metric_name="conflicting_configs",
                    metric_value=float(count),
                    metric_threshold=1.0,
                    evidence_tool="filesystem",
                    evidence_raw=f"Found {count} ruff configs (limit 1): "
                    f"{', '.join(ruff_sources)}",
                    confidence="high",
                    suggested_action="Consolidate ruff configuration into a single file",
                )
            )

    return findings


def _collect_versions(root: Path) -> list[tuple[str, str | None]]:
    """Return list of (source_path, version_string) in deterministic order."""
    sources: list[tuple[str, str | None]] = []

    # pyproject.toml [project].version
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = data.get("project")
            if isinstance(project, dict) and "version" in project:
                sources.append(("pyproject.toml", str(project["version"])))
        except (tomllib.TOMLDecodeError, OSError):
            pass

    # package.json "version"
    pjson = root / "package.json"
    if pjson.exists():
        try:
            data = json.loads(pjson.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "version" in data:
                sources.append(("package.json", str(data["version"])))
        except (json.JSONDecodeError, OSError):
            pass

    # CHANGELOG*.md first ## X.Y.Z heading
    for changelog in sorted(root.glob("CHANGELOG*.md")):
        try:
            for line in changelog.read_text(encoding="utf-8").splitlines():
                m = _VERSION_RE.match(line)
                if m:
                    sources.append((changelog.name, m.group(1)))
                    break
        except OSError:
            pass

    # top-level */__init__.py __version__ = "X.Y.Z"
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
                    (str(init.relative_to(root).as_posix()), node.value.value)
                )
                break

    return sources


def _check_version_mismatch(root: Path) -> list[hc.Finding]:
    findings: list[hc.Finding] = []
    sources = _collect_versions(root)
    if len(sources) < 2:
        return findings
    versions = {v for _, v in sources if v is not None}
    if len(versions) < 2:
        return findings
    canonical = sources[0][1]
    distinct_count = len(versions)
    evidence_entries = [f"{path}={ver}" for path, ver in sources]
    evidence_raw = (
        f"Found {distinct_count} distinct versions: "
        f"{', '.join(evidence_entries)}"
    )
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
                    suggested_action=f"Align version strings across all sources: "
                    f"{', '.join(evidence_entries)}",
                )
            )
    return findings


def _check_missing_ci(root: Path) -> list[hc.Finding]:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return [
            hc.Finding(
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
        ]
    yml_files = list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml"))
    if not yml_files:
        return [
            hc.Finding(
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
        ]
    return []


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


def analyze_tree(
    root: Path,
    source_prefixes: list[str],
    thresholds: dict,
) -> tuple[list[hc.Finding], bool]:
    max_bytes = thresholds.get("max_tracked_file_bytes", 1048576)
    prefixes = _normalize_prefixes(source_prefixes)
    findings: list[hc.Finding] = []
    git_repo = _is_git_repo(root)

    if git_repo:
        try:
            tracked = _tracked_paths(root)
            tracked_ignored = _tracked_ignored_paths(root)
        except Exception as exc:
            raise ToolError(str(exc)) from exc
        findings.extend(_check_tracked_artifacts(root, tracked))
        findings.extend(_check_tracked_ignored(root, tracked_ignored))
        findings.extend(_check_oversized_tracked(root, tracked, max_bytes))
        findings.extend(_check_broken_symlinks(root, tracked))

    findings.extend(_check_conflicting_configs(root))
    findings.extend(_check_version_mismatch(root))
    findings.extend(_check_missing_ci(root))
    findings.extend(_check_missing_license(root))

    if prefixes:
        findings = [f for f in findings if _in_scope(f.path, prefixes)]

    return findings, git_repo


def render_report(findings: list[hc.Finding]) -> str:
    lines = [f"# repo-hygiene-audit report", ""]
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


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        try:
            thresholds.update(
                json.loads(Path(config_path).read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"invalid --config: {exc}") from exc
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Repo hygiene audit (advisory)."
    )
    parser.add_argument("--root")
    parser.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
        help="Path prefix(es) relative to --root to include. Repeatable.",
    )
    parser.add_argument("--out-dir")
    parser.add_argument("--config", help="JSON file overriding thresholds.")
    parser.add_argument("--format", choices=["json", "md"], default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir:
        print(
            json.dumps(
                {"status": "error", "message": "--root and --out-dir are required"}
            )
        )
        return hc.EXIT_ERROR

    root = Path(args.root).resolve()
    try:
        thresholds = load_thresholds(args.config)
        findings, git_repo = analyze_tree(
            root, args.source_prefixes, thresholds
        )
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR

    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, f"{LEAF}_report.md").write_text(
        render_report(findings), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "findings": len(data),
                "leaf": LEAF,
                "git": git_repo,
            }
        )
    )
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
