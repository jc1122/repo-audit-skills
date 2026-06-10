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
TOOL_TIMEOUT = 120

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


def _rel(name: str, root: Path) -> str:
    p = Path(name)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return p.as_posix()
    return p.as_posix()


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    return [
        p
        for p in files
        if any(
            p.relative_to(root).as_posix().startswith(pre) for pre in source_prefixes
        )
    ]


def _ruff_lint(root: Path, rel_files: list[str], config: dict) -> list[hc.Finding]:
    cmd = [
        "ruff",
        "check",
        "--no-cache",
        "--output-format",
        "json",
        "--select",
        config["ruff_select"],
        "--ignore",
        config["ruff_ignore"],
        *rel_files,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
            timeout=TOOL_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise ToolError("ruff is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"ruff timed out after {TOOL_TIMEOUT}s") from exc
    try:
        items = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise ToolError(
            f"ruff produced unparseable output: {proc.stderr.strip()}"
        ) from exc
    owned = set(config["ruff_ignore"].split(","))
    findings: list[hc.Finding] = []
    for item in items:
        code = item.get("code") or "RUFF"
        if code in owned:
            continue
        loc = item.get("location") or {}
        row, col = int(loc.get("row", 1)), int(loc.get("column", 1))
        end_row = int((item.get("end_location") or {}).get("row", row))
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="LINT",
                severity="medium",
                path=_rel(item.get("filename", ""), root),
                line_start=row,
                line_end=end_row,
                symbol=f"{code}@{row}:{col}",
                metric_name=code,
                metric_value=0.0,
                metric_threshold=0.0,
                evidence_tool="ruff",
                evidence_raw=item.get("message", ""),
                confidence="high",
                suggested_action=item.get("message", f"Fix {code}"),
            )
        )
    return findings


def _ruff_format(root: Path, rel_files: list[str]) -> list[hc.Finding]:
    cmd = ["ruff", "format", "--check", *rel_files]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
            timeout=TOOL_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise ToolError("ruff is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"ruff timed out after {TOOL_TIMEOUT}s") from exc
    findings: list[hc.Finding] = []
    for line in (proc.stdout + proc.stderr).splitlines():
        line = line.strip()
        if not line.startswith("Would reformat:"):
            continue
        path = line.split("Would reformat:", 1)[1].strip()
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="FORMAT",
                severity="low",
                path=_rel(path, root),
                line_start=1,
                line_end=1,
                symbol=path,
                metric_name="format_drift",
                metric_value=0.0,
                metric_threshold=0.0,
                evidence_tool="ruff format",
                evidence_raw=line,
                confidence="high",
                suggested_action=f"Run the formatter on {path}",
            )
        )
    return findings


def _type_findings(root: Path, rel_files: list[str], config: dict) -> list[hc.Finding]:
    checker = config.get("type_checker", "mypy")
    with tempfile.TemporaryDirectory() as cache:
        if checker == "ty":
            cmd = ["ty", "check", *rel_files]
        else:
            cmd = [
                "mypy",
                "--no-error-summary",
                "--no-color-output",
                "--ignore-missing-imports",
                "--no-incremental",
                "--cache-dir",
                cache,
                *rel_files,
            ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(root),
                text=True,
                capture_output=True,
                check=False,
                timeout=TOOL_TIMEOUT,
            )
        except FileNotFoundError as exc:
            raise ToolError(f"{checker} is not installed") from exc
        except subprocess.TimeoutExpired as exc:
            raise ToolError(f"{checker} timed out after {TOOL_TIMEOUT}s") from exc
    findings: list[hc.Finding] = []
    for line in (proc.stdout + proc.stderr).splitlines():
        m = _TYPE_RE.match(line.strip())
        if not m:
            continue
        row = int(m.group("line"))
        code = m.group("code") or "type-error"
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="TYPE",
                severity="high",
                path=_rel(m.group("path"), root),
                line_start=row,
                line_end=row,
                symbol=f"{code}@{row}",
                metric_name=code,
                metric_value=0.0,
                metric_threshold=0.0,
                evidence_tool=checker,
                evidence_raw=m.group("msg"),
                confidence="high",
                suggested_action=m.group("msg"),
            )
        )
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


def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# quality-audit report", ""]
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
                f"- `{f.path}:{f.line_start}` {f.metric_name} — {f.evidence_raw} [{f.severity}]"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def load_config(config_path: str | None) -> dict:
    config = dict(DEFAULT_CONFIG)
    if config_path:
        try:
            config.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"invalid --config: {exc}") from exc
    return config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic lint/format/type audit (advisory)."
    )
    parser.add_argument("--root")
    parser.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
        help="Path prefix(es) relative to --root to include. Repeatable.",
    )
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--out-dir")
    parser.add_argument(
        "--config",
        help="JSON file overriding config (type_checker, ruff_select, ruff_ignore).",
    )
    parser.add_argument("--format", choices=["json", "md"], default="json")
    parser.add_argument(
        "--simulate-missing-tool", action="store_true", help=argparse.SUPPRESS
    )
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
    try:
        if args.simulate_missing_tool:
            raise ToolError("simulated missing tool")
        config = load_config(args.config)
        findings = analyze_tree(args.root, args.source_prefixes, config)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, "quality_report.md").write_text(
        render_report(findings), encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
