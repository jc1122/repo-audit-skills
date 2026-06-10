import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_package_skills_installer_checks_pass_on_real_package():
    mod = _load("check_release")
    defects: list[str] = []
    version = mod.check_package(defects)
    mod.check_skills(version, defects)
    mod.check_installer(defects)
    assert defects == [], defects
    assert mod.SEMVER_RE.match(version)


def test_frontmatter_parses_a_skill_md():
    mod = _load("check_release")
    fm = mod.frontmatter(ROOT / "skills" / "coverage-gap-audit" / "SKILL.md")
    assert fm.get("name") == "coverage-gap-audit"
    assert "version" in fm
