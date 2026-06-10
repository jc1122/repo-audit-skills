import json

from helpers import load_module, FIXTURES


def test_dirty_with_advisory_matches_golden(tmp_path, capsys):
    """Dirty fixture + advisory report produces the golden advisory findings."""
    mod = load_module()
    out = tmp_path / "out"
    adv = FIXTURES / "advisory.json"
    rc = mod.main([
        "--root", str(FIXTURES / "dirty"),
        "--out-dir", str(out),
        "--advisory-report", str(adv),
    ])
    assert rc == 1
    data = json.loads((out / "dependency_findings.json").read_text())
    golden = json.loads((FIXTURES / "golden_advisory_findings.json").read_text())
    assert data == golden
