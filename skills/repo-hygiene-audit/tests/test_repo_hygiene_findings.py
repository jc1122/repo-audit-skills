import json
from pathlib import Path

from helpers import FIXTURES, load_module, make_dirty_repo


def test_golden_findings_match_dirty_repo(tmp_path):
    """Run against make_dirty_repo with max_tracked_file_bytes=1024 and
    compare findings field-by-field against golden_findings.json."""
    repo = make_dirty_repo(tmp_path)
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
    """Each expected signal group is present in the dirty repo output."""
    repo = make_dirty_repo(tmp_path)
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
        "broken_symlink",
        "conflicting_configs",
        "version_mismatch",
        "ci_missing",
        "license_missing",
    }
    missing = expected - signal_names
    assert not missing, f"missing signal groups: {missing}"


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
