import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_coverage_gap.py"


def _module():
    spec = importlib.util.spec_from_file_location("check_coverage_gap", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _snapshot_data() -> list[dict[str, str]]:
    return [
        {"path": "scripts/self_audit.py", "metric": "file_coverage_percent"},
        {"path": "scripts/check_coverage_gap.py", "metric": "file_coverage_percent"},
    ]


def _write(path: Path, payload: list[dict[str, str]]) -> None:
    path.write_text(json.dumps(payload))


def _run(mod, snapshot, baseline, capsys):
    rc = mod.main(["--snapshot", str(snapshot), "--baseline", str(baseline)])
    payload = json.loads(capsys.readouterr().out)
    return rc, payload


def test_snapshot_matches_baseline(tmp_path, capsys):
    mod = _module()
    snapshot = tmp_path / "snapshot.json"
    baseline = tmp_path / "baseline.json"
    data = _snapshot_data()
    _write(snapshot, data)
    _write(baseline, data)
    rc, payload = _run(mod, snapshot, baseline, capsys)
    assert rc == 0
    assert payload["status"] == "pass"
    assert payload["count"] == len(data)
    assert payload["baseline"] == len(data)


def test_snapshot_with_new_finding(tmp_path, capsys):
    mod = _module()
    snapshot = tmp_path / "snapshot.json"
    baseline = tmp_path / "baseline.json"
    snapshot_data = _snapshot_data()
    baseline_data = [_snapshot_data()[0]]
    _write(snapshot, snapshot_data)
    _write(baseline, baseline_data)
    rc, payload = _run(mod, snapshot, baseline, capsys)
    assert rc == 1
    assert payload["status"] == "fail"
    assert payload["new_findings"] == [snapshot_data[1]]


def test_snapshot_stale_baseline(tmp_path, capsys):
    mod = _module()
    snapshot = tmp_path / "snapshot.json"
    baseline = tmp_path / "baseline.json"
    snapshot_data = [_snapshot_data()[0]]
    stale = _snapshot_data()[1]
    baseline_data = [*snapshot_data, stale]
    _write(snapshot, snapshot_data)
    _write(baseline, baseline_data)
    rc, payload = _run(mod, snapshot, baseline, capsys)
    assert rc == 1
    assert payload["status"] == "fail"
    assert payload["stale_baseline"] == [stale]
    assert "scripts/coverage_gap_baseline.json" in payload["message"]
