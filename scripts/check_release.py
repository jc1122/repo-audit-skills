#!/usr/bin/env python3
"""Release checks for the repo-audit-skills package."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Append one entry per skill as later plans land.
# Name on left == skill dir == SKILL.md name.
REQUIRED_SKILLS = {
    "complexity-audit": "complexity-audit",
    "duplication-audit": "duplication-audit",
    "dead-code-audit": "dead-code-audit",
    "structure-audit": "structure-audit",
    "quality-audit": "quality-audit",
    "code-health-audit-pipeline": "code-health-audit-pipeline",
    "test-audit-pipeline": "test-audit-pipeline",
    "test-quality-assurance": "test-quality-assurance",
    "test-redundancy-triage": "test-redundancy-triage",
    "coverage-gap-audit": "coverage-gap-audit",
    "hotspot-audit": "hotspot-audit",
    "dependency-audit": "dependency-audit",
    "repo-hygiene-audit": "repo-hygiene-audit",
    "docs-consistency-audit": "docs-consistency-audit",
    "security-audit": "security-audit",
    "test-effectiveness-audit": "test-effectiveness-audit",
}
REQUIRED_SCRIPTS = {
    "complexity-audit": ["scripts/complexity_audit.py"],
    "duplication-audit": ["scripts/duplication_audit.py"],
    "dead-code-audit": ["scripts/dead_code_audit.py"],
    "structure-audit": ["scripts/structure_audit.py"],
    "quality-audit": ["scripts/quality_audit.py"],
    "code-health-audit-pipeline": ["scripts/code_health_pipeline.py"],
    "test-audit-pipeline": ["scripts/audit_pipeline.py"],
    "test-quality-assurance": ["scripts/audit_test_quality.py"],
    "test-redundancy-triage": ["scripts/triage_redundancy.py"],
    "coverage-gap-audit": ["scripts/coverage_gap_audit.py"],
    "hotspot-audit": ["scripts/hotspot_audit.py"],
    "dependency-audit": ["scripts/dependency_audit.py"],
    "repo-hygiene-audit": ["scripts/repo_hygiene_audit.py"],
    "docs-consistency-audit": ["scripts/docs_consistency_audit.py"],
    "security-audit": ["scripts/security_audit.py"],
    "test-effectiveness-audit": ["scripts/test_effectiveness_audit.py"],
}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path} does not start with YAML frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError(f"{path} has unterminated YAML frontmatter")
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        values[key.strip()] = raw.strip().strip('"')
    return values


def check_package(defects: list[str]) -> str:
    package_path = ROOT / "package.json"
    if not package_path.exists():
        defects.append("package.json missing")
        return "0.0.0"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    version = str(package.get("version", ""))
    if not SEMVER_RE.match(version):
        defects.append(f"package.json version is not semver: {version!r}")
    if package.get("name") != "repo-audit-skills":
        defects.append("package.json name must be repo-audit-skills")
    for path in [
        "bin/install-repo-audit-skills.js",
        "scripts/check_release.py",
        "scripts/check_skill_fixtures.py",
        "scripts/check_vendored_common.py",
        "scripts/self_audit.py",
        "scripts/check_self_audit.py",
        "scripts/self_audit_baseline.json",
        "scripts/check_coverage_gap.py",
        "scripts/coverage_gap_baseline.json",
        "scripts/gate_common.py",
        "scripts/check_security_audit.py",
        "scripts/security_baseline.json",
        "scripts/check_repo_hygiene.py",
        "scripts/repo_hygiene_baseline.json",
        "scripts/check_docs_consistency.py",
        "scripts/docs_consistency_baseline.json",
        "scripts/check_dependency_audit.py",
        "scripts/dependency_baseline.json",
        "shared/health_common.py",
    ]:
        if not (ROOT / path).exists():
            defects.append(f"required release file missing: {path}")
    return version


def check_skills(version: str, defects: list[str]) -> None:
    for skill_dir, expected_name in REQUIRED_SKILLS.items():
        skill_root = ROOT / "skills" / skill_dir
        skill_md = skill_root / "SKILL.md"
        if not skill_md.exists():
            defects.append(f"missing SKILL.md for {skill_dir}")
            continue
        try:
            meta = frontmatter(skill_md)
        except ValueError as exc:
            defects.append(str(exc))
            continue
        if meta.get("name") != expected_name:
            defects.append(
                f"{skill_dir}/SKILL.md name is {meta.get('name')!r}, "
                f"expected {expected_name!r}"
            )
        if meta.get("version") != version:
            defects.append(
                f"{skill_dir}/SKILL.md version is {meta.get('version')!r}, "
                f"expected {version!r}"
            )
        for rel_path in REQUIRED_SCRIPTS[skill_dir]:
            if not (skill_root / rel_path).exists():
                defects.append(f"missing script for {skill_dir}: {rel_path}")


def check_installer(defects: list[str]) -> None:
    checks = [
        ["node", "bin/install-repo-audit-skills.js", "--version"],
        ["node", "bin/install-repo-audit-skills.js", "--list"],
        [
            "node",
            "bin/install-repo-audit-skills.js",
            "--dry-run",
            "--dest",
            str(Path(tempfile.gettempdir()) / "repo-audit-skills-release-check"),
            "--force",
        ],
    ]
    for cmd in checks:
        result = run(cmd)
        if result.returncode != 0:
            defects.append(
                f"{' '.join(cmd)} failed: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )


def check_git_clean(defects: list[str]) -> None:
    result = run(["git", "status", "--short"])
    if result.returncode != 0:
        defects.append(f"git status failed: {result.stderr.strip()}")
        return
    if result.stdout.strip():
        defects.append("git tree is not clean")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-clean", action="store_true", help="Require a clean git worktree."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    defects: list[str] = []
    version = check_package(defects)
    check_skills(version, defects)
    check_installer(defects)
    if args.require_clean:
        check_git_clean(defects)
    if defects:
        print(json.dumps({"status": "fail", "defects": defects}, indent=2))
        return 1
    print(
        json.dumps(
            {"status": "pass", "version": version, "skills": sorted(REQUIRED_SKILLS)},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
