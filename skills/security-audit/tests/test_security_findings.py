import importlib.util
import json
from pathlib import Path

from helpers import FIXTURES, SKILL_ROOT, load_module, read_findings


def test_dirty_fixture_matches_golden(tmp_path):
    mod = load_module()
    out_dir = tmp_path / "out"
    rc = mod.main(["--root", str(FIXTURES / "dirty"), "--out-dir", str(out_dir)])
    assert rc == 1
    produced = read_findings(out_dir)
    golden = json.loads((FIXTURES / "golden_findings.json").read_text())
    assert produced == golden
    assert all(f["signal"] == "SECURITY" for f in produced)


def test_vendored_signals_include_security():
    import sys

    spec = importlib.util.spec_from_file_location(
        "_vendored_hc", SKILL_ROOT / "scripts" / "health_common.py"
    )
    hc = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = hc
    spec.loader.exec_module(hc)
    assert {"PERF", "SECURITY"} <= hc.SIGNALS
