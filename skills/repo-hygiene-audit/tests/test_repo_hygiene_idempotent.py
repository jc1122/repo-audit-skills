import json

from helpers import load_module, make_dirty_repo


def test_findings_byte_identical_across_runs(tmp_path):
    """Two runs against the same dirty repo yield byte-identical findings JSON."""
    repo, _ = make_dirty_repo(tmp_path)
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"max_tracked_file_bytes": 1024}')

    out_a = tmp_path / "a"
    out_b = tmp_path / "b"

    mod = load_module()
    rc_a = mod.main(
        ["--root", str(repo), "--out-dir", str(out_a), "--config", str(cfg)]
    )
    rc_b = mod.main(
        ["--root", str(repo), "--out-dir", str(out_b), "--config", str(cfg)]
    )
    assert rc_a == rc_b

    text_a = (out_a / "repo-hygiene_findings.json").read_bytes()
    text_b = (out_b / "repo-hygiene_findings.json").read_bytes()
    assert text_a == text_b, "findings JSON differ across runs"

    # Also assert both are valid JSON lists of dicts with consistent ids
    data_a = json.loads(text_a)
    assert isinstance(data_a, list)
    assert len(data_a) > 0
    for f in data_a:
        assert isinstance(f, dict)
        assert "id" in f
        assert f["leaf"] == "repo-hygiene"
