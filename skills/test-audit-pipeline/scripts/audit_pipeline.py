#!/usr/bin/env python3
"""Unified test-audit pipeline.

Orchestrates coverage collection, TQA scoring, and redundancy triage into a
single workflow with parallel execution of independent stages.

Usage:
    python audit_pipeline.py --root /path/to/repo --python .venv/bin/python \
        --suite tests/test_api.py --out-dir /tmp/audit

Exit codes:
    0  All stages succeeded
    1  One or more stages failed (partial results are still written)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Script discovery
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR.parent.parent  # ~/.agents/skills/
DEFAULT_TQA_SCRIPT = (
    SKILLS_DIR / "test-quality-assurance" / "scripts" / "audit_test_quality.py"
)
DEFAULT_TRIAGE_SCRIPT = (
    SKILLS_DIR / "test-redundancy-triage" / "scripts" / "triage_redundancy.py"
)
StageReportStatus = dict[str, bool]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log(msg: str) -> None:
    """Print a progress message to stderr."""
    print(msg, file=sys.stderr, flush=True)


def _build_env(base_env: dict[str, str], env_pairs: list[str]) -> dict[str, str]:
    """Merge current environment with user-supplied KEY=VALUE pairs."""
    env = {**base_env}
    for pair in env_pairs:
        if "=" not in pair:
            _log(f"WARNING: ignoring malformed --env value (no '='): {pair}")
            continue
        key, _, value = pair.partition("=")
        env[key] = value
    return env


def _run_stage(
    cmd: list[str],
    *,
    env: dict[str, str],
    cwd: str | Path,
    label: str,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and return the CompletedProcess."""
    _log(f"  → {label}: {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        env=env,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    """Read a JSON file, returning None on failure."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Stage 1: Coverage collection
# ---------------------------------------------------------------------------


def stage_coverage(
    *,
    python: str,
    root: Path,
    source_prefix: str | None,
    out_dir: Path,
    test_marker: str,
    env: dict[str, str],
) -> tuple[bool, Path]:
    """Collect branch coverage with pytest-cov. Returns (success, json_path)."""
    cov_json = out_dir / "coverage.json"
    cov_source = source_prefix if source_prefix else str(root)

    cmd = [
        python,
        "-m",
        "pytest",
        "-m",
        test_marker,
        "-n",
        "0",
        f"--cov={cov_source}",
        "--cov-branch",
        f"--cov-report=json:{cov_json}",
        "-q",
    ]
    result = _run_stage(cmd, env=env, cwd=root, label="coverage")
    if result.returncode != 0:
        _log(f"  ✗ Coverage collection failed (exit {result.returncode})")
        if result.stderr:
            _log(result.stderr[:2000])
        return False, cov_json
    _log("  ✓ Coverage collected")
    return True, cov_json


# ---------------------------------------------------------------------------
# Stage 2a: TQA audit
# ---------------------------------------------------------------------------


def stage_tqa(
    *,
    python: str,
    tqa_script: Path,
    root: Path,
    out_dir: Path,
    cov_json: Path | None,
    internal_import_patterns: list[str],
    public_hints: list[str],
    tqa_baseline: str | None,
    env: dict[str, str],
) -> tuple[bool, Path, Path]:
    """Run the TQA audit script. Returns (success, json_path, md_path)."""
    json_out = out_dir / "tqa_report.json"
    md_out = out_dir / "tqa_report.md"

    cmd = [
        python,
        str(tqa_script),
        "--root",
        str(root),
        "--json-out",
        str(json_out),
        "--md-out",
        str(md_out),
    ]
    for pat in internal_import_patterns:
        cmd += ["--internal-import-pattern", pat]
    for hint in public_hints:
        cmd += ["--public-hint", hint]
    if cov_json and cov_json.exists():
        cmd += ["--cov-json", str(cov_json)]
    if tqa_baseline:
        cmd += ["--baseline-json", tqa_baseline]

    result = _run_stage(cmd, env=env, cwd=root, label="TQA audit")
    if result.returncode != 0:
        _log(f"  ✗ TQA audit failed (exit {result.returncode})")
        if result.stderr:
            _log(result.stderr[:2000])
        return False, json_out, md_out
    _log("  ✓ TQA audit complete")
    return True, json_out, md_out


# ---------------------------------------------------------------------------
# Stage 2b: Redundancy triage
# ---------------------------------------------------------------------------


def stage_triage(
    *,
    python: str,
    triage_script: Path,
    root: Path,
    suites: list[str],
    comparator_suites: list[str],
    source_prefix: str | None,
    out_dir: Path,
    max_workers: int,
    env_pairs: list[str],
    env: dict[str, str],
) -> tuple[bool, Path]:
    """Run the redundancy triage script. Returns (success, triage_dir)."""
    triage_dir = out_dir / "triage"
    triage_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        python,
        str(triage_script),
        "--root",
        str(root),
        "--python",
        python,
        "--out-dir",
        str(triage_dir),
        "--max-workers",
        str(max_workers),
    ]
    for s in suites:
        cmd += ["--suite", s]
    for cs in comparator_suites:
        cmd += ["--comparator-suite", cs]
    if source_prefix:
        cmd += ["--source-prefix", source_prefix]
    for pair in env_pairs:
        cmd += ["--env", pair]

    result = _run_stage(cmd, env=env, cwd=root, label="Redundancy triage")
    if result.returncode != 0:
        _log(f"  ✗ Redundancy triage failed (exit {result.returncode})")
        if result.stderr:
            _log(result.stderr[:2000])
        return False, triage_dir
    _log("  ✓ Redundancy triage complete")
    return True, triage_dir


# ---------------------------------------------------------------------------
# Stage 3: Unified report
# ---------------------------------------------------------------------------


def _extract_coverage_summary(cov_json: Path) -> dict[str, Any]:
    """Extract summary stats from coverage.json."""
    data = _read_json(cov_json)
    if not data:
        return {}
    totals = data.get("totals", {})
    return {
        "covered_lines": totals.get("covered_lines", 0),
        "missing_lines": totals.get("missing_lines", 0),
        "num_statements": totals.get("num_statements", 0),
        "percent_covered": totals.get("percent_covered", 0.0),
        "covered_branches": totals.get("covered_branches", 0),
        "missing_branches": totals.get("missing_branches", 0),
        "num_branches": totals.get("num_branches", 0),
        "percent_covered_display": totals.get("percent_covered_display", "N/A"),
    }


def _extract_triage_summary(triage_dir: Path) -> dict[str, Any]:
    """Extract decision counts from triage outputs."""
    summary: dict[str, Any] = {"decisions": {}, "candidates": []}
    # Look for candidate_validation.csv or JSON summary
    csv_path = triage_dir / "candidate_validation.csv"
    if csv_path.exists():
        import csv

        decisions: dict[str, int] = {}
        candidates: list[dict[str, str]] = []
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                dec = row.get("validation_decision", row.get("decision", "UNKNOWN"))
                decisions[dec] = decisions.get(dec, 0) + 1
                candidates.append(
                    {
                        "test": row.get("candidate", row.get("test_id", "")),
                        "decision": dec,
                    }
                )
        summary["decisions"] = decisions
        summary["candidates"] = candidates
    return summary


def build_summary(
    stage_results: dict,
    findings: list,
    *,
    root: str = "",
    stages_run: list[str] | None = None,
    stage_status: dict[str, str] | None = None,
    parallel_stages: list[str] | None = None,
    cov_summary: dict[str, Any] | None = None,
    tqa_data: dict[str, Any] | None = None,
    triage_summary: dict[str, Any] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Build the canonical pipeline summary dict (pure, no side effects).

    Timestamps and wall-clock values live under ``"meta"`` so the canonical
    body is deterministic.
    """
    if stages_run is None:
        stages_run = []
    if stage_status is None:
        stage_status = {}
    if parallel_stages is None:
        parallel_stages = []
    if cov_summary is None:
        cov_summary = {}
    if tqa_data is None:
        tqa_data = {}
    if triage_summary is None:
        triage_summary = {}
    if now is None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    summary: dict[str, Any] = {
        "meta": {"generated_at": now},
        "root": root,
        "stages_run": stages_run,
        "stage_status": stage_status,
        "parallel_stages": parallel_stages,
    }
    if cov_summary:
        summary["coverage"] = cov_summary
    if tqa_data:
        summary["tqa"] = {
            "rubric_scores": tqa_data.get("rubric_scores", tqa_data.get("scores", {})),
            "overall_score": tqa_data.get("overall_score", tqa_data.get("grade")),
            "findings_count": len(
                tqa_data.get("findings", tqa_data.get("action_items", []))
            ),
        }
    if triage_summary.get("decisions"):
        summary["triage"] = {
            "decisions": triage_summary["decisions"],
            "total_candidates": len(triage_summary.get("candidates", [])),
        }
    return summary


def _append_parallelism_section(lines: list[str], parallel_stages: list[str]) -> None:
    lines.append("## Parallelism Opportunities")
    lines.append("")
    if parallel_stages:
        lines.append(f"Stages run in parallel: **{', '.join(parallel_stages)}**")
    else:
        lines.append("No stages were run in parallel (single-stage mode).")
    lines.append("")
    lines.append("For agent orchestrators with subagent capabilities:")
    lines.append(
        "- Stage 2a (TQA) can be delegated to a `test-quality-assurance` subagent"
    )
    lines.append(
        "- Stage 2b (Triage) can be delegated to a `test-redundancy-triage` subagent"
    )
    lines.append(
        "- Both subagents can run concurrently after coverage collection completes"
    )
    lines.append("")


def _append_tqa_section(
    lines: list[str], tqa_ok: bool, tqa_data: dict[str, Any]
) -> None:
    lines.append("## TQA Quality Scores")
    lines.append("")
    if not tqa_ok:
        lines.append("*TQA audit failed — no scores available.*")
    elif tqa_data:
        rubric = tqa_data.get("rubric_scores", tqa_data.get("scores", {}))
        if rubric:
            lines.append("| Dimension | Score |")
            lines.append("|-----------|-------|")
            for dim, score in rubric.items():
                lines.append(f"| {dim} | {score} |")
        else:
            lines.append("*No rubric scores found in TQA output.*")
        overall = tqa_data.get("overall_score", tqa_data.get("grade"))
        if overall is not None:
            lines.append("")
            lines.append(f"**Overall score**: {overall}")
    else:
        lines.append("*TQA report not found.*")
    lines.append("")


def _append_coverage_section(
    lines: list[str],
    skip_coverage: bool,
    coverage_ok: bool,
    cov_summary: dict[str, Any],
) -> None:
    lines.append("## Coverage Summary")
    lines.append("")
    if skip_coverage:
        lines.append("*Coverage collection was skipped.*")
    elif not coverage_ok:
        lines.append("*Coverage collection failed.*")
    elif cov_summary:
        lines.append(
            f"- **Line coverage**: {cov_summary.get('percent_covered_display', 'N/A')}"
        )
        lines.append(f"- **Statements**: {cov_summary.get('num_statements', 'N/A')}")
        lines.append(f"- **Covered lines**: {cov_summary.get('covered_lines', 'N/A')}")
        lines.append(f"- **Missing lines**: {cov_summary.get('missing_lines', 'N/A')}")
        lines.append(f"- **Branches**: {cov_summary.get('num_branches', 'N/A')}")
        lines.append(
            f"- **Covered branches**: {cov_summary.get('covered_branches', 'N/A')}"
        )
        lines.append(
            f"- **Missing branches**: {cov_summary.get('missing_branches', 'N/A')}"
        )
    else:
        lines.append("*No coverage data available.*")
    lines.append("")


def _append_triage_section(
    lines: list[str],
    skip_triage: bool,
    triage_ok: bool,
    triage_summary: dict[str, Any],
) -> None:
    lines.append("## Redundancy Triage Decisions")
    lines.append("")
    if skip_triage:
        lines.append("*Redundancy triage was skipped.*")
    elif not triage_ok:
        lines.append("*Redundancy triage failed.*")
    elif triage_summary.get("decisions"):
        decisions = triage_summary["decisions"]
        lines.append("| Decision | Count |")
        lines.append("|----------|-------|")
        for dec, count in sorted(decisions.items()):
            lines.append(f"| {dec} | {count} |")
        lines.append("")
        actionable = [
            c
            for c in triage_summary.get("candidates", [])
            if "DELETE" in c.get("decision", "") or "MERGE" in c.get("decision", "")
        ]
        if actionable:
            lines.append("### Actionable Candidates")
            lines.append("")
            for c in actionable:
                lines.append(f"- **{c['decision']}**: `{c['test']}`")
    else:
        lines.append("*No triage decisions found.*")
    lines.append("")


def _triage_action_items(triage_summary: dict[str, Any]) -> list[str]:
    action_items: list[str] = []
    if triage_summary.get("decisions"):
        n_delete = sum(
            v for k, v in triage_summary["decisions"].items() if "DELETE" in k
        )
        n_merge = sum(v for k, v in triage_summary["decisions"].items() if "MERGE" in k)
        if n_delete:
            action_items.append(f"Review and remove {n_delete} delete-safe test(s)")
        if n_merge:
            action_items.append(
                f"Review and consolidate {n_merge} merge-candidate test(s)"
            )
    return action_items


def _tqa_action_items(tqa_data: dict[str, Any]) -> list[str]:
    action_items: list[str] = []
    if tqa_data:
        findings = tqa_data.get("findings", tqa_data.get("action_items", []))
        if isinstance(findings, list):
            for f in findings[:5]:
                if isinstance(f, dict):
                    action_items.append(f.get("description", f.get("text", str(f))))
                elif isinstance(f, str):
                    action_items.append(f)
    return action_items


def _report_action_items(
    tqa_data: dict[str, Any], triage_summary: dict[str, Any]
) -> list[str]:
    return _triage_action_items(triage_summary) + _tqa_action_items(tqa_data)


def _append_action_items_section(
    lines: list[str], tqa_data: dict[str, Any], triage_summary: dict[str, Any]
) -> None:
    lines.append("## Action Items")
    lines.append("")
    action_items = _report_action_items(tqa_data, triage_summary)
    if action_items:
        for i, item in enumerate(action_items, 1):
            lines.append(f"{i}. {item}")
    else:
        lines.append("*No action items generated.*")
    lines.append("")


def _append_stage_status_section(
    lines: list[str],
    status: StageReportStatus,
) -> None:
    lines.append("## Stage Status")
    lines.append("")
    lines.append("| Stage | Status |")
    lines.append("|-------|--------|")
    if not status["skip_coverage"]:
        coverage_status = "✓ OK" if status["coverage_ok"] else "✗ FAILED"
        lines.append(f"| Coverage | {coverage_status} |")
    lines.append(f"| TQA Audit | {'✓ OK' if status['tqa_ok'] else '✗ FAILED'} |")
    if not status["skip_triage"]:
        lines.append(f"| Triage | {'✓ OK' if status['triage_ok'] else '✗ FAILED'} |")
    lines.append("")


def _make_stage_report_status(
    tqa_ok: bool,
    triage_ok: bool,
    coverage_ok: bool,
    skip_triage: bool,
    skip_coverage: bool,
) -> StageReportStatus:
    return {
        "tqa_ok": tqa_ok,
        "triage_ok": triage_ok,
        "coverage_ok": coverage_ok,
        "skip_triage": skip_triage,
        "skip_coverage": skip_coverage,
    }


def _stage_status_dict(status: StageReportStatus) -> dict[str, str]:
    return {
        "coverage": (
            "ok"
            if status["coverage_ok"]
            else ("skipped" if status["skip_coverage"] else "failed")
        ),
        "tqa": "ok" if status["tqa_ok"] else "failed",
        "triage": (
            "ok"
            if status["triage_ok"]
            else ("skipped" if status["skip_triage"] else "failed")
        ),
    }


def _stage_report_header(now: str, root: Path, stages_run: list[str]) -> list[str]:
    return [
        "# Test Audit Pipeline Report",
        "",
        f"**Generated**: {now}",
        f"**Root**: `{root}`",
        f"**Stages run**: {', '.join(stages_run)}",
        "",
    ]


def _load_stage_report_inputs(
    skip_coverage: bool,
    skip_triage: bool,
    tqa_json_path: Path,
    cov_json_path: Path,
    triage_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    tqa_data = _read_json(tqa_json_path) or {}
    cov_summary = _extract_coverage_summary(cov_json_path) if not skip_coverage else {}
    triage_summary = _extract_triage_summary(triage_dir) if not skip_triage else {}
    return tqa_data, cov_summary, triage_summary


def _write_report_markdown(out_dir: Path, lines: list[str]) -> None:
    report_md = out_dir / "pipeline_report.md"
    report_md.write_text("\n".join(lines))
    _log(f"  → Wrote {report_md}")


def stage_report(
    *,
    out_dir: Path,
    root: Path,
    stages_run: list[str],
    tqa_ok: bool,
    triage_ok: bool,
    coverage_ok: bool,
    skip_triage: bool,
    skip_coverage: bool,
    tqa_json_path: Path,
    cov_json_path: Path,
    triage_dir: Path,
    parallel_stages: list[str],
) -> bool:
    """Generate unified pipeline_report.md and pipeline_summary.json."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status = _make_stage_report_status(
        tqa_ok, triage_ok, coverage_ok, skip_triage, skip_coverage
    )
    tqa_data, cov_summary, triage_summary = _load_stage_report_inputs(
        skip_coverage, skip_triage, tqa_json_path, cov_json_path, triage_dir
    )

    # --- Markdown report ---
    lines = _stage_report_header(now, root, stages_run)
    _append_parallelism_section(lines, parallel_stages)
    _append_tqa_section(lines, tqa_ok, tqa_data)
    _append_coverage_section(lines, skip_coverage, coverage_ok, cov_summary)
    _append_triage_section(lines, skip_triage, triage_ok, triage_summary)
    _append_action_items_section(lines, tqa_data, triage_summary)
    _append_stage_status_section(lines, status)

    _write_report_markdown(out_dir, lines)

    # --- JSON summary ---
    summary = build_summary(
        {},  # stage_results — reserved for future extensibility
        [],  # findings — reserved for future extensibility
        root=str(root),
        stages_run=stages_run,
        stage_status=_stage_status_dict(status),
        parallel_stages=parallel_stages,
        cov_summary=cov_summary,
        tqa_data=tqa_data,
        triage_summary=triage_summary,
        now=now,
    )

    summary_json = out_dir / "pipeline_summary.json"
    summary_json.write_text(json.dumps(summary, indent=2))
    _log(f"  → Wrote {summary_json}")

    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_suite_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--suite", action="append", default=[], help="Test suite file/dir (repeatable)"
    )
    parser.add_argument(
        "--comparator-suite",
        action="append",
        default=[],
        help="Comparator suite (repeatable)",
    )
    parser.add_argument(
        "--source-prefix",
        default=None,
        help="Source prefix for coverage (e.g. src/pkg/)",
    )
    parser.add_argument(
        "--internal-import-pattern",
        action="append",
        default=[],
        help="Regex for internal imports (TQA)",
    )
    parser.add_argument(
        "--public-hint",
        action="append",
        default=[],
        help="Public API hint string (TQA)",
    )


def _add_execution_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--out-dir", required=True, type=Path, help="Output directory for all reports"
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        help="Environment variable KEY=VALUE (repeatable)",
    )
    parser.add_argument(
        "--tqa-baseline", default=None, help="Path to previous TQA JSON for comparison"
    )
    parser.add_argument(
        "--skip-triage", action="store_true", help="Skip redundancy triage stage"
    )
    parser.add_argument(
        "--skip-coverage", action="store_true", help="Skip coverage collection stage"
    )
    parser.add_argument(
        "--test-marker",
        default="not benchmark and not slow",
        help="Pytest marker expression for coverage",
    )
    parser.add_argument(
        "--max-workers", type=int, default=4, help="Max workers for triage parallelism"
    )
    parser.add_argument(
        "--tqa-script",
        type=Path,
        default=None,
        help="Override path to audit_test_quality.py",
    )
    parser.add_argument(
        "--triage-script",
        type=Path,
        default=None,
        help="Override path to triage_redundancy.py",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified test-audit pipeline: coverage → TQA + triage → report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", required=True, type=Path, help="Repository root path")
    parser.add_argument(
        "--python", default=sys.executable, help="Python interpreter to use"
    )
    _add_suite_args(parser)
    _add_execution_args(parser)
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    return _build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = parse_args(argv)
    root = args.root.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tqa_script = args.tqa_script or DEFAULT_TQA_SCRIPT
    triage_script = args.triage_script or DEFAULT_TRIAGE_SCRIPT

    # Validate scripts exist
    if not tqa_script.exists():
        _log(f"ERROR: TQA script not found: {tqa_script}")
        return 1
    if not args.skip_triage and not triage_script.exists():
        _log(f"ERROR: Triage script not found: {triage_script}")
        return 1

    env = _build_env(os.environ.copy(), args.env)
    any_failure = False

    # ------------------------------------------------------------------
    # Stage 1: Coverage
    # ------------------------------------------------------------------
    stages_run: list[str] = []
    coverage_ok = True
    cov_json = out_dir / "coverage.json"

    if not args.skip_coverage:
        _log("Stage 1/3: Collecting coverage...")
        stages_run.append("coverage")
        coverage_ok, cov_json = stage_coverage(
            python=args.python,
            root=root,
            source_prefix=args.source_prefix,
            out_dir=out_dir,
            test_marker=args.test_marker,
            env=env,
        )
        if not coverage_ok:
            any_failure = True
    else:
        _log("Stage 1/3: Coverage collection skipped")

    # ------------------------------------------------------------------
    # Stage 2: Parallel TQA + Triage
    # ------------------------------------------------------------------
    _log("Stage 2/3: Running TQA + triage in parallel...")
    tqa_ok = False
    triage_ok = True
    tqa_json_path = out_dir / "tqa_report.json"
    tqa_md_path = out_dir / "tqa_report.md"
    triage_dir = out_dir / "triage"
    parallel_stages: list[str] = []

    run_tqa = True
    run_triage = not args.skip_triage and len(args.suite) > 0

    _tqa_kw = dict(
        python=args.python,
        tqa_script=tqa_script,
        root=root,
        out_dir=out_dir,
        cov_json=cov_json if not args.skip_coverage else None,
        internal_import_patterns=args.internal_import_pattern,
        public_hints=args.public_hint,
        tqa_baseline=args.tqa_baseline,
        env=env,
    )
    _tri_kw = dict(
        python=args.python,
        triage_script=triage_script,
        root=root,
        suites=args.suite,
        comparator_suites=args.comparator_suite,
        source_prefix=args.source_prefix,
        out_dir=out_dir,
        max_workers=args.max_workers,
        env_pairs=args.env,
        env=env,
    )

    if run_tqa and run_triage:
        parallel_stages = ["TQA audit", "Redundancy triage"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_tqa: Future[tuple[bool, Path, Path]] = pool.submit(stage_tqa, **_tqa_kw)
            fut_triage: Future[tuple[bool, Path]] = pool.submit(stage_triage, **_tri_kw)
            tqa_ok, tqa_json_path, tqa_md_path = fut_tqa.result()
            triage_ok, triage_dir = fut_triage.result()
    else:
        if run_tqa:
            stages_run.append("tqa")
            tqa_ok, tqa_json_path, tqa_md_path = stage_tqa(**_tqa_kw)
        if run_triage:
            stages_run.append("triage")
            triage_ok, triage_dir = stage_triage(**_tri_kw)

    if run_tqa:
        stages_run.append("tqa")
    if run_triage:
        stages_run.append("triage")
    if not tqa_ok:
        any_failure = True
    if not triage_ok:
        any_failure = True

    # ------------------------------------------------------------------
    # Stage 3: Unified report
    # ------------------------------------------------------------------
    _log("Stage 3/3: Generating unified report...")
    stages_run.append("report")
    stage_report(
        out_dir=out_dir,
        root=root,
        stages_run=stages_run,
        tqa_ok=tqa_ok,
        triage_ok=triage_ok,
        coverage_ok=coverage_ok,
        skip_triage=args.skip_triage,
        skip_coverage=args.skip_coverage,
        tqa_json_path=tqa_json_path,
        cov_json_path=cov_json,
        triage_dir=triage_dir,
        parallel_stages=parallel_stages,
    )

    if any_failure:
        _log("Pipeline completed with failures — partial results written")
        return 1

    _log("Pipeline completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
