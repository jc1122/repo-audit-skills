import json

from helpers import FIXTURES, load_module, read_findings


def test_advisory_emits_security(tmp_path):
    mod = load_module()
    out_dir = tmp_path / "out"
    rc = mod.main(
        [
            "--root", str(FIXTURES / "clean"),
            "--out-dir", str(out_dir),
            "--advisory-report", str(FIXTURES / "advisory.json"),
        ]
    )
    assert rc == 1
    produced = read_findings(out_dir)
    golden = json.loads((FIXTURES / "golden_advisory_findings.json").read_text())
    assert produced == golden
    assert produced[0]["signal"] == "SECURITY"
    assert produced[0]["evidence"]["tool"] == "advisory-report"
