import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_repo_hygiene.py"

FINDING_A = {
    "leaf": "hygiene",
    "metric": "tracked_artifact",
    "path": "scripts/a.py",
    "symbol": "<module>",
}
FINDING_B = {
    "leaf": "hygiene",
    "metric": "tracked_artifact",
    "path": "scripts/b.py",
    "symbol": "<module>",
}


def _run(tmp_path, capsys, snapshot, baseline):
    spec = importlib.util.spec_from_file_location("check_repo_hygiene", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
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
    assert "scripts/repo_hygiene_baseline.json" in payload["message"]


def test_equal_snapshot_and_baseline_passes(tmp_path, capsys):
    rc, payload = _run(
        tmp_path, capsys, [FINDING_A, FINDING_B], [FINDING_A, FINDING_B]
    )
    assert rc == 0
    assert payload["status"] == "pass"


def test_new_finding_still_fails(tmp_path, capsys):
    rc, payload = _run(tmp_path, capsys, [FINDING_A, FINDING_B], [FINDING_A])
    assert rc == 1
    assert payload["new_findings"] == [FINDING_B]


def test_scope_has_no_source_prefix():
    spec = importlib.util.spec_from_file_location("check_repo_hygiene", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    gs = mod._spec()
    assert "--source-prefix" not in gs.leaf_cmd
