"""Finding-level assertions for docs-consistency-audit.

Verifies each finding group individually against the committed fixtures.
"""

import json

from helpers import FIXTURES, load_module, read_findings


def _run_dirty(out, config=None):
    mod = load_module()
    args = ["--root", str(FIXTURES / "dirty"), "--out-dir", str(out)]
    if config:
        args.extend(["--config", str(config)])
    return mod.main(args)


# ── group 1: unknown flags in documented commands ──────────────────

def test_finding_doc_flag_unknown(tmp_path):
    """Group 1: unknown flag in fenced bash block → doc_flag_unknown finding."""
    out = tmp_path / "out"
    _run_dirty(out)
    data = read_findings(out)
    flags = [f for f in data if f["metric"]["name"] == "doc_flag_unknown"]
    assert len(flags) == 1
    f = flags[0]
    assert f["leaf"] == "docs-consistency"
    assert f["signal"] == "LINT"
    assert f["severity"] == "medium"
    assert f["confidence"] == "medium"
    assert f["path"] == "README.md"
    assert f["location"]["symbol"] == "tools/cli.py"
    assert f["evidence"]["tool"] == "argparse"
    assert "--no-such-flag" in f["evidence"]["raw"]


# ── group 2: dead doc paths ────────────────────────────────────────

def test_finding_doc_path_missing(tmp_path):
    """Group 2: inline code span referencing nonexistent file → doc_path_missing."""
    out = tmp_path / "out"
    _run_dirty(out)
    data = read_findings(out)
    paths = [f for f in data if f["metric"]["name"] == "doc_path_missing"]
    assert len(paths) == 1
    f = paths[0]
    assert f["leaf"] == "docs-consistency"
    assert f["signal"] == "LINT"
    assert f["severity"] == "low"
    assert f["location"]["symbol"] == "missing/file.py"
    assert f["path"] == "README.md"


# ── group 3: stale version pins ────────────────────────────────────

def test_finding_doc_version_stale(tmp_path):
    """Group 3: stale version pin (9.9.9 vs 1.0.0) → doc_version_stale."""
    out = tmp_path / "out"
    _run_dirty(out)
    data = read_findings(out)
    versions = [f for f in data if f["metric"]["name"] == "doc_version_stale"]
    assert len(versions) == 1
    f = versions[0]
    assert f["leaf"] == "docs-consistency"
    assert f["signal"] == "LINT"
    assert f["severity"] == "medium"
    assert f["confidence"] == "high"
    assert f["evidence"]["raw"] == "found mypkg==9.9.9, current version is 1.0.0"
    assert "9.9.9" in f["evidence"]["raw"]
    assert "1.0.0" in f["evidence"]["raw"]


# ── group 4: docstring coverage (configured) ───────────────────────

def test_finding_docstring_percent_configured(tmp_path):
    """Group 4: docstring_min_percent=80 with 1/3 documented → finding."""
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"docstring_min_percent": 80}')
    out = tmp_path / "out"
    _run_dirty(out, config=cfg)
    data = read_findings(out)
    ds = [f for f in data if f["metric"]["name"] == "docstring_percent"]
    assert len(ds) == 1
    f = ds[0]
    assert f["leaf"] == "docs-consistency"
    assert f["signal"] == "LINT"
    assert f["severity"] == "low"
    assert f["confidence"] == "medium"
    assert f["path"] == "pkg/mod.py"
    assert f["location"]["symbol"] == "<module>"
    assert f["metric"]["value"] == 33.3
    assert f["metric"]["threshold"] == 80.0


# ── group 3: CHANGELOG*.md exclusion ───────────────────────────────

def test_changelog_excluded_from_version_checks(tmp_path):
    """Stale version pins in CHANGELOG*.md are excluded from checks."""
    import os
    root = tmp_path / "tree"
    root.mkdir()
    # Package metadata with current version
    (root / "pyproject.toml").write_text(
        '[project]\nname = "mypkg"\nversion = "1.0.0"\n'
    )
    # CHANGELOG.md with stale version -- must be excluded
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## 1.0.0\n\nUpgrade with `pip install mypkg==9.9.9`.\n"
    )
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(root), "--out-dir", str(out)])
    # CHANGELOG.md is excluded; no version stale finding should appear
    data = read_findings(out)
    versions = [f for f in data if f["metric"]["name"] == "doc_version_stale"]
    assert versions == [], (
        f"CHANGELOG.md should be excluded, got {versions}"
    )


def test_changelog_exclusion_readme_still_checked(tmp_path):
    """Stale version pins in README.md are still flagged."""
    root = tmp_path / "tree"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "mypkg"\nversion = "1.0.0"\n'
    )
    (root / "README.md").write_text(
        "# Readme\n\nInstall: `pip install mypkg==9.9.9`\n"
    )
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(root), "--out-dir", str(out)])
    data = read_findings(out)
    versions = [f for f in data if f["metric"]["name"] == "doc_version_stale"]
    assert len(versions) == 1, (
        f"README.md should be checked, got {len(versions)} findings"
    )
    assert versions[0]["path"] == "README.md"


# ── source-prefix filtering ────────────────────────────────────────

def test_source_prefix_filters_markdown_findings(tmp_path):
    """--source-prefix limits scans to files under the prefix.

    A tree with a dirty README.md inside pkg/ and an identically dirty
    README.md at the root: when --source-prefix pkg/ is used, the root
    README.md is out of scope and must not produce findings.
    """
    root = tmp_path / "tree"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    dirty_md = (
        "# Pkg\n\n"
        "```bash\n"
        "python3 tools/cli.py --root . --no-such-flag\n"
        "pip install mypkg==9.9.9\n"
        "```\n\n"
        "See `missing/file.py`.\n"
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname = "mypkg"\nversion = "1.0.0"\n'
    )
    (root / "README.md").write_text(dirty_md)
    (pkg / "README.md").write_text(dirty_md)
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(root),
        "--source-prefix", "pkg/",
        "--out-dir", str(out),
    ])
    # Only pkg/README.md is in scope; findings should all reference pkg/
    data = read_findings(out)
    assert len(data) > 0, "expected findings from in-prefix file"
    for f in data:
        assert f["path"].startswith("pkg/"), (
            f"finding outside prefix: {f['path']}"
        )


def test_source_prefix_excludes_out_of_prefix_content(tmp_path):
    """Out-of-prefix content produces no findings when prefix is set."""
    root = tmp_path / "tree"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "mypkg"\nversion = "1.0.0"\n'
    )
    (root / "README.md").write_text(
        "# Root\n\n"
        "```bash\n"
        "python3 tools/cli.py --root . --no-such-flag\n"
        "pip install mypkg==9.9.9\n"
        "```\n\n"
        "See `missing/file.py`.\n"
    )
    mod = load_module()
    out = tmp_path / "out"
    # Use a prefix that matches nothing
    rc = mod.main([
        "--root", str(root),
        "--source-prefix", "src/",
        "--out-dir", str(out),
    ])
    # No files in scope -> no findings
    data = read_findings(out)
    assert data == [], f"expected no findings, got {len(data)}"


# ── golden comparison (field-by-field) ─────────────────────────────

def test_default_golden_matches(tmp_path):
    """Default dirty run matches golden_findings.json field-by-field."""
    out = tmp_path / "out"
    _run_dirty(out)
    actual = read_findings(out)
    expected = json.loads(
        (FIXTURES / "golden_findings.json").read_text()
    )
    assert len(actual) == len(expected)
    for a, e in zip(actual, expected):
        assert a == e, f"mismatch at finding:\n  actual: {a}\n  expected: {e}"


def test_configured_golden_matches(tmp_path):
    """Configured docstring run matches golden_findings_docstrings.json field-by-field."""
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"docstring_min_percent": 80}')
    out = tmp_path / "out"
    _run_dirty(out, config=cfg)
    actual = read_findings(out)
    expected = json.loads(
        (FIXTURES / "golden_findings_docstrings.json").read_text()
    )
    assert len(actual) == len(expected)
    for a, e in zip(actual, expected):
        assert a == e, f"mismatch at finding:\n  actual: {a}\n  expected: {e}"
