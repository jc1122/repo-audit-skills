"""Regression tests for hotspot-audit precision suppressions."""

import json

from helpers import _g, load_module, make_history, read_findings


def _write_config(tmp_path, thresholds):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps(thresholds))
    return cfg


def _make_solo_author_repo(tmp_path):
    repo = tmp_path / "solo"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")
    for i in range(3):
        (repo / "owned.py").write_text(f"value = {i}\n")
        _g(repo, "add", "-A")
        _g(repo, "commit", "-q", "-m", f"solo-{i}")
    return repo


def _make_own_test_pair_repo(tmp_path):
    repo = tmp_path / "pairs"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")
    (repo / "tests").mkdir()

    for i in range(5):
        (repo / "foo.py").write_text(f"foo = {i}\n")
        (repo / "tests" / "test_foo.py").write_text(f"test_foo = {i}\n")
        _g(repo, "add", "-A")
        _g(repo, "commit", "-q", "-m", f"own-test-{i}")

    for i in range(5):
        (repo / "a.py").write_text(f"a = {i}\n")
        (repo / "b.py").write_text(f"b = {i}\n")
        _g(repo, "add", "-A")
        _g(repo, "commit", "-q", "-m", f"coupled-{i}")

    return repo


def test_solo_author_repo_suppresses_author_concentration(tmp_path, capsys):
    repo = _make_solo_author_repo(tmp_path)
    cfg = _write_config(tmp_path, {"min_author_commits": 2})
    out = tmp_path / "out"
    mod = load_module()

    rc = mod.main(["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)])

    assert rc == 0
    findings = read_findings(out)
    assert [f for f in findings if f["metric"]["name"] == "author_concentration"] == []
    status = json.loads(capsys.readouterr().out.strip())
    assert status["suppressed_solo_author"] is True


def test_two_author_fixture_keeps_author_concentration_findings(tmp_path, capsys):
    repo = make_history(tmp_path)
    cfg = _write_config(tmp_path, {"min_author_commits": 5})
    out = tmp_path / "out"
    mod = load_module()

    rc = mod.main(["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)])

    assert rc == 1
    findings = read_findings(out)
    concentration = [
        f for f in findings if f["metric"]["name"] == "author_concentration"
    ]
    assert [f["path"] for f in concentration] == ["a.py", "hot.py"]
    status = json.loads(capsys.readouterr().out.strip())
    assert status["suppressed_solo_author"] is False


def test_own_test_pair_is_suppressed_but_unrelated_pair_still_fires(tmp_path, capsys):
    repo = _make_own_test_pair_repo(tmp_path)
    out = tmp_path / "out"
    mod = load_module()

    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])

    assert rc == 1
    findings = read_findings(out)
    symbols = [
        f["location"]["symbol"]
        for f in findings
        if f["metric"]["name"] == "temporal_coupling_ratio"
    ]
    assert "foo.py<->tests/test_foo.py" not in symbols
    assert "a.py<->b.py" in symbols
    status = json.loads(capsys.readouterr().out.strip())
    assert status["suppressed_own_test_pairs"] == 1
