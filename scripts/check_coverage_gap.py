#!/usr/bin/env python3
"""Testedness gate: run every suite under coverage, then ratchet the
coverage-gap findings against scripts/coverage_gap_baseline.json."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEAF = ROOT / "skills" / "coverage-gap-audit" / "scripts" / "coverage_gap_audit.py"
OUT = ROOT / ".self_audit_out" / "coverage"
SNAPSHOT = ROOT / "scripts" / "coverage_gap_snapshot.json"
BASELINE = ROOT / "scripts" / "coverage_gap_baseline.json"
RCFILE = ROOT / ".coveragerc"
SUITES = [
    "tests",
    "skills/complexity-audit/tests",
    "skills/duplication-audit/tests",
    "skills/dead-code-audit/tests",
    "skills/structure-audit/tests",
    "skills/quality-audit/tests",
    "skills/code-health-audit-pipeline/tests",
    "skills/coverage-gap-audit/tests",
    "skills/test-audit-pipeline/tests",
    "skills/test-quality-assurance/tests",
    "skills/test-redundancy-triage/tests",
]
SUITE_TIMEOUT = 600


def _prefixes() -> list[str]:
    pres = ["shared", "scripts"]
    for d in sorted((ROOT / "skills").iterdir()):
        if (d / "scripts").is_dir():
            pres.append(f"skills/{d.name}/scripts")
    return pres


def run_suites_with_coverage() -> tuple[Path, dict[str, int]]:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob(".coverage*"):
        stale.unlink()
    env = dict(os.environ, COVERAGE_FILE=str(OUT / ".coverage"))
    results: dict[str, int] = {}
    for suite in SUITES:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                suite,
                "-q",
                "-p",
                "no:cacheprovider",
                "--cov",
                "--cov-append",
                "--cov-report=",
                f"--cov-config={RCFILE}",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=SUITE_TIMEOUT,
            check=False,
        )
        results[suite] = proc.returncode
    coverage_json = OUT / "coverage.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "json",
            "-o",
            str(coverage_json),
            f"--rcfile={RCFILE}",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    return coverage_json, results


def run_leaf(coverage_json: Path) -> list[dict]:
    cmd = [
        sys.executable,
        str(LEAF),
        "--root",
        str(ROOT),
        "--out-dir",
        str(OUT / "leaf"),
        "--coverage-json",
        str(coverage_json),
    ]
    for p in _prefixes():
        cmd += ["--source-prefix", p]
    proc = subprocess.run(
        cmd, cwd=ROOT, text=True, capture_output=True, timeout=300, check=False
    )
    if proc.returncode == 2:
        print(json.dumps({"status": "fail", "leaf_error": proc.stdout.strip()}))
        raise SystemExit(1)
    findings = json.loads(
        (OUT / "leaf" / "coverage-gap_findings.json").read_text(encoding="utf-8")
    )
    return sorted(
        ({"path": f["path"], "metric": f["metric"]["name"]} for f in findings),
        key=lambda d: (d["path"], d["metric"]),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run all suites under coverage and ratchet testedness findings."
    )
    parser.add_argument(
        "--coverage-json",
        help="Use an existing coverage.py JSON report instead of running suites "
        "(testing/debugging only).",
    )
    args = parser.parse_args(argv)
    suite_results: dict[str, int] = {}
    if args.coverage_json:
        coverage_json = Path(args.coverage_json)
    else:
        coverage_json, suite_results = run_suites_with_coverage()
        failed = {s: rc for s, rc in suite_results.items() if rc != 0}
        if failed:
            print(json.dumps({"status": "fail", "failed_suites": failed}, indent=2))
            return 1
    current = run_leaf(coverage_json)
    SNAPSHOT.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    base = {tuple(sorted(d.items())) for d in baseline}
    new = [d for d in current if tuple(sorted(d.items())) not in base]
    if new:
        print(json.dumps({"status": "fail", "new_findings": new}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "status": "pass",
                "suites": len(suite_results) or None,
                "count": len(current),
                "baseline": len(baseline),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
