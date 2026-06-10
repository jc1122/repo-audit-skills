#!/usr/bin/env python3
"""test-effectiveness-audit leaf: mutmut mutation testing -> TEST findings for weak test suites."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "test-effectiveness"

DEFAULT_THRESHOLDS = {
    "min_kill_rate": 0.8,
    "mutmut_timeout_seconds": 600,
    "estimated_mutants_per_def": 8,
}

PROBLEM_STATUSES = {"survived", "no tests"}


class ToolError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Task A6 verbatim parser functions
# ---------------------------------------------------------------------------


def parse_results_text(text: str) -> dict[str, str]:
    """'    calc.x_weak__mutmut_1: no tests' -> {key: status}; killed mutants are absent."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if ": " in line and "__mutmut_" in line:
            key, _, status = line.partition(": ")
            out[key] = status.strip()
    return out


def module_totals(work: Path) -> dict[str, int]:
    """mutants/<rel>.py.meta -> {module_rel_path: total_mutants} via exit_code_by_key length."""
    totals: dict[str, int] = {}
    mutants_dir = work / "mutants"
    if not mutants_dir.is_dir():
        return totals
    for meta in sorted(mutants_dir.rglob("*.py.meta")):
        rel = meta.relative_to(mutants_dir).as_posix()[: -len(".meta")]
        data = json.loads(meta.read_text(encoding="utf-8"))
        totals[rel] = len(data.get("exit_code_by_key", {}))
    return totals


def key_to_module(key: str) -> str:
    """'pkg.calc.x_weak__mutmut_3' -> 'pkg/calc.py' (dotted module prefix before .x_)."""
    dotted = key.split(".x_", 1)[0]
    return dotted.replace(".", "/") + ".py"


# ---------------------------------------------------------------------------
# Stable internal helpers for tests
# ---------------------------------------------------------------------------


def estimate_mutants(
    root: Path, rel_paths: list[str], estimated_mutants_per_def: int
) -> int:
    """Count ast.FunctionDef + ast.AsyncFunctionDef nodes across scoped files."""
    total_defs = 0
    for rel in rel_paths:
        p = root / rel
        if p.is_file() and p.suffix == ".py":
            try:
                tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
                total_defs += sum(
                    1
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
            except SyntaxError:
                pass
        elif p.is_dir():
            for py_file in sorted(p.rglob("*.py")):
                try:
                    tree = ast.parse(
                        py_file.read_text(encoding="utf-8", errors="replace")
                    )
                    total_defs += sum(
                        1
                        for node in ast.walk(tree)
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )
                except SyntaxError:
                    pass
    return total_defs * estimated_mutants_per_def


def read_scope_paths(root: Path, paths_file: Path) -> list[str]:
    """Read newline-separated root-relative .py files/dirs from a file."""
    text = paths_file.read_text(encoding="utf-8", errors="replace")
    rels: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            rels.append(line)
    return rels


def prepare_sandbox(
    root: Path, rel_paths: list[str], tests_dir: str, out_dir: Path
) -> Path:
    """Set up mutmut sandbox at out_dir/.mutmut-work.  Returns the work directory."""
    work = out_dir / ".mutmut-work"
    # Wipe per run
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    top_entries: list[str] = []

    for rel in rel_paths:
        src = root / rel
        dst = work / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        elif src.is_file():
            shutil.copy2(src, dst)
        # Top-level entry = first path component of the copied path
        top = rel.split("/")[0]
        if top not in top_entries:
            top_entries.append(top)

    # Copy tests dir
    tests_src = root / tests_dir
    tests_dst = work / tests_dir
    if tests_src.is_dir():
        if tests_dst.exists():
            shutil.rmtree(tests_dst)
        shutil.copytree(tests_src, tests_dst)

    # Write setup.cfg
    source_paths_str = " ".join(top_entries)
    (work / "setup.cfg").write_text(
        f"[mutmut]\nsource_paths={source_paths_str}\n", encoding="utf-8"
    )

    return work


def _resolve_module_for_key(
    problem_key: str, totals: dict[str, int]
) -> str | None:
    """Map a problem key to the matching module total key.

    Real mutmut with source_paths=src emits keys like ``calc.x_weak__mutmut_1``
    while meta lives at ``src/calc.py``.  key_to_module produces ``calc.py``;
    we reconcile by suffix-matching against module-total keys ending in
    ``/calc.py``.  Direct matches are also supported.
    """
    km = key_to_module(problem_key)
    # Direct match
    if km in totals:
        return km
    # Suffix match (unique only)
    candidates = [k for k in totals if k.endswith("/" + km)]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _in_scope(rel: str, prefixes: list[str]) -> bool:
    """Return True when *rel* starts with a source prefix (or no prefixes given)."""
    return not prefixes or any(rel.startswith(p) for p in prefixes)


def findings_from_mutmut(
    work: Path, thresholds: dict, root_rel_prefix: str = ""
) -> list[hc.Finding]:
    """Produce TEST findings for modules below the kill-rate threshold."""
    min_kill_rate = float(thresholds["min_kill_rate"])

    totals = module_totals(work)
    if not totals:
        return []

    # Run mutmut results
    proc = subprocess.run(
        [sys.executable, "-m", "mutmut", "results"],
        cwd=str(work),
        text=True,
        capture_output=True,
        check=False,
    )
    results_text = proc.stdout
    problem_entries = parse_results_text(results_text)

    # Map problem keys to module keys
    module_problems: dict[str, dict[str, str]] = {m: {} for m in totals}
    for problem_key, status in problem_entries.items():
        if status not in PROBLEM_STATUSES:
            continue
        matched = _resolve_module_for_key(problem_key, totals)
        if matched:
            module_problems[matched][problem_key] = status

    findings: list[hc.Finding] = []
    for module_path in sorted(totals):
        total = totals[module_path]
        problems = module_problems[module_path]
        num_problems = len(problems)
        if total == 0:
            continue
        kill_rate = (total - num_problems) / total
        if kill_rate >= min_kill_rate:
            continue

        severity = "high" if kill_rate < 0.5 else "medium"

        # Build evidence: up to 10 key=status entries
        survivor_keys = sorted(problems.keys())
        evidence_parts = [f"{k}={problems[k]}" for k in survivor_keys[:10]]
        evidence_raw = "; ".join(evidence_parts)
        if len(survivor_keys) > 10:
            evidence_raw += f" ...(+{len(survivor_keys) - 10} more)"

        # mutmut show for first 3 survivors — append @@ hunk headers
        for survivor_key in survivor_keys[:3]:
            try:
                show = subprocess.run(
                    [sys.executable, "-m", "mutmut", "show", survivor_key],
                    cwd=str(work),
                    text=True,
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                for line in show.stdout.splitlines() + show.stderr.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("@@"):
                        evidence_raw += "\n" + stripped
            except (subprocess.TimeoutExpired, OSError):
                pass

        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal="TEST",
                severity=severity,
                path=module_path,
                line_start=1,
                line_end=1,
                symbol="<module>",
                metric_name="mutation_kill_rate",
                metric_value=round(kill_rate, 3),
                metric_threshold=min_kill_rate,
                evidence_tool="mutmut",
                evidence_raw=evidence_raw,
                confidence="high",
                suggested_action=(
                    f"Strengthen assertions/cases for {module_path}: "
                    "surviving mutants listed in evidence"
                ),
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Analysis pipeline
# ---------------------------------------------------------------------------


def analyze_tree(
    root: str | Path,
    source_prefixes: list[str],
    thresholds: dict,
    paths_file: str | Path,
    tests_dir: str,
    max_mutants: int,
    out_dir: str | Path,
) -> tuple[list[hc.Finding], int]:
    """Run the full test-effectiveness pipeline.  Returns (findings, actual_total)."""
    root = Path(root).resolve()
    out_dir = Path(out_dir).resolve()

    # Read scope paths
    rel_paths = read_scope_paths(root, Path(paths_file))
    if not rel_paths:
        return [], 0

    # Estimate mutant budget
    est = estimate_mutants(
        root, rel_paths, int(thresholds["estimated_mutants_per_def"])
    )
    if est > max_mutants:
        raise ToolError(
            f"scope too large: ~{est} mutants > --max-mutants {max_mutants}; "
            "narrow --paths"
        )

    # Probe for mutmut
    if importlib.util.find_spec("mutmut") is None:
        raise ToolError("mutmut is not installed; pip install mutmut==3.6.0")

    # Prepare sandbox
    work = prepare_sandbox(root, rel_paths, tests_dir, out_dir)

    timeout = int(thresholds["mutmut_timeout_seconds"])

    # Run mutmut
    try:
        subprocess.run(
            [sys.executable, "-m", "mutmut", "run"],
            cwd=str(work),
            timeout=timeout,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(
            f"mutmut run timed out after {timeout}s; increase "
            "mutmut_timeout_seconds or narrow --paths"
        ) from None

    # Export CI/CD stats
    subprocess.run(
        [sys.executable, "-m", "mutmut", "export-cicd-stats"],
        cwd=str(work),
        check=False,
        capture_output=True,
        text=True,
    )

    # Produce findings
    findings = findings_from_mutmut(work, thresholds)
    actual_total = sum(module_totals(work).values())

    # Filter by source prefixes
    if source_prefixes:
        findings = [
            f for f in findings if _in_scope(f.path, list(source_prefixes))
        ]

    return hc.sort_findings(findings), actual_total


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# test-effectiveness-audit report", ""]
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
                f"- `{f.path}:{f.line_start}` {f.symbol} — "
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
        description="Deterministic mutation-testing effectiveness audit (advisory)."
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
    parser.add_argument(
        "--paths",
        help="File containing newline-separated root-relative .py files or dirs to mutate.",
    )
    parser.add_argument(
        "--tests-dir",
        help="Root-relative test directory to copy into the sandbox.",
        dest="tests_dir",
    )
    parser.add_argument(
        "--max-mutants",
        type=int,
        help="Maximum estimated mutants before refusing to run.",
        dest="max_mutants",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Validate required flags
    missing = []
    if not args.root:
        missing.append("--root")
    if not args.out_dir:
        missing.append("--out-dir")
    if not args.paths:
        missing.append("--paths")
    if not args.tests_dir:
        missing.append("--tests-dir")
    if args.max_mutants is None:
        missing.append("--max-mutants")

    if missing:
        msg = (
            f"Mutation testing requires scoped paths: --paths, --tests-dir, "
            f"and --max-mutants are mandatory "
            f"(missing: {', '.join(missing)}). "
            f"Unscoped mutation testing costs hours; feed it e.g. the top-N "
            f"hotspot paths."
        )
        print(json.dumps({"status": "error", "message": msg}))
        return hc.EXIT_ERROR

    try:
        thresholds = load_thresholds(args.config)
        findings, actual_total = analyze_tree(
            args.root,
            args.source_prefixes,
            thresholds,
            args.paths,
            args.tests_dir,
            args.max_mutants,
            args.out_dir,
        )
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR

    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, f"{LEAF}_report.md").write_text(
        render_report(findings), encoding="utf-8"
    )

    status: dict = {"status": "ok", "findings": len(data), "leaf": LEAF}
    if actual_total > args.max_mutants:
        status["budget_exceeded"] = True
    print(json.dumps(status))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
