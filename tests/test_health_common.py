import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("health_common", ROOT / "shared" / "health_common.py")
hc = importlib.util.module_from_spec(SPEC)
sys.modules["health_common"] = hc
SPEC.loader.exec_module(hc)


def make(**kw):
    base = dict(
        leaf="complexity", signal="DECOMPOSE", severity="high",
        path="pkg/a.py", line_start=10, line_end=40, symbol="f",
        metric_name="cyclomatic_complexity", metric_value=22.0, metric_threshold=10.0,
        evidence_tool="lizard", evidence_raw="f cc=22", confidence="high",
        suggested_action="Split f()",
    )
    base.update(kw)
    return hc.Finding(**base)


def test_stable_id_is_deterministic_and_short():
    f = make()
    assert f.stable_id() == make().stable_id()
    assert len(f.stable_id()) == 16


def test_stable_id_changes_with_identity_fields():
    assert make(symbol="f").stable_id() != make(symbol="g").stable_id()


def test_to_dict_shape():
    d = make().to_dict()
    assert d["id"] == make().stable_id()
    assert d["location"] == {"line_start": 10, "line_end": 40, "symbol": "f"}
    assert d["metric"] == {"name": "cyclomatic_complexity", "value": 22.0, "threshold": 10.0}
    assert d["evidence"] == {"tool": "lizard", "raw": "f cc=22"}


def test_sort_is_stable_by_path_line_signal_metric():
    a = make(path="pkg/a.py", line_start=5)
    b = make(path="pkg/a.py", line_start=1)
    c = make(path="pkg/b.py", line_start=1)
    assert hc.sort_findings([c, a, b]) == [b, a, c]


def test_write_findings_is_byte_stable(tmp_path):
    fs = [make(symbol="g"), make(symbol="f")]
    hc.write_findings(fs, tmp_path, "complexity")
    out = (tmp_path / "complexity_findings.json").read_bytes()
    hc.write_findings(list(reversed(fs)), tmp_path, "complexity")
    assert (tmp_path / "complexity_findings.json").read_bytes() == out
    data = json.loads(out)
    assert [d["location"]["symbol"] for d in data] == ["f", "g"]


def test_exit_code_constants():
    assert (hc.EXIT_CLEAN, hc.EXIT_FINDINGS, hc.EXIT_ERROR) == (0, 1, 2)


def test_test_signal_is_in_schema():
    assert "TEST" in hc.SIGNALS


def test_perf_and_security_signals_in_schema():
    assert "PERF" in hc.SIGNALS
    assert "SECURITY" in hc.SIGNALS
