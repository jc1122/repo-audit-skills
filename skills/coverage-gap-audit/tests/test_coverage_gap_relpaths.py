import json

from helpers import run_cli, read_findings


def test_absolute_report_paths_are_emitted_relative(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "m.py").write_text("def f():\n    return 1\n")
    report = {
        "files": {
            str(pkg / "m.py"): {
                "executed_lines": [1],
                "summary": {"num_statements": 2},
            }
        }
    }
    (tmp_path / "cov.json").write_text(json.dumps(report))
    out = tmp_path / "out"
    run_cli(
        "--root", str(tmp_path), "--source-prefix", "pkg/",
        "--coverage-json", str(tmp_path / "cov.json"), "--out-dir", str(out),
    )
    data = read_findings(out)
    assert data, "expected a partial-coverage finding"
    assert all(not f["path"].startswith("/") for f in data), [f["path"] for f in data]
