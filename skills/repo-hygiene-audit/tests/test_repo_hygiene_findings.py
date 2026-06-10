import json

from helpers import FIXTURES, load_module, make_dirty_repo


def test_golden_findings_match_dirty_repo(tmp_path):
    """Run against make_dirty_repo with max_tracked_file_bytes=1024 and
    compare findings field-by-field against golden_findings.json.

    When ``os.symlink`` is unavailable the broken_symlink fixture is not
    created; the golden entry for it is skipped in that case.
    """
    repo, symlink_ok = make_dirty_repo(tmp_path)
    out = tmp_path / "out"
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"max_tracked_file_bytes": 1024}')

    mod = load_module()
    rc = mod.main(
        ["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)]
    )
    assert rc == 1  # findings present

    actual = json.loads((out / "repo-hygiene_findings.json").read_text())
    golden = json.loads((FIXTURES / "golden_findings.json").read_text())

    # When symlink was not created, filter out the broken_symlink golden entry
    if not symlink_ok:
        golden = [g for g in golden if g["metric"]["name"] != "broken_symlink"]
        actual = [a for a in actual if a["metric"]["name"] != "broken_symlink"]

    assert len(actual) == len(golden), (
        f"count mismatch: {len(actual)} vs {len(golden)}"
    )

    # Compare field-by-field
    for i, (a, g) in enumerate(zip(actual, golden)):
        for key in g:
            assert key in a, f"finding {i}: missing key '{key}'"
            assert a[key] == g[key], (
                f"finding {i}: key '{key}' mismatch: {a[key]!r} != {g[key]!r}"
            )


def test_dirty_repo_finding_signals(tmp_path):
    """Each expected signal group is present in the dirty repo output.
    The broken_symlink signal is only expected when the symlink fixture
    was created successfully."""
    repo, symlink_ok = make_dirty_repo(tmp_path)
    out = tmp_path / "out"
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"max_tracked_file_bytes": 1024}')

    mod = load_module()
    rc = mod.main(
        ["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)]
    )
    assert rc == 1

    data = json.loads((out / "repo-hygiene_findings.json").read_text())
    signal_names = {f["metric"]["name"] for f in data}

    expected = {
        "tracked_artifact",
        "tracked_ignored",
        "tracked_file_bytes",
        "conflicting_configs",
        "version_mismatch",
        "ci_missing",
        "license_missing",
    }
    if symlink_ok:
        expected.add("broken_symlink")
    missing = expected - signal_names
    assert not missing, f"missing signal groups: {missing}"

    # When symlink was not created, assert it is also absent from output
    if not symlink_ok:
        assert "broken_symlink" not in signal_names, (
            "broken_symlink should not appear when os.symlink failed"
        )


def test_clean_repo_yields_no_findings(tmp_path):
    """make_clean_repo produces zero findings."""
    from helpers import make_clean_repo

    repo = make_clean_repo(tmp_path)
    out = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    assert rc == 0
    data = json.loads((out / "repo-hygiene_findings.json").read_text())
    assert data == []
