#!/usr/bin/env python3
"""duplication-audit leaf: jscpd clone detection → EXTRACT/MERGE findings."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "duplication"

DEFAULT_THRESHOLDS = {
    "min_tokens": 50,
    "min_lines": 5,
}


class ToolError(RuntimeError):
    pass


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    return [p for p in files if any(p.relative_to(root).as_posix().startswith(pre) for pre in source_prefixes)]


def _rel(name: str, root: Path) -> str:
    p = Path(name)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return p.as_posix()
    return p.as_posix()


def _run_jscpd(root: Path, files: list[Path], thresholds: dict, out_dir: Path) -> dict:
    rel_files = [p.relative_to(root).as_posix() for p in files]
    cmd = [
        "npx", "--yes", "jscpd", "--silent",
        "--reporters", "json", "--output", str(out_dir),
        "--min-tokens", str(thresholds["min_tokens"]),
        "--min-lines", str(thresholds["min_lines"]),
        *rel_files,
    ]
    try:
        proc = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise ToolError("npx/node is not installed (needed to run jscpd)") from exc
    report_path = out_dir / "jscpd-report.json"
    if not report_path.exists():
        raise ToolError(f"jscpd produced no report: {proc.stderr.strip() or proc.stdout.strip()}")
    return json.loads(report_path.read_text(encoding="utf-8"))


def _findings_from_report(report: dict, root: Path, thresholds: dict) -> list[hc.Finding]:
    findings: list[hc.Finding] = []
    min_tokens = thresholds["min_tokens"]
    for dup in report.get("duplicates", []):
        ff, sf = dup["firstFile"], dup["secondFile"]
        p1, p2 = _rel(ff["name"], root), _rel(sf["name"], root)
        tokens = int(dup.get("tokens", 0))
        signal = "MERGE" if p1 == p2 else "EXTRACT"
        severity = "high" if tokens > 3 * min_tokens else "medium"
        symbol = f"{p2}:{sf['start']}-{sf['end']}"
        findings.append(hc.Finding(
            leaf=LEAF, signal=signal, severity=severity, path=p1,
            line_start=int(ff["start"]), line_end=int(ff["end"]), symbol=symbol,
            metric_name="duplicate_tokens", metric_value=float(tokens),
            metric_threshold=float(min_tokens),
            evidence_tool="jscpd",
            evidence_raw=f"{p1}:{ff['start']}-{ff['end']} == {p2}:{sf['start']}-{sf['end']} ({tokens} tokens)",
            confidence="high",
            suggested_action=(
                f"Extract shared code between {p1} and {p2}" if signal == "EXTRACT"
                else f"Merge duplicated block within {p1}"
            ),
        ))
    return findings


def analyze_tree(root, source_prefixes, thresholds) -> list[hc.Finding]:
    root = Path(root)
    files = _iter_python_files(root, list(source_prefixes or []))
    if not files:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        report = _run_jscpd(root, files, thresholds, Path(tmp))
    return hc.sort_findings(_findings_from_report(report, root, thresholds))
