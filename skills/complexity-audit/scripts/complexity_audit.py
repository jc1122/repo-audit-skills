#!/usr/bin/env python3
"""complexity-audit leaf: lizard (per-function) + radon mi (per-module) → findings."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "complexity"
TOOL_TIMEOUT = 120

DEFAULT_THRESHOLDS = {
    "cc_medium": 10,
    "cc_high": 20,
    "nloc_medium": 50,
    "max_params": 5,
    "mi_low": 65,
    "mi_medium": 50,
    "mi_entrypoint_low": 20,
}

_MAIN_GUARD = re.compile(r"^if __name__ ==", re.M)


LAST_ANALYSIS_METADATA = {
    "entrypoint_mi_relaxed": 0,
}


class ToolError(RuntimeError):
    pass


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    kept = []
    for p in files:
        rel = p.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix in source_prefixes):
            kept.append(p)
    return kept


def _lizard_findings(
    root: Path, files: list[Path], thresholds: dict
) -> list[hc.Finding]:
    try:
        import lizard
    except ImportError as exc:  # pragma: no cover - exercised via missing-tool test
        raise ToolError("lizard is not installed") from exc
    findings: list[hc.Finding] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        analysis = lizard.analyze_file(str(path))
        for fn in analysis.function_list:
            cc = fn.cyclomatic_complexity
            if cc > thresholds["cc_medium"]:
                sev = "high" if cc > thresholds["cc_high"] else "medium"
                findings.append(
                    hc.Finding(
                        leaf=LEAF,
                        signal="DECOMPOSE",
                        severity=sev,
                        path=rel,
                        line_start=fn.start_line,
                        line_end=fn.end_line,
                        symbol=fn.name,
                        metric_name="cyclomatic_complexity",
                        metric_value=float(cc),
                        metric_threshold=float(thresholds["cc_medium"]),
                        evidence_tool="lizard",
                        evidence_raw=f"{fn.long_name} CCN={cc}",
                        confidence="high",
                        suggested_action=(
                            f"Split {fn.name}() — complexity {cc} exceeds "
                            f"{thresholds['cc_medium']}"
                        ),
                    )
                )
            if fn.nloc > thresholds["nloc_medium"]:
                findings.append(
                    hc.Finding(
                        leaf=LEAF,
                        signal="DECOMPOSE",
                        severity="medium",
                        path=rel,
                        line_start=fn.start_line,
                        line_end=fn.end_line,
                        symbol=fn.name,
                        metric_name="function_nloc",
                        metric_value=float(fn.nloc),
                        metric_threshold=float(thresholds["nloc_medium"]),
                        evidence_tool="lizard",
                        evidence_raw=f"{fn.long_name} NLOC={fn.nloc}",
                        confidence="high",
                        suggested_action=(
                            f"Shorten {fn.name}() — {fn.nloc} lines exceeds "
                            f"{thresholds['nloc_medium']}"
                        ),
                    )
                )
            if fn.parameter_count > thresholds["max_params"]:
                findings.append(
                    hc.Finding(
                        leaf=LEAF,
                        signal="SIMPLIFY",
                        severity="low",
                        path=rel,
                        line_start=fn.start_line,
                        line_end=fn.end_line,
                        symbol=fn.name,
                        metric_name="parameter_count",
                        metric_value=float(fn.parameter_count),
                        metric_threshold=float(thresholds["max_params"]),
                        evidence_tool="lizard",
                        evidence_raw=f"{fn.long_name} params={fn.parameter_count}",
                        confidence="high",
                        suggested_action=(
                            f"Reduce parameters of {fn.name}() — "
                            f"{fn.parameter_count} exceeds {thresholds['max_params']}"
                        ),
                    )
                )
    return findings


def _is_entrypoint(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(_MAIN_GUARD.search(text))


def _radon_mi_data(files: list[Path]) -> dict:
    """Run radon MI and return its JSON payload."""
    cmd = ["radon", "mi", "-j", *[str(p) for p in files]]
    try:
        proc = subprocess.run(
            cmd, text=True, capture_output=True, check=False, timeout=TOOL_TIMEOUT
        )
    except FileNotFoundError as exc:
        raise ToolError("radon is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"radon timed out after {TOOL_TIMEOUT}s") from exc
    if proc.returncode != 0:
        raise ToolError(
            f"radon mi failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return json.loads(proc.stdout or "{}")


def _entrypoint_mi_relaxed(path: Path, mi: float, thresholds: dict) -> bool:
    """Return True when entrypoint module MI is above the configured floor."""
    relaxed_limit = thresholds.get("mi_entrypoint_low")
    return (
        relaxed_limit is not None
        and mi >= float(relaxed_limit)
        and _is_entrypoint(path)
    )


def _module_mi_finding(
    root: Path, path: Path, mi: float, rank: str, thresholds: dict
) -> hc.Finding:
    """Build a maintainability_index finding for one module."""
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    sev = "medium" if mi < thresholds["mi_medium"] else "low"
    return hc.Finding(
        leaf=LEAF,
        signal="SIMPLIFY",
        severity=sev,
        path=rel,
        line_start=1,
        line_end=1,
        symbol="<module>",
        metric_name="maintainability_index",
        metric_value=mi,
        metric_threshold=float(thresholds["mi_low"]),
        evidence_tool="radon",
        evidence_raw=f"MI={mi:.1f} rank={rank}",
        confidence="high",
        suggested_action=(
            f"Improve maintainability of {rel} — MI {mi:.1f} below "
            f"{thresholds['mi_low']}"
        ),
    )


def _radon_mi_findings(
    root: Path, files: list[Path], thresholds: dict
) -> list[hc.Finding]:
    if not files:
        return []
    data = _radon_mi_data(files)
    findings: list[hc.Finding] = []
    for fname, info in data.items():
        if not isinstance(info, dict) or "mi" not in info:
            continue
        path = Path(fname)
        mi = float(info["mi"])
        if mi >= thresholds["mi_low"]:
            continue
        if _entrypoint_mi_relaxed(path, mi, thresholds):
            LAST_ANALYSIS_METADATA["entrypoint_mi_relaxed"] += 1
            continue
        findings.append(
            _module_mi_finding(root, path, mi, info.get("rank", "?"), thresholds)
        )
    return findings


def analyze_tree(root, source_prefixes, thresholds) -> list[hc.Finding]:
    global LAST_ANALYSIS_METADATA
    root = Path(root)
    LAST_ANALYSIS_METADATA = {"entrypoint_mi_relaxed": 0}
    files = _iter_python_files(root, list(source_prefixes or []))
    findings = _lizard_findings(root, files, thresholds)
    findings += _radon_mi_findings(root, files, thresholds)
    return hc.sort_findings(findings)


def render_report(findings: list[hc.Finding], metadata: dict | None = None) -> str:
    lines = ["# complexity-audit report", ""]
    if metadata is not None:
        lines.extend(
            [
                "## Precision counters",
                f"- entrypoint_mi_relaxed: {metadata.get('entrypoint_mi_relaxed', 0)}",
                "",
            ]
        )
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    for signal in sorted({finding.signal for finding in findings}):
        group = [finding for finding in findings if finding.signal == signal]
        lines.append(f"## {signal} ({len(group)})")
        for f in group:
            lines.append(
                f"- `{f.path}:{f.line_start}` {f.symbol} — {f.metric_name}="
                f"{f.metric_value:g} (>{f.metric_threshold:g}) [{f.severity}]"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        thresholds.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic complexity/maintainability audit (advisory)."
    )
    parser.add_argument("--root", required=False, help="Target repository root.")
    parser.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
        help="Path prefix(es) (relative to --root) to include. Repeatable.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Unused placeholder for prefix excludes.",
    )
    parser.add_argument(
        "--out-dir", required=False, help="Directory for findings + report."
    )
    parser.add_argument("--config", help="JSON file overriding thresholds.")
    parser.add_argument(
        "--format",
        choices=["json", "md"],
        default="json",
        help="Stdout summary format.",
    )
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
        thresholds = load_thresholds(args.config)
        findings = analyze_tree(args.root, args.source_prefixes, thresholds)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    entrypoint_mi_relaxed = LAST_ANALYSIS_METADATA["entrypoint_mi_relaxed"]
    data = hc.write_findings(findings, args.out_dir, LEAF)
    report = render_report(
        findings, {"entrypoint_mi_relaxed": entrypoint_mi_relaxed}
    )
    Path(args.out_dir, "complexity_report.md").write_text(
        report, encoding="utf-8"
    )
    status = {"status": "ok", "findings": len(data), "leaf": LEAF}
    status["entrypoint_mi_relaxed"] = entrypoint_mi_relaxed
    print(json.dumps(status))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
