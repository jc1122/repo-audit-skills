import json
from pathlib import Path

from helpers import load_module, read_findings


def _write_tool(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "import subprocess\n\n"
        "PASSWORD = 'secret-token'\n\n"
        "def status():\n"
        "    subprocess.run(['git', 'status'])\n",
        encoding="utf-8",
    )


def _write_config(path: Path, globs: list[str]) -> Path:
    config = {
        "trusted_subprocess": {
            "enabled": True,
            "rules": ["B404", "B603", "B607"],
            "path_globs": globs,
        }
    }
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def _metrics(findings: list[dict]) -> set[str]:
    return {finding["metric"]["name"] for finding in findings}


def test_policy_absent_keeps_subprocess_findings(tmp_path):
    mod = load_module()
    _write_tool(tmp_path / "scripts" / "tool.py")
    out_dir = tmp_path / "out"

    assert mod.main(["--root", str(tmp_path), "--out-dir", str(out_dir)]) == 1

    assert "bandit_B603" in _metrics(read_findings(out_dir))


def test_matching_policy_suppresses_and_counts_trusted_subprocess(tmp_path):
    mod = load_module()
    _write_tool(tmp_path / "scripts" / "tool.py")
    config = _write_config(tmp_path / "security.json", ["scripts/**"])
    out_dir = tmp_path / "out"

    assert (
        mod.main(
            [
                "--root",
                str(tmp_path),
                "--out-dir",
                str(out_dir),
                "--config",
                str(config),
            ]
        )
        == 1
    )

    findings = read_findings(out_dir)
    assert not ({"bandit_B404", "bandit_B603", "bandit_B607"} & _metrics(findings))
    summary = json.loads((out_dir / "security_summary.json").read_text())
    assert summary["suppression_counts"] == {"trusted_subprocess": 3}
    assert {
        (item["class"], item["rule"], item["path"])
        for item in summary["suppressed_findings"]
    } == {
        ("trusted_subprocess", "B404", "scripts/tool.py"),
        ("trusted_subprocess", "B603", "scripts/tool.py"),
        ("trusted_subprocess", "B607", "scripts/tool.py"),
    }


def test_policy_does_not_hide_other_rules_on_same_file(tmp_path):
    mod = load_module()
    _write_tool(tmp_path / "scripts" / "tool.py")
    config = _write_config(tmp_path / "security.json", ["scripts/**"])
    out_dir = tmp_path / "out"

    assert (
        mod.main(
            [
                "--root",
                str(tmp_path),
                "--out-dir",
                str(out_dir),
                "--config",
                str(config),
            ]
        )
        == 1
    )

    assert "bandit_B105" in _metrics(read_findings(out_dir))


def test_policy_does_not_hide_files_outside_path_globs(tmp_path):
    mod = load_module()
    _write_tool(tmp_path / "other" / "tool.py")
    config = _write_config(tmp_path / "security.json", ["scripts/**"])
    out_dir = tmp_path / "out"

    assert (
        mod.main(
            [
                "--root",
                str(tmp_path),
                "--out-dir",
                str(out_dir),
                "--config",
                str(config),
            ]
        )
        == 1
    )

    assert "bandit_B603" in _metrics(read_findings(out_dir))
    summary = json.loads((out_dir / "security_summary.json").read_text())
    assert summary["suppressed_findings"] == []


def test_markdown_renders_suppression_count(tmp_path):
    mod = load_module()
    _write_tool(tmp_path / "scripts" / "tool.py")
    config = _write_config(tmp_path / "security.json", ["scripts/**"])
    out_dir = tmp_path / "out"

    assert (
        mod.main(
            [
                "--root",
                str(tmp_path),
                "--out-dir",
                str(out_dir),
                "--config",
                str(config),
            ]
        )
        == 1
    )

    report = (out_dir / "security_report.md").read_text(encoding="utf-8")
    assert "trusted_subprocess: 3 counted suppressions" in report
