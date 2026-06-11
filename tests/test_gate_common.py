"""Tests for scripts/gate_common.py — shared ratchet-gate verdict logic."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gate_common.py"

NORM_A = {
    "leaf": "complexity",
    "path": "scripts/x.py",
    "symbol": "f",
    "metric": "cyclomatic_complexity",
}
NORM_B = {
    "leaf": "quality",
    "path": "scripts/y.py",
    "symbol": "<module>",
    "metric": "lint_errors",
}
NORM_C = {
    "leaf": "dead",
    "path": "scripts/z.py",
    "symbol": "g",
    "metric": "unused_code",
}

RAW_A = {
    "leaf": "complexity",
    "path": "scripts/x.py",
    "location": {"symbol": "f"},
    "metric": {"name": "cyclomatic_complexity"},
    "id": "extra1",
    "severity": "high",
}
RAW_B = {
    "leaf": "quality",
    "path": "scripts/y.py",
    "location": {"symbol": "<module>"},
    "metric": {"name": "lint_errors"},
    "id": "extra2",
}
# keys in different order to test sort stability of normalize_findings
RAW_C = {
    "metric": {"name": "unused_code"},
    "severity": "low",
    "location": {"symbol": "g"},
    "leaf": "dead",
    "path": "scripts/z.py",
    "id": "extra3",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _load_module():
    spec = importlib.util.spec_from_file_location("gate_common", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# identities
# ---------------------------------------------------------------------------


def test_identities_dedup():
    mod = _load_module()
    result = mod.identities([NORM_A, NORM_A.copy()])
    assert len(result) == 1


def test_identities_different():
    mod = _load_module()
    result = mod.identities([NORM_A, NORM_B])
    assert len(result) == 2


# ---------------------------------------------------------------------------
# verdict
# ---------------------------------------------------------------------------


def test_verdict_pass():
    mod = _load_module()
    code, payload = mod.verdict(
        [NORM_A, NORM_B],
        [NORM_A, NORM_B],
        baseline_path="scripts/foo_baseline.json",
    )
    assert code == 0
    assert payload["status"] == "pass"
    assert payload["count"] == 2
    assert payload["baseline"] == 2


def test_verdict_new_finding():
    mod = _load_module()
    code, payload = mod.verdict(
        [NORM_A, NORM_B],
        [NORM_A],
        baseline_path="scripts/foo_baseline.json",
    )
    assert code == 1
    assert payload["new_findings"] == [NORM_B]


def test_verdict_stale_baseline():
    mod = _load_module()
    code, payload = mod.verdict(
        [NORM_A],
        [NORM_A, NORM_B],
        baseline_path="scripts/foo_baseline.json",
    )
    assert code == 1
    assert payload["stale_baseline"] == [NORM_B]
    assert "same commit" in payload["message"]
    assert "scripts/foo_baseline.json" in payload["message"]


# ---------------------------------------------------------------------------
# normalize_findings
# ---------------------------------------------------------------------------


def test_normalize_findings_maps_and_sorts():
    mod = _load_module()
    raw = [RAW_A, RAW_B, RAW_C]
    result = mod.normalize_findings(raw)
    # sorted by (path, leaf, metric, symbol)
    assert result[0] == NORM_A  # scripts/x.py, complexity, cyclomatic_…
    assert result[1] == NORM_B  # scripts/y.py, quality, lint_errors
    assert result[2] == NORM_C  # scripts/z.py, dead, unused_code
    # extra keys are dropped
    for d in result:
        assert set(d.keys()) == {"leaf", "path", "symbol", "metric"}


def test_normalize_findings_empty():
    mod = _load_module()
    assert mod.normalize_findings([]) == []


# ---------------------------------------------------------------------------
# production_prefixes
# ---------------------------------------------------------------------------


def test_production_prefixes():
    mod = _load_module()
    result = mod.production_prefixes(ROOT)
    assert isinstance(result, list)
    assert result[0] == "shared"
    assert result[1] == "scripts"
    assert "skills/security-audit/scripts" in result


# ---------------------------------------------------------------------------
# gate_main (with --snapshot so the leaf is never invoked)
# ---------------------------------------------------------------------------


def _run_gate(tmp_path, capsys, snapshot, baseline):
    mod = _load_module()
    snap = tmp_path / "snap.json"
    base = tmp_path / "base.json"
    snap.write_text(json.dumps(snapshot))
    base.write_text(json.dumps(baseline))
    rc = mod.gate_main(
        ["--snapshot", str(snap), "--baseline", str(base)],
        mod.GateSpec(
            leaf_cmd=["/bin/false"],
            findings_file="/dev/null",
            snapshot_path=str(tmp_path / "out.json"),
            baseline_path="scripts/x_baseline.json",
            description="x",
        ),
    )
    return rc, json.loads(capsys.readouterr().out)


def test_gate_main_pass(tmp_path, capsys):
    rc, payload = _run_gate(
        tmp_path, capsys, [NORM_A, NORM_B], [NORM_A, NORM_B]
    )
    assert rc == 0
    assert payload["status"] == "pass"


def test_gate_main_new_finding(tmp_path, capsys):
    rc, payload = _run_gate(
        tmp_path, capsys, [NORM_A, NORM_B], [NORM_A]
    )
    assert rc == 1
    assert payload["new_findings"] == [NORM_B]


def test_gate_main_stale_baseline(tmp_path, capsys):
    rc, payload = _run_gate(
        tmp_path, capsys, [NORM_A], [NORM_A, NORM_B]
    )
    assert rc == 1
    assert payload["stale_baseline"] == [NORM_B]
    assert "same commit" in payload["message"]
    assert "scripts/x_baseline.json" in payload["message"]


# ---------------------------------------------------------------------------
# gate_main leaf-run branch (no --snapshot)
# ---------------------------------------------------------------------------


def test_gate_main_leaf_run_pass(tmp_path, capsys):
    """Verify gate_main runs the leaf, normalizes, and returns pass."""
    mod = _load_module()
    findings_file = tmp_path / "findings.json"
    snapshot_file = tmp_path / "snapshot.json"
    baseline_file = tmp_path / "baseline.json"

    baseline_file.write_text("[]")

    rc = mod.gate_main(
        ["--baseline", str(baseline_file)],
        mod.GateSpec(
            leaf_cmd=[
                sys.executable,
                "-c",
                f"open({str(findings_file)!r},'w').write('[]')",
            ],
            findings_file=str(findings_file),
            snapshot_path=str(snapshot_file),
            baseline_path="scripts/test_baseline.json",
            description="test",
        ),
    )

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 0
    assert payload["status"] == "pass"
    assert snapshot_file.exists()
    assert json.loads(snapshot_file.read_text()) == []


def test_gate_main_leaf_tool_error(tmp_path, capsys):
    """Verify returncode 2 produces an error payload and exit code 1."""
    mod = _load_module()
    findings_file = tmp_path / "findings.json"
    snapshot_file = tmp_path / "snapshot.json"
    baseline_file = tmp_path / "baseline.json"

    baseline_file.write_text("[]")

    rc = mod.gate_main(
        [],
        mod.GateSpec(
            leaf_cmd=[sys.executable, "-c", "import sys; sys.exit(2)"],
            findings_file=str(findings_file),
            snapshot_path=str(snapshot_file),
            baseline_path="scripts/test_baseline.json",
            description="test",
        ),
    )

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 1
    assert payload["status"] == "error"
    assert payload["leaf_returncode"] == 2
