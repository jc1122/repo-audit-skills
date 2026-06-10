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
