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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_common import verdict  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LEAF = ROOT / "skills" / "coverage-gap-audit" / "scripts" / "coverage_gap_audit.py"
OUT = ROOT / ".self_audit_out" / "coverage"
SNAPSHOT = ROOT / "scripts" / "coverage_gap_snapshot.json"
BASELINE_PATH = "scripts/coverage_gap_baseline.json"
BASELINE = ROOT / BASELINE_PATH
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
    "skills/hotspot-audit/tests",
    "skills/repo-hygiene-audit/tests",
    "skills/dependency-audit/tests",
    "skills/docs-consistency-audit/tests",
    "skills/security-audit/tests",
    "skills/test-effectiveness-audit/tests",
]
SUITE_TIMEOUT = 600


def _prefixes() -> list[str]:
    pres = ["shared", "scripts"]
    for d in sorted((ROOT / "skills").iterdir()):
        if (d / "scripts").is_dir():
            pres.append(f"skills/{d.name}/scripts")
    return pres


def suite_env(out_dir: Path, suite: str) -> dict[str, str]:
    slug = suite.replace("/", "_")
    return dict(os.environ, COVERAGE_FILE=str(out_dir / f".coverage.{slug}"))


def _run_one_suite(suite: str) -> tuple[str, int]:
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
            "--cov-report=",
            f"--cov-config={RCFILE}",
        ],
        cwd=ROOT,
        env=suite_env(OUT, suite),
        text=True,
        capture_output=True,
        timeout=SUITE_TIMEOUT,
        check=False,
    )
    return suite, proc.returncode


def run_suites_with_coverage() -> tuple[Path, dict[str, int]]:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob(".coverage*"):
        stale.unlink()
    from concurrent.futures import ThreadPoolExecutor

    workers = max(2, (os.cpu_count() or 2) - 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = dict(pool.map(_run_one_suite, SUITES))
    env = dict(os.environ, COVERAGE_FILE=str(OUT / ".coverage"))
    subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "combine",
            "--keep",
            *sorted(str(p) for p in OUT.glob(".coverage.*")),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
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
    parser.add_argument(
        "--snapshot",
        help="Use an existing coverage-gap snapshot instead of running coverage+leaf.",
    )
    parser.add_argument(
        "--baseline",
        help="Alternate baseline JSON (testing only).",
    )
    args = parser.parse_args(argv)
    suite_results: dict[str, int] = {}
    if args.snapshot:
        current = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    elif args.coverage_json:
        coverage_json = Path(args.coverage_json)
        current = run_leaf(coverage_json)
    else:
        coverage_json, suite_results = run_suites_with_coverage()
        failed = {s: rc for s, rc in suite_results.items() if rc != 0}
        if failed:
            print(json.dumps({"status": "fail", "failed_suites": failed}, indent=2))
            return 1
        current = run_leaf(coverage_json)

    SNAPSHOT.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    baseline = json.loads(Path(args.baseline or BASELINE).read_text(encoding="utf-8"))
    code, payload = verdict(current, baseline, baseline_path=BASELINE_PATH)
    if code != 0:
        print(json.dumps(payload, indent=2))
        return 1
    print(
        json.dumps(
            {
                "status": "pass",
                "count": payload["count"],
                "baseline": payload["baseline"],
                "suites": len(suite_results) or None,
            },
            indent=2,
        )
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
