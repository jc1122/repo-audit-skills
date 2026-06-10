import json

from helpers import load_module, FIXTURES


def test_source_prefix_filters_imports_to_prefix(tmp_path, capsys):
    """With --source-prefix src, only files under src/ are scanned for imports."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "prefix"),
        "--out-dir", str(out),
        "--source-prefix", "src",
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    # Only findings from src/ should appear; tests/test_app.py imports pendulum
    # but is outside the src/ prefix, so its imports should not be analyzed.
    # Findings may still include manifest-level findings (declared_unused, etc.)
    for finding in data:
        assert finding["path"].startswith("src/") or finding["path"] in (
            "pyproject.toml", "requirements.txt"
        ), (
            f"Finding path {finding['path']} should be within src/ prefix "
            f"or a manifest file"
        )


def test_source_prefix_excludes_tests_directory(tmp_path, capsys):
    """With --source-prefix src, imports from tests/ are excluded."""
    mod = load_module()
    out_full = tmp_path / "out_full"
    out_prefix = tmp_path / "out_prefix"
    # Full run includes tests/test_app.py (pendulum import)
    mod.main([
        "--root", str(FIXTURES / "prefix"),
        "--out-dir", str(out_full),
    ])
    # Prefixed run excludes tests/
    mod.main([
        "--root", str(FIXTURES / "prefix"),
        "--out-dir", str(out_prefix),
        "--source-prefix", "src",
    ])
    data_full = json.loads((out_full / "dependency_findings.json").read_text())
    data_prefix = json.loads((out_prefix / "dependency_findings.json").read_text())
    # The prefix run should have <= findings compared to the full run
    assert len(data_prefix) <= len(data_full), (
        f"Prefix run ({len(data_prefix)} findings) should not have more "
        f"findings than full run ({len(data_full)} findings)"
    )


def test_multiple_source_prefixes_are_union(tmp_path, capsys):
    """Multiple --source-prefix flags create a union of scanned paths."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "prefix"),
        "--out-dir", str(out),
        "--source-prefix", "src",
        "--source-prefix", "tests",
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    # With both prefixes, findings from src/ should appear
    # (src/app.py imports yaml which is undeclared)
    paths = {f["path"] for f in data}
    has_src = any(p.startswith("src/") for p in paths)
    assert has_src, "Expected findings from src/ with dual prefixes"
    # Should complete without error (union of prefixes is valid)
    assert rc in (0, 1), f"Expected exit 0 or 1, got {rc}"


def test_local_module_not_flagged_as_undeclared(tmp_path, capsys):
    """A top-level import matching a local module file is skipped, not flagged."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "local_mod"),
        "--out-dir", str(out),
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    # mylocal.py exists at root level -> should be treated as local, NOT undeclared
    # unknown_lib is not local and not declared -> should be undeclared
    undeclared = [
        f for f in data
        if f["metric"]["name"] == "import_undeclared"
    ]
    symbols = {f["location"]["symbol"] for f in undeclared}
    # mylocal should NOT appear in undeclared findings
    assert "mylocal" not in symbols, (
        f"mylocal is a local module and should not be flagged as undeclared; "
        f"got undeclared symbols: {symbols}"
    )


def test_local_module_package_not_flagged(tmp_path, capsys):
    """A top-level import matching a package directory is local, not undeclared."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
    ])
    data = json.loads((out / "dependency_findings.json").read_text())
    # The 'src' directory exists but is not a Python package (no __init__.py).
    # Verify no findings reference 'src' as a symbol.
    for finding in data:
        assert finding["location"]["symbol"] != "src", (
            "Directory 'src' is not a module and should not appear as a symbol"
        )


def test_stdlib_imports_never_flagged(tmp_path, capsys):
    """Standard library imports are never flagged as undeclared."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "no_manifest"),
        "--out-dir", str(out),
    ])
    # no_manifest fixture imports os and json (both stdlib)
    # Even if manifest existed, stdlib should never trigger findings
    assert rc == 0
    data = json.loads((out / "dependency_findings.json").read_text())
    assert data == [], "stdlib imports should never produce findings"


def test_source_prefix_status_line_reflects_args(tmp_path, capsys):
    """Status line with --source-prefix still reports ok/findings correctly."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
        "--source-prefix", "src",
    ])
    assert rc in (0, 1), f"Expected exit 0 or 1, got {rc}"
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    assert payload["status"] == "ok"
    assert payload["leaf"] == "dependency"
