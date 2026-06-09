#!/usr/bin/env python3
"""quality-audit leaf: ruff lint + ruff format --check + mypy/ty → LINT/FORMAT/TYPE."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "quality"

DEFAULT_CONFIG = {
    "type_checker": "mypy",
    "ruff_select": "E,W,F,B,SIM,UP",
    "ruff_ignore": "F401,F811,F841,C901",
}

_TYPE_RE = re.compile(
    r"^(?P<path>[^:]+):(?P<line>\d+):(?:(?P<col>\d+):)?\s*error:\s*(?P<msg>.*?)(?:\s*\[(?P<code>[\w-]+)\])?$"
)


class ToolError(RuntimeError):
    pass


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    return [p for p in files if any(p.relative_to(root).as_posix().startswith(pre) for pre in source_prefixes)]


def _ruff_lint(root: Path, rel_files: list[str], config: dict) -> list[hc.Finding]:
    cmd = ["ruff", "check", "--no-cache", "--output-format", "json",
           "--select", config["ruff_select"], "--ignore", config["ruff_ignore"], *rel_files]
    try:
        proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise ToolError("ruff is not installed") from exc
    try:
        items = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise ToolError(f"ruff produced unparseable output: {proc.stderr.strip()}") from exc
    owned = set(config["ruff_ignore"].split(","))
    findings: list[hc.Finding] = []
    for item in items:
        code = item.get("code") or "RUFF"
        if code in owned:
            continue
        loc = item.get("location") or {}
        row, col = int(loc.get("row", 1)), int(loc.get("column", 1))
        end_row = int((item.get("end_location") or {}).get("row", row))
        findings.append(hc.Finding(
            leaf=LEAF, signal="LINT", severity="medium",
            path=Path(item.get("filename", "")).as_posix(), line_start=row, line_end=end_row,
            symbol=f"{code}@{row}:{col}", metric_name=code, metric_value=0.0, metric_threshold=0.0,
            evidence_tool="ruff", evidence_raw=item.get("message", ""),
            confidence="high", suggested_action=item.get("message", f"Fix {code}"),
        ))
    return findings


def _ruff_format(root: Path, rel_files: list[str]) -> list[hc.Finding]:
    cmd = ["ruff", "format", "--check", *rel_files]
    try:
        proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise ToolError("ruff is not installed") from exc
    findings: list[hc.Finding] = []
    for line in (proc.stdout + proc.stderr).splitlines():
        line = line.strip()
        if not line.startswith("Would reformat:"):
            continue
        path = line.split("Would reformat:", 1)[1].strip()
        findings.append(hc.Finding(
            leaf=LEAF, signal="FORMAT", severity="low", path=Path(path).as_posix(),
            line_start=1, line_end=1, symbol=path, metric_name="format_drift",
            metric_value=0.0, metric_threshold=0.0, evidence_tool="ruff format",
            evidence_raw=line, confidence="high",
            suggested_action=f"Run the formatter on {path}",
        ))
    return findings


def _type_findings(root: Path, rel_files: list[str], config: dict) -> list[hc.Finding]:
    checker = config.get("type_checker", "mypy")
    with tempfile.TemporaryDirectory() as cache:
        if checker == "ty":
            cmd = ["ty", "check", *rel_files]
        else:
            cmd = ["mypy", "--no-error-summary", "--no-color-output", "--ignore-missing-imports",
                   "--no-incremental", "--cache-dir", cache, *rel_files]
        try:
            proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True, check=False)
        except FileNotFoundError as exc:
            raise ToolError(f"{checker} is not installed") from exc
    findings: list[hc.Finding] = []
    for line in (proc.stdout + proc.stderr).splitlines():
        m = _TYPE_RE.match(line.strip())
        if not m:
            continue
        row = int(m.group("line"))
        code = m.group("code") or "type-error"
        findings.append(hc.Finding(
            leaf=LEAF, signal="TYPE", severity="high", path=Path(m.group("path")).as_posix(),
            line_start=row, line_end=row, symbol=f"{code}@{row}", metric_name=code,
            metric_value=0.0, metric_threshold=0.0, evidence_tool=checker,
            evidence_raw=m.group("msg"), confidence="high",
            suggested_action=m.group("msg"),
        ))
    return findings


def analyze_tree(root, source_prefixes, config) -> list[hc.Finding]:
    root = Path(root)
    files = _iter_python_files(root, list(source_prefixes or []))
    if not files:
        return []
    rel_files = [p.relative_to(root).as_posix() for p in files]
    findings = _ruff_lint(root, rel_files, config)
    findings += _ruff_format(root, rel_files)
    findings += _type_findings(root, rel_files, config)
    return hc.sort_findings(findings)
