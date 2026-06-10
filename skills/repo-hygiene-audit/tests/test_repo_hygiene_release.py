import json

from helpers import _g, load_module


def test_conflicting_pytest_configs(tmp_path):
    """pytest.ini + pyproject.toml [tool.pytest.ini_options] → conflicting_configs."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")

    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "pyproject.toml").write_text(
        '[project]\nversion = "1.0.0"\n\n[tool.pytest.ini_options]\n'
    )
    (repo / "LICENSE").write_text("MIT\n")
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "check.yml").write_text("name: check\n")
    (repo / "CHANGELOG.md").write_text("## 1.0.0\n")

    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "init")

    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    data = json.loads((out / "repo-hygiene_findings.json").read_text())

    conflicting = [f for f in data if f["metric"]["name"] == "conflicting_configs"]
    assert len(conflicting) == 1
    c = conflicting[0]
    assert c["signal"] == "RESTRUCTURE"
    assert c["severity"] == "medium"
    assert c["confidence"] == "high"
    assert c["location"]["symbol"] == "pytest-config"
    assert c["metric"]["value"] == 2.0
    assert c["metric"]["threshold"] == 1.0


def test_version_mismatch_detected(tmp_path):
    """pyproject.toml version != CHANGELOG first heading → version_mismatch."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")

    (repo / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n')
    (repo / "CHANGELOG.md").write_text("## 1.1.0\n\nRelease notes.\n")
    (repo / "LICENSE").write_text("MIT\n")
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "check.yml").write_text("name: check\n")

    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "init")

    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    data = json.loads((out / "repo-hygiene_findings.json").read_text())

    mismatches = [f for f in data if f["metric"]["name"] == "version_mismatch"]
    assert len(mismatches) == 1
    m = mismatches[0]
    assert m["signal"] == "RESTRUCTURE"
    assert m["severity"] == "medium"
    assert m["confidence"] == "high"
    assert m["location"]["symbol"] == "version"
    assert m["metric"]["value"] == 2.0  # two distinct versions
    assert m["metric"]["threshold"] == 1.0
    # Evidence should list both sources
    assert "1.0.0" in m["evidence"]["raw"]
    assert "1.1.0" in m["evidence"]["raw"]


def test_missing_ci_detected(tmp_path):
    """No .github/workflows/*.yml|yaml → ci_missing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")

    (repo / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n')
    (repo / "CHANGELOG.md").write_text("## 1.0.0\n")
    (repo / "LICENSE").write_text("MIT\n")

    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "init")

    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    data = json.loads((out / "repo-hygiene_findings.json").read_text())

    ci = [f for f in data if f["metric"]["name"] == "ci_missing"]
    assert len(ci) == 1
    c = ci[0]
    assert c["signal"] == "RESTRUCTURE"
    assert c["severity"] == "low"
    assert c["confidence"] == "high"
    assert c["location"]["symbol"] == "<ci>"
    assert c["path"] == ".github"


def test_missing_license_detected(tmp_path):
    """No root LICENSE* → license_missing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")

    (repo / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n')
    (repo / "CHANGELOG.md").write_text("## 1.0.0\n")
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "check.yml").write_text("name: check\n")

    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "init")

    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    data = json.loads((out / "repo-hygiene_findings.json").read_text())

    lic = [f for f in data if f["metric"]["name"] == "license_missing"]
    assert len(lic) == 1
    l = lic[0]
    assert l["signal"] == "RESTRUCTURE"
    assert l["severity"] == "low"
    assert l["confidence"] == "high"
    assert l["location"]["symbol"] == "<license>"
    assert l["path"] == "LICENSE"


def test_prefixed_run_on_own_repo_shape_is_clean(tmp_path):
    """Own-repo-shape fixture under --source-prefix filtering yields NO findings."""
    from helpers import make_prefixed_own_repo_shape

    repo = make_prefixed_own_repo_shape(tmp_path)
    out = tmp_path / "out"

    mod = load_module()
    rc = mod.main([
        "--root", str(repo),
        "--out-dir", str(out),
        "--source-prefix", "shared",
        "--source-prefix", "scripts",
        "--source-prefix", "skills/foo/scripts",
    ])
    assert rc == 0, f"expected exit 0, got {rc}"
    data = json.loads((out / "repo-hygiene_findings.json").read_text())
    assert data == [], f"expected no findings, got {data}"
