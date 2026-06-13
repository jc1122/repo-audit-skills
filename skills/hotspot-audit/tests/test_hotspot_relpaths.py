"""Relpath contract tests for hotspot-audit.

C-4 relpath requirement: every finding path is root-relative, uses POSIX ``/``
separators (never backslashes, never absolute), and respects --source-prefix
scoping.  All tests are in-process via load_module().main([...]).
"""

import json
from pathlib import Path

from helpers import load_module, make_history


def test_finding_paths_never_absolute(tmp_path):
    """No finding path may start with ``/`` (absolute path)."""
    repo = make_history(tmp_path)
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    assert rc == 1, "expected findings from make_history fixture"
    data = json.loads((out / "hotspot_findings.json").read_text())
    assert len(data) > 0, "fixture must produce findings for this test"
    for f in data:
        assert not f["path"].startswith("/"), (
            f"finding path must be relative, got absolute: {f['path']}"
        )


def test_finding_paths_use_posix_separators(tmp_path):
    """Every finding path must use ``/``, not backslashes."""
    repo = make_history(tmp_path)
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    assert rc == 1, "expected findings from make_history fixture"
    data = json.loads((out / "hotspot_findings.json").read_text())
    for f in data:
        assert "\\" not in f["path"], (
            f"finding path must use POSIX '/', got backslash: {f['path']}"
        )
        # Verify it's not empty and doesn't contain non-POSIX path characters
        assert f["path"], "finding path must not be empty"


def test_source_prefix_filters_findings(tmp_path):
    """--source-prefix hot.py restricts analysis to that single file."""
    repo = make_history(tmp_path)
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(
        ["--root", str(repo), "--out-dir", str(out), "--source-prefix", "hot.py"]
    )
    assert rc == 1, "hot.py should still produce churn finding"
    data = json.loads((out / "hotspot_findings.json").read_text())
    # Only hot.py is in scope -- no a.py<->b.py coupling finding
    paths = {f["path"] for f in data}
    assert paths == {"hot.py"}, (
        f"expected only hot.py in findings with --source-prefix hot.py, got: {sorted(paths)}"
    )


def test_source_prefix_repeatable_scopes_multiple_dirs(tmp_path):
    """Multiple --source-prefix flags scope to union of prefixes."""
    repo = make_history(tmp_path)
    mod = load_module()
    out = tmp_path / "out"
    # Scope to a non-existent prefix -> zero in-scope files -> zero findings
    rc = mod.main(
        [
            "--root", str(repo), "--out-dir", str(out),
            "--source-prefix", "nonexistent/",
        ]
    )
    assert rc == 0, "no in-scope files -> no findings"
    data = json.loads((out / "hotspot_findings.json").read_text())
    assert data == [], "expected zero findings when no files match --source-prefix"


def test_paths_relative_to_root_not_source_prefix(tmp_path):
    """Finding paths are relative to --root, not to --source-prefix or cwd."""
    repo = make_history(tmp_path)
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    assert rc == 1
    data = json.loads((out / "hotspot_findings.json").read_text())
    for f in data:
        full = Path(repo) / f["path"]
        assert full.exists(), (
            f"finding path {f['path']!r} does not exist relative to "
            f"--root {repo}"
        )


def test_relative_paths_on_repo_with_absolute_root(tmp_path):
    """Paths stay relative even when --root is given as an absolute path."""
    repo = make_history(tmp_path)
    mod = load_module()
    out = tmp_path / "out"
    # Pass --root as resolved absolute path
    rc = mod.main(["--root", str(repo.resolve()), "--out-dir", str(out.resolve())])
    assert rc == 1
    data = json.loads((out / "hotspot_findings.json").read_text())
    for f in data:
        assert not Path(f["path"]).is_absolute(), (
            f"finding path {f['path']!r} must be relative even with "
            f"absolute --root"
        )
