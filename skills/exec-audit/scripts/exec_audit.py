#!/usr/bin/env python3
"""exec-audit leaf: duplicate-execution detection, slow-test detection, benchmark-gap detection.

Repo-agnostic, stdlib-only. Never mutates the audited repository.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Health-common fallback (vendored copy not in this packet)
# ---------------------------------------------------------------------------
_SHARED = Path(__file__).resolve().parents[3] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
import health_common as hc  # noqa: E402

LEAF = "exec"

DEFAULT_THRESHOLDS: dict[str, object] = {
    "slow_test_threshold_s": 1.0,
    "slow_test_cap_s": 300.0,
    "max_runner_occurrences": 1,
}

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ToolError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# NPM script expansion
# ---------------------------------------------------------------------------

_NPM_RUN_RE = re.compile(r"\bnpm\s+run\s+(\S+)")


def _load_package_json(root: Path) -> dict | None:
    pkg_path = root / "package.json"
    if not pkg_path.is_file():
        return None
    try:
        return json.loads(pkg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _expand_npm_script(
    scripts: dict[str, str],
    name: str,
    visited: frozenset[str] | None = None,
    depth: int = 0,
) -> str:
    """Recursively expand ``npm run <name>`` references in a script command.

    Returns the expanded command string.  Empty string on missing script,
    cycle, or excessive depth.
    """
    if depth > 20:
        return ""
    if visited is None:
        visited = frozenset()
    if name in visited:
        return ""
    visited = visited | {name}
    cmd = scripts.get(name, "")
    if not cmd:
        return ""

    def _replace(m: re.Match[str]) -> str:
        inner = m.group(1)
        if inner in scripts:
            return _expand_npm_script(scripts, inner, visited, depth + 1)
        return m.group(0)

    return _NPM_RUN_RE.sub(_replace, cmd)


def _split_atomic(expanded: str) -> list[str]:
    """Split an expanded command string into atomic commands on ``&&`` and ``;``."""
    parts: list[str] = []
    for chunk in expanded.split("&&"):
        for sub in chunk.split(";"):
            stripped = sub.strip()
            if stripped:
                parts.append(stripped)
    return parts


def _runner_of(cmd: str) -> str:
    """Return the first whitespace-delimited token (the runner/path)."""
    stripped = cmd.strip()
    return stripped.split()[0] if stripped else ""


# ---------------------------------------------------------------------------
# Duplicate-execution detection
# ---------------------------------------------------------------------------


def _duplicate_findings(
    root: Path, scripts: dict[str, str]
) -> list[hc.Finding]:
    """Emit PERF findings when an npm script expansion invokes the same
    runner/path more than once."""
    findings: list[hc.Finding] = []
    seen_keys: set[str] = set()

    for name in sorted(scripts):
        expanded = _expand_npm_script(scripts, name)
        if not expanded:
            continue
        atomics = _split_atomic(expanded)
        runners = [(_runner_of(c), c) for c in atomics if _runner_of(c)]

        # Count occurrences per runner
        from collections import Counter
        counts = Counter(r for r, _ in runners)

        for runner, count in counts.items():
            if count <= 1:
                continue
            # Build a stable key to deduplicate across script names
            key = f"{runner}|{count}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            # Collect the duplicated commands
            dup_cmds = [c for r, c in runners if r == runner]
            evidence = f"npm script expansion invokes '{runner}' {count} times: " + " && ".join(dup_cmds)
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="PERF",
                    severity="medium",
                    path="package.json",
                    line_start=0,
                    line_end=0,
                    symbol=f"scripts.{name}",
                    metric_name="duplicate_execution",
                    metric_value=float(count),
                    metric_threshold=1.0,
                    evidence_tool="exec-audit",
                    evidence_raw=evidence,
                    confidence="high",
                    suggested_action=(
                        f"Script '{name}' invokes '{runner}' {count} times "
                        f"after expansion. Consolidate into a single invocation."
                    ),
                )
            )
    return findings


# ---------------------------------------------------------------------------
# JUnit slow-test detection
# ---------------------------------------------------------------------------


def _parse_junit(xml_path: Path) -> list[dict]:
    """Parse a JUnit XML file and return testcase dicts with name, classname, duration."""
    try:
        tree = ET.parse(str(xml_path))
    except (ET.ParseError, OSError) as exc:
        raise ToolError(f"cannot parse {xml_path}: {exc}") from exc
    root_el = tree.getroot()
    cases: list[dict] = []
    for tc in root_el.iter("testcase"):
        name = tc.get("name", "")
        classname = tc.get("classname", "")
        time_str = tc.get("time", "0")
        try:
            duration = float(time_str)
        except (ValueError, TypeError):
            duration = 0.0
        cases.append({"name": name, "classname": classname, "duration": duration})
    return cases


def _slow_test_findings(
    junit_paths: list[str], thresholds: dict
) -> list[hc.Finding]:
    """Emit PERF findings for testcases whose duration exceeds the threshold."""
    threshold = float(thresholds.get("slow_test_threshold_s", 1.0))
    cap = float(thresholds.get("slow_test_cap_s", 300.0))
    findings: list[hc.Finding] = []

    for raw in junit_paths:
        xml_path = Path(raw)
        if not xml_path.is_file():
            raise ToolError(f"junit-xml file not found: {raw}")
        cases = _parse_junit(xml_path)
        for case in cases:
            dur = case["duration"]
            if dur <= threshold:
                continue
            display_dur = min(dur, cap)
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal="PERF",
                    severity="medium",
                    path=str(xml_path),
                    line_start=0,
                    line_end=0,
                    symbol=f"{case['classname']}.{case['name']}",
                    metric_name="slow_test",
                    metric_value=display_dur,
                    metric_threshold=threshold,
                    evidence_tool="exec-audit",
                    evidence_raw=(
                        f"slow test: {case['classname']}.{case['name']} "
                        f"({dur:.3f}s, capped at {cap}s)"
                    ),
                    confidence="high",
                    suggested_action=(
                        f"Test '{case['name']}' takes {dur:.3f}s; "
                        f"consider optimising or splitting."
                    ),
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Benchmark entrypoints-missing detection
# ---------------------------------------------------------------------------


def _has_benchmark_marker(root: Path) -> bool:
    """Check whether the repo has any benchmark entrypoint marker."""
    # pytest-benchmark in requirements / pyproject.toml
    for candidate in [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-test.txt",
        "pyproject.toml",
    ]:
        fp = root / candidate
        if fp.is_file():
            text = fp.read_text(encoding="utf-8", errors="replace")
            if "pytest-benchmark" in text:
                return True
    # package.json benchmark/bench script
    pkg = _load_package_json(root)
    if pkg:
        scripts = pkg.get("scripts", {})
        for name in scripts:
            if name in ("bench", "benchmark") or "bench" in name.split(":"):
                return True
    # pytest marker registration in conftest.py / pytest.ini / pyproject.toml
    for conftest in root.rglob("conftest.py"):
        try:
            text = conftest.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "benchmark" in text and "pytest" in text:
            return True
    # benchmark directories
    for d in root.iterdir():
        if d.is_dir() and d.name in ("benchmarks", "benchmark", "bench"):
            return True
    # pytest.mark.benchmark in test files
    for test_file in root.rglob("test_*.py"):
        try:
            text = test_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "pytest.mark.benchmark" in text:
            return True
    # Makefile / tox.ini / noxfile.py with benchmark target
    for candidate in ["Makefile", "tox.ini", "noxfile.py"]:
        fp = root / candidate
        if fp.is_file():
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "benchmark" in text or "bench" in text:
                return True

    return False


def _benchmark_gap_finding(root: Path) -> hc.Finding | None:
    """Emit at most one low-confidence info finding when no benchmark marker exists."""
    if _has_benchmark_marker(root):
        return None
    return hc.Finding(
        leaf=LEAF,
        signal="PERF",
        severity="info",
        path=".",
        line_start=0,
        line_end=0,
        symbol="benchmark_entrypoints_missing",
        metric_name="benchmark_entrypoints_missing",
        metric_value=1.0,
        metric_threshold=0.0,
        evidence_tool="exec-audit",
        evidence_raw="No benchmark entrypoints detected (pytest-benchmark, bench scripts, benchmark dirs, etc.)",
        confidence="low",
        suggested_action=(
            "Consider adding a benchmark suite (pytest-benchmark, "
            "npm bench script, or benchmark/ directory)."
        ),
    )


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def _render_report(findings: list[hc.Finding]) -> str:
    lines = ["# exec-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"

    by_signal: dict[str, list[hc.Finding]] = {}
    for f in findings:
        by_signal.setdefault(f.signal, []).append(f)
    for sig in sorted(by_signal):
        lines.append(f"## {sig} ({len(by_signal[sig])})")
        for f in by_signal[sig]:
            lines.append(
                f"- `{f.path}` {f.symbol} — "
                f"{f.metric_name}={f.metric_value:g} [{f.severity}]"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _load_thresholds(config_path: str | None) -> dict:
    thresholds: dict[str, object] = dict(DEFAULT_THRESHOLDS)
    if config_path:
        try:
            thresholds.update(
                json.loads(Path(config_path).read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"invalid --config: {exc}") from exc
    return thresholds


# ---------------------------------------------------------------------------
# Main analysis entrypoint
# ---------------------------------------------------------------------------


def _analyze(
    root: Path,
    junit_paths: list[str],
    thresholds: dict,
) -> list[hc.Finding]:
    findings: list[hc.Finding] = []

    # 1. NPM duplicate-execution
    pkg = _load_package_json(root)
    if pkg:
        scripts = pkg.get("scripts") or {}
        if isinstance(scripts, dict):
            findings.extend(_duplicate_findings(root, scripts))

    # 2. JUnit slow-test
    findings.extend(_slow_test_findings(junit_paths, thresholds))

    # 3. Benchmark gap
    bg = _benchmark_gap_finding(root)
    if bg:
        findings.append(bg)

    return hc.sort_findings(findings)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic execution audit (advisory)."
    )
    parser.add_argument("--root", help="Root directory to audit.")
    parser.add_argument("--out-dir", help="Output directory.")
    parser.add_argument(
        "--format", choices=["json", "md"], default="json", help="Report format."
    )
    parser.add_argument(
        "--config", help="JSON file overriding thresholds."
    )
    parser.add_argument(
        "--junit-xml",
        action="append",
        default=[],
        dest="junit_xml",
        help="Path to a JUnit XML report. Repeatable.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.root or not args.out_dir:
        print(
            json.dumps(
                {"status": "error", "message": "--root and --out-dir are required"}
            )
        )
        return hc.EXIT_ERROR
    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir).resolve()

    try:
        thresholds = _load_thresholds(args.config)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR

    try:
        findings = _analyze(root, args.junit_xml, thresholds)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    except Exception as exc:
        print(json.dumps({"status": "error", "message": f"unexpected error: {exc}"}))
        return hc.EXIT_ERROR

    data = hc.write_findings(findings, out_dir, LEAF)
    (out_dir / "exec_report.md").write_text(
        _render_report(findings), encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
