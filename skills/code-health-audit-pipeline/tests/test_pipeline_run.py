import json
from pathlib import Path

from helpers import FIXTURES, load_module

ch = load_module()


def _registry(tmp_path, leaves):
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({"leaves": leaves}))
    return path


def test_select_leaves_filters_by_language():
    leaves = [
        {"name": "py", "skill": "py", "script": "x", "languages": ["python"], "findings_file": "py_findings.json"},
        {"name": "c", "skill": "c", "script": "x", "languages": ["c"], "findings_file": "c_findings.json"},
    ]
    selected = ch.select_leaves(leaves, ["python"])
    assert [s["name"] for s in selected] == ["py"]


def test_select_leaves_wildcard_always_selected():
    leaves = [
        {"name": "py", "skill": "py", "script": "x", "languages": ["python"], "findings_file": "py_findings.json"},
        {"name": "any", "skill": "any", "script": "x", "languages": ["*"], "findings_file": "any_findings.json"},
    ]
    assert [s["name"] for s in ch.select_leaves(leaves, ["python"])] == ["py", "any"]
    assert [s["name"] for s in ch.select_leaves(leaves, ["rust"])] == ["any"]


def test_run_leaves_collects_findings_and_exits(tmp_path):
    leaves = [
        {"name": "stub", "skill": "stub", "script": str(FIXTURES / "stub_leaf.py"),
         "languages": ["python"], "findings_file": "stub_findings.json"},
        {"name": "empty", "skill": "empty", "script": str(FIXTURES / "empty_leaf.py"),
         "languages": ["python"], "findings_file": "empty_findings.json"},
    ]
    out = tmp_path / "out"
    findings, leaf_exit = ch.run_leaves(leaves, root=str(tmp_path), source_prefixes=["pkg/"],
                                        out_dir=out, overrides={})
    assert leaf_exit == {"stub": 1, "empty": 0}
    assert len(findings) == 1
    assert (out / "stub" / "stub_findings.json").exists()
    assert (out / "empty" / "empty_findings.json").exists()


def test_errored_leaf_recorded(tmp_path):
    leaves = [{"name": "err", "skill": "err", "script": str(FIXTURES / "error_leaf.py"),
               "languages": ["python"], "findings_file": "err_findings.json"}]
    out = tmp_path / "out"
    findings, leaf_exit = ch.run_leaves(leaves, root=str(tmp_path), source_prefixes=[],
                                        out_dir=out, overrides={})
    assert leaf_exit == {"err": 2}
    assert findings == []


def test_override_replaces_script(tmp_path):
    leaves = [{"name": "stub", "skill": "stub", "script": "does/not/exist.py",
               "languages": ["python"], "findings_file": "stub_findings.json"}]
    out = tmp_path / "out"
    findings, leaf_exit = ch.run_leaves(leaves, root=str(tmp_path), source_prefixes=[],
                                        out_dir=out, overrides={"stub": str(FIXTURES / "stub_leaf.py")})
    assert leaf_exit == {"stub": 1}
    assert len(findings) == 1
