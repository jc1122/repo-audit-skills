from helpers import FIXTURES, load_module

ps = load_module()


def test_clean_fixture_yields_no_findings():
    findings = ps.analyze_tree(FIXTURES / "clean", source_prefixes=["pkg/"])
    assert findings == []


def test_dirty_fixture_flags_perf_smells():
    findings = ps.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"])
    assert findings, "expected at least one perf smell"
    assert all(f.signal == "PERF" for f in findings)
    assert all(f.evidence_tool == "perflint" for f in findings)
    assert all(f.path.endswith("dirty.py") for f in findings)
    # every finding records the perflint message id as its metric name
    assert all(f.metric_name for f in findings)


def test_missing_tool_raises_tool_error_not_silent_clean(monkeypatch):
    # a missing pylint must be a hard error (EXIT_ERROR), never zero findings
    def _boom(*a, **k):
        raise FileNotFoundError("pylint")

    monkeypatch.setattr(ps.subprocess, "run", _boom)
    import pytest
    with pytest.raises(ps.ToolError):
        ps.analyze_tree(FIXTURES / "dirty", source_prefixes=["pkg/"])


def test_main_returns_exit_error_on_tool_error(monkeypatch, tmp_path):
    def _raise(*a, **k):
        raise ps.ToolError("pylint is not installed")

    monkeypatch.setattr(ps, "analyze_tree", _raise)
    rc = ps.main(["--root", str(FIXTURES / "dirty"), "--source-prefix", "pkg/",
                  "--out-dir", str(tmp_path)])
    assert rc == ps.hc.EXIT_ERROR
