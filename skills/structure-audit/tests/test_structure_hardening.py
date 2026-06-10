from helpers import load_module


def test_syntax_error_file_is_skipped_not_raised(tmp_path):
    sa = load_module()
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "ok.py").write_text("import os\n")
    (pkg / "bad.py").write_text("def broken(:\n    return\n")
    findings = sa.analyze_tree(str(tmp_path), ["pkg"], dict(sa.DEFAULT_THRESHOLDS))
    assert isinstance(findings, list)
