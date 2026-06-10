"""Docstring-coverage specific tests for docs-consistency-audit."""

from helpers import FIXTURES, load_module, read_findings


def _run(out, root="dirty", config=None):
    mod = load_module()
    args = ["--root", str(FIXTURES / root), "--out-dir", str(out)]
    if config:
        args.extend(["--config", str(config)])
    return mod.main(args)


def test_docstring_group_off_by_default(tmp_path):
    """Docstring group is OFF when docstring_min_percent is None (default)."""
    out = tmp_path / "out"
    _run(out)
    data = read_findings(out)
    ds = [f for f in data if f["metric"]["name"] == "docstring_percent"]
    assert ds == []


def test_docstring_clean_passes(tmp_path):
    """Clean fixture (all documented) passes with docstring_min_percent=80."""
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"docstring_min_percent": 80}')
    out = tmp_path / "out"
    _run(out, root="clean", config=cfg)
    data = read_findings(out)
    ds = [f for f in data if f["metric"]["name"] == "docstring_percent"]
    assert ds == []


def test_docstring_dirty_fails(tmp_path):
    """Dirty fixture (1/3 documented) fails with docstring_min_percent=80."""
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"docstring_min_percent": 80}')
    out = tmp_path / "out"
    rc = _run(out, config=cfg)
    assert rc == 1
    data = read_findings(out)
    ds = [f for f in data if f["metric"]["name"] == "docstring_percent"]
    assert len(ds) == 1
    assert ds[0]["metric"]["value"] == 33.3
    assert ds[0]["metric"]["threshold"] == 80.0


def test_docstring_no_public_symbols_skipped(tmp_path):
    """Module with 0 public symbols is skipped (no finding)."""
    import os
    root = tmp_path / "tree"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "mod.py").write_text("def _private():\n    pass\n")
    # No public symbols → should be skipped entirely
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"docstring_min_percent": 80}')
    out = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(root), "--out-dir", str(out), "--config", str(cfg)])
    assert rc == 0
    data = read_findings(out)
    ds = [f for f in data if f["metric"]["name"] == "docstring_percent"]
    assert ds == []


def test_docstring_module_fully_documented(tmp_path):
    """Module with all public symbols documented → no finding."""
    root = tmp_path / "tree"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "mod.py").write_text(
        'def f1():\n    """doc"""\n    pass\n'
        'def f2():\n    """doc"""\n    pass\n'
    )
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"docstring_min_percent": 80}')
    out = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(root), "--out-dir", str(out), "--config", str(cfg)])
    assert rc == 0
    data = read_findings(out)
    ds = [f for f in data if f["metric"]["name"] == "docstring_percent"]
    assert ds == []
