import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_self_audit.py"

FINDING_A = {"leaf": "complexity", "metric": "cyclomatic_complexity", "path": "scripts/x.py", "symbol": "f"}
FINDING_B = {"leaf": "quality", "metric": "lint_errors", "path": "scripts/y.py", "symbol": "<module>"}


def _load_mod():
    spec = importlib.util.spec_from_file_location("check_self_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(tmp_path, capsys, snapshot, baseline):
    mod = _load_mod()
    snap = tmp_path / "snapshot.json"
    base = tmp_path / "baseline.json"
    snap.write_text(json.dumps(snapshot))
    base.write_text(json.dumps(baseline))
    rc = mod.main(["--snapshot", str(snap), "--baseline", str(base)])
    return rc, json.loads(capsys.readouterr().out)


def test_stale_baseline_entry_fails_with_ratchet_message(tmp_path, capsys):
    rc, payload = _run(tmp_path, capsys, [FINDING_A], [FINDING_A, FINDING_B])
    assert rc == 1
    assert payload["status"] == "fail"
    assert payload["stale_baseline"] == [FINDING_B]
    assert "same commit" in payload["message"]


def test_equal_snapshot_and_baseline_passes(tmp_path, capsys):
    rc, payload = _run(tmp_path, capsys, [FINDING_A, FINDING_B], [FINDING_A, FINDING_B])
    assert rc == 0
    assert payload["status"] == "pass"


def test_new_finding_still_fails(tmp_path, capsys):
    rc, payload = _run(tmp_path, capsys, [FINDING_A, FINDING_B], [FINDING_A])
    assert rc == 1
    assert payload["new_findings"] == [FINDING_B]


def _accept(tmp_path, entries):
    path = tmp_path / "accept.json"
    path.write_text(json.dumps({"version": 1, "accept": entries}))
    return path


def test_baseline_rows_returns_report_findings_only(tmp_path):
    mod = _load_mod()
    path = _accept(
        tmp_path,
        [
            {"match": {"kind": "finding", **FINDING_A}, "reason": "x", "applies": ["report"]},
            # remediation-only path entry — must be ignored as a baseline row
            {"match": {"kind": "path", "glob": "**/tests/fixtures/**"}, "reason": "y", "applies": ["remediation"]},
            # finding that does not apply to the report stage — also ignored
            {"match": {"kind": "finding", **FINDING_B}, "reason": "z", "applies": ["remediation"]},
        ],
    )
    rows = mod._baseline_rows(path)
    assert rows == [FINDING_A]


def test_baseline_rows_fails_closed_on_bad_version(tmp_path):
    mod = _load_mod()
    path = tmp_path / "accept.json"
    path.write_text(json.dumps({"version": 2, "accept": []}))
    with pytest.raises(ValueError):
        mod._baseline_rows(path)
