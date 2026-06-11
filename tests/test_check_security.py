import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_security_audit.py"

FINDING_A = {
    "leaf": "security",
    "metric": "bandit_issue",
    "path": "scripts/a.py",
    "symbol": "f",
}
FINDING_B = {
    "leaf": "security",
    "metric": "bandit_issue",
    "path": "scripts/b.py",
    "symbol": "g",
}


def _run(tmp_path, capsys, snapshot, baseline):
    spec = importlib.util.spec_from_file_location("check_security_audit", SCRIPT)
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
    assert "scripts/security_baseline.json" in payload["message"]


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


def test_scope_includes_source_prefixes():
    spec = importlib.util.spec_from_file_location("check_security_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    import scripts.gate_common as gate_common  # noqa: E402

    gs = mod._spec()
    assert "--source-prefix" in gs.leaf_cmd
    assert "shared" in gs.leaf_cmd
    assert "scripts" in gs.leaf_cmd
    source_prefix_count = sum(
        1 for a in gs.leaf_cmd if a == "--source-prefix"
    )
    assert source_prefix_count == len(gate_common.production_prefixes(ROOT))
