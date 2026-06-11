"""Config-driven hotspot precision policy for family repositories."""

import json

from helpers import _g, load_module, read_findings


def _write_config(tmp_path, config):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps(config))
    return cfg


def _temporal_symbols(findings):
    return [
        f["location"]["symbol"]
        for f in findings
        if f["metric"]["name"] == "temporal_coupling_ratio"
    ]


def _author_paths(findings):
    return [
        f["path"]
        for f in findings
        if f["metric"]["name"] == "author_concentration"
    ]


def _make_family_repo(tmp_path):
    repo = tmp_path / "family"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")
    (repo / "references").mkdir()

    for i in range(5):
        (repo / "SKILL.md").write_text(f"# Skill\n\nrev {i}\n")
        (repo / "references" / "usage.md").write_text(f"usage {i}\n")
        _g(repo, "add", "-A")
        _g(repo, "commit", "-q", "-m", f"docs-{i}")

    for i in range(5):
        (repo / "a.py").write_text(f"a = {i}\n")
        (repo / "b.py").write_text(f"b = {i}\n")
        _g(repo, "add", "-A")
        _g(repo, "commit", "-q", "-m", f"coupled-{i}")

    (repo / "note.md").write_text("bob touched this\n")
    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "bob-touch", author="bob")
    return repo


def _make_churn_repo(tmp_path):
    repo = tmp_path / "churn"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")

    for i in range(5):
        (repo / "hot.py").write_text(
            "\n".join(f"x{j} = {j}  # rev {i}" for j in range(250)) + "\n"
        )
        _g(repo, "add", "-A")
        _g(repo, "commit", "-q", "-m", f"hot-{i}")

    (repo / "note.md").write_text("bob touched this\n")
    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "bob-touch", author="bob")
    return repo


def test_declared_coupling_pair_is_suppressed_and_counted(tmp_path, capsys):
    repo = _make_family_repo(tmp_path)
    cfg = _write_config(
        tmp_path,
        {"coupling_allow_pairs": [["SKILL.md", "references/**"]]},
    )
    out = tmp_path / "out"
    mod = load_module()

    rc = mod.main(["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)])

    assert rc == 1
    findings = read_findings(out)
    symbols = _temporal_symbols(findings)
    assert "SKILL.md<->references/usage.md" not in symbols
    assert "a.py<->b.py" in symbols
    status = json.loads(capsys.readouterr().out.strip())
    assert status["suppression_counts"]["declared_coupling"] == 1
    report = (out / "hotspot_report.md").read_text()
    assert "`declared_coupling`=1" in report


def test_undeclared_coupling_still_fires_under_same_config(tmp_path):
    repo = _make_family_repo(tmp_path)
    cfg = _write_config(
        tmp_path,
        {"coupling_allow_pairs": [["SKILL.md", "references/**"]]},
    )
    out = tmp_path / "out"
    mod = load_module()

    rc = mod.main(["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)])

    assert rc == 1
    assert "a.py<->b.py" in _temporal_symbols(read_findings(out))


def test_single_maintainer_suppresses_author_concentration_and_counts(tmp_path, capsys):
    repo = _make_family_repo(tmp_path)
    cfg = _write_config(
        tmp_path,
        {"min_author_commits": 5, "single_maintainer": True},
    )
    out = tmp_path / "out"
    mod = load_module()

    rc = mod.main(["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)])

    assert rc == 1
    assert _author_paths(read_findings(out)) == []
    status = json.loads(capsys.readouterr().out.strip())
    assert status["suppression_counts"]["single_maintainer"] == 4
    report = (out / "hotspot_report.md").read_text()
    assert "`single_maintainer`=4" in report


def test_policy_absent_keeps_declared_coupling_and_author_findings(tmp_path, capsys):
    repo = _make_family_repo(tmp_path)
    cfg = _write_config(tmp_path, {"min_author_commits": 5})
    out = tmp_path / "out"
    mod = load_module()

    rc = mod.main(["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)])

    assert rc == 1
    findings = read_findings(out)
    symbols = _temporal_symbols(findings)
    assert "SKILL.md<->references/usage.md" in symbols
    assert "a.py<->b.py" in symbols
    assert _author_paths(findings) == [
        "SKILL.md",
        "a.py",
        "b.py",
        "references/usage.md",
    ]
    status = json.loads(capsys.readouterr().out.strip())
    assert status["suppression_counts"]["declared_coupling"] == 0
    assert status["suppression_counts"]["single_maintainer"] == 0


def test_churn_complexity_is_not_suppressed_by_family_policy(tmp_path):
    repo = _make_churn_repo(tmp_path)
    cfg = _write_config(
        tmp_path,
        {
            "coupling_allow_pairs": [["hot.py", "references/**"]],
            "single_maintainer": True,
        },
    )
    out = tmp_path / "out"
    mod = load_module()

    rc = mod.main(["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)])

    assert rc == 1
    churn = [
        f for f in read_findings(out) if f["metric"]["name"] == "churn_complexity_product"
    ]
    assert [f["path"] for f in churn] == ["hot.py"]
