"""Finding-level assertions for hotspot-audit.

Tests the analysis output field-by-field against known fixture expectations.
All tests are in-process via load_module().main([...]).
"""

import json

from helpers import FIXTURES, load_module, make_history


def test_hotspot_churn_product(tmp_path):
    """Plan A1: hot.py churn-complexity + three temporal-coupling pairs from fixture.

    The fixture touches hot.py, a.py, b.py together in 5 commits (c0-c4),
    producing three co-changing pairs.  The plan's analysis spec counts all
    pairs meeting the thresholds -- not only one.
    """
    repo = make_history(tmp_path)
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    assert rc == 1
    data = json.loads((out / "hotspot_findings.json").read_text())

    # --- churn-complexity hotspot -------------------------------------------
    hot = [f for f in data if f["metric"]["name"] == "churn_complexity_product"]
    assert [f["path"] for f in hot] == ["hot.py"]
    assert hot[0]["metric"]["value"] == 1200.0  # 6 commits x 200 nloc
    assert hot[0]["signal"] == "DECOMPOSE"
    assert hot[0]["severity"] == "low"  # < 2x threshold (2000)

    # --- temporal coupling (three pairs, all co-change 5x) ------------------
    pairs = [f for f in data if f["metric"]["name"] == "temporal_coupling_ratio"]
    assert [f["location"]["symbol"] for f in pairs] == [
        "a.py<->b.py",
        "a.py<->hot.py",
        "b.py<->hot.py",
    ]
    # a.py<->b.py: co=5 / min(churn a=5, churn b=6) = 5/5 = 1.0
    assert pairs[0]["metric"]["value"] == 1.0
    # a.py<->hot.py: co=5 / min(5, 6) = 1.0
    assert pairs[1]["metric"]["value"] == 1.0
    # b.py<->hot.py: co=5 / min(6, 6) = 5/6 ~ 0.83
    assert pairs[2]["metric"]["value"] == 0.83

    # default min_author_commits=10 > the fixture's 6 -> no knowledge findings
    assert [f for f in data if f["metric"]["name"] == "author_concentration"] == []


def test_author_concentration_with_lowered_config(tmp_path):
    """Verbatim A1 assertion: lowered min_author_commits surfaces knowledge concentration."""
    repo = make_history(tmp_path)
    mod = load_module()
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"min_author_commits": 5}')
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out), "--config", str(cfg)])
    assert rc == 1
    data = json.loads((out / "hotspot_findings.json").read_text())
    conc = [f for f in data if f["metric"]["name"] == "author_concentration"]
    # a.py: alice 5/5 commits; hot.py: alice 6/6 commits; b.py: alice 5/6 = 0.83 < 0.9 -> absent
    assert [f["path"] for f in conc] == ["a.py", "hot.py"]
    assert all(f["confidence"] == "low" and f["signal"] == "RESTRUCTURE" for f in conc)


def test_golden_findings_match_field_by_field(tmp_path):
    """Default run against make_history must match golden_findings.json field-by-field."""
    repo = make_history(tmp_path)
    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(repo), "--out-dir", str(out)])
    assert rc == 1
    actual = json.loads((out / "hotspot_findings.json").read_text())
    golden_path = FIXTURES / "golden_findings.json"
    expected = json.loads(golden_path.read_text())
    assert len(actual) == len(expected), (
        f"expected {len(expected)} findings, got {len(actual)}"
    )
    for i, (exp, act) in enumerate(zip(expected, actual)):
        assert act == exp, (
            f"finding[{i}] mismatch:\n"
            f"  expected: {json.dumps(exp, indent=2)}\n"
            f"  actual:   {json.dumps(act, indent=2)}"
        )
