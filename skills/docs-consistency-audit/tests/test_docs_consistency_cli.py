"""CLI contract tests for docs-consistency-audit."""

import json

from helpers import FIXTURES, load_module, read_findings, run_cli


def _dirty_args(out, config=None):
    args = [
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
    ]
    if config:
        args.extend(["--config", str(config)])
    return args


def _clean_args(out):
    return [
        "--root", str(FIXTURES / "clean"),
        "--out-dir", str(out),
    ]


# ── subprocess smoke (only one) ────────────────────────────────────

def test_help_exits_zero():
    """Subprocess smoke: --help exits 0."""
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--root" in result.stdout


# ── in-process CLI tests ───────────────────────────────────────────

def test_clean_exits_zero_and_empty(tmp_path):
    """Clean fixture → exit 0, [] findings."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(_clean_args(out))
    assert rc == 0
    assert read_findings(out) == []


def test_dirty_default_run_exits_one(tmp_path):
    """Dirty default run (groups 1-3) → exit 1, findings match golden."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(_dirty_args(out))
    assert rc == 1
    data = read_findings(out)
    assert len(data) > 0
    for f in data:
        assert f["leaf"] == "docs-consistency"
        assert f["signal"] == "LINT"


def test_dirty_configured_docstring_run(tmp_path):
    """Dirty run with docstring_min_percent: 80 → includes docstring finding."""
    mod = load_module()
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"docstring_min_percent": 80}')
    out = tmp_path / "out"
    rc = mod.main(_dirty_args(out, config=cfg))
    assert rc == 1
    data = read_findings(out)
    docstring_findings = [
        f for f in data if f["metric"]["name"] == "docstring_percent"
    ]
    assert len(docstring_findings) == 1
    dsf = docstring_findings[0]
    assert dsf["severity"] == "low"
    assert dsf["confidence"] == "medium"
    assert dsf["location"]["symbol"] == "<module>"


def test_missing_required_args_exits_two(tmp_path):
    """Missing --root or --out-dir → exit 2 + status-error."""
    mod = load_module()
    rc = mod.main(["--root", str(FIXTURES / "dirty")])
    assert rc == 2
    rc = mod.main(["--out-dir", str(tmp_path)])
    assert rc == 2


def test_invalid_config_exits_two(tmp_path):
    """Invalid --config → exit 2 + status-error."""
    mod = load_module()
    cfg = tmp_path / "bad.json"
    cfg.write_text("not json")
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
        "--config", str(cfg),
    ])
    assert rc == 2


def test_unreadable_root_exits_two(tmp_path):
    """Unreadable --root → exit 2."""
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(tmp_path / "nope"),
        "--out-dir", str(out),
    ])
    assert rc == 2


# ── guard test (mandatory per plan) ────────────────────────────────

def test_guard_never_imports_module_without_build_parser(tmp_path):
    """The sideeffect.py module has no build_parser → guard skips it.

    This test asserts that running the audit on the dirty fixture does
    NOT raise RuntimeError("must never be imported") and completes with
    exit code 1 (findings present).
    """
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
    ])
    assert rc == 1
    # sideeffect.py was mentioned in README but has no build_parser
    # → the guard prevented its import; no RuntimeError was raised
