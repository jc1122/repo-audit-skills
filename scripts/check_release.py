#!/usr/bin/env python3
"""Release checks for the code-health-skills package."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Append one entry per skill as later plans land. Name on left == skill dir == SKILL.md name.
REQUIRED_SKILLS = {
    "complexity-audit": "complexity-audit",
}
REQUIRED_SCRIPTS = {
    "complexity-audit": ["scripts/complexity_audit.py"],
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
    if package.get("name") != "code-health-skills":
        defects.append("package.json name must be code-health-skills")
    for path in ["bin/install-code-health-skills.js", "scripts/check_release.py",
                 "scripts/check_skill_fixtures.py", "scripts/check_vendored_common.py",
                 "shared/health_common.py"]:
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
            defects.append(f"{skill_dir}/SKILL.md name is {meta.get('name')!r}, expected {expected_name!r}")
        if meta.get("version") != version:
            defects.append(f"{skill_dir}/SKILL.md version is {meta.get('version')!r}, expected {version!r}")
        for rel_path in REQUIRED_SCRIPTS[skill_dir]:
            if not (skill_root / rel_path).exists():
                defects.append(f"missing script for {skill_dir}: {rel_path}")


def check_installer(defects: list[str]) -> None:
    checks = [
        ["node", "bin/install-code-health-skills.js", "--version"],
        ["node", "bin/install-code-health-skills.js", "--list"],
        ["node", "bin/install-code-health-skills.js", "--dry-run", "--dest", "/tmp/code-health-skills-release-check", "--force"],
    ]
    for cmd in checks:
        result = run(cmd)
        if result.returncode != 0:
            defects.append(f"{' '.join(cmd)} failed: {result.stderr.strip() or result.stdout.strip()}")


def check_git_clean(defects: list[str]) -> None:
    result = run(["git", "status", "--short"])
    if result.returncode != 0:
        defects.append(f"git status failed: {result.stderr.strip()}")
        return
    if result.stdout.strip():
        defects.append("git tree is not clean")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-clean", action="store_true", help="Require a clean git worktree.")
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
    print(json.dumps({"status": "pass", "version": version, "skills": sorted(REQUIRED_SKILLS)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
