"""Regression tests for exclude prefixes and placeholder path suppression."""

import json

from helpers import load_module, read_findings


def test_exclude_prefix_silences_matching_markdown_only(tmp_path):
    root = tmp_path / "tree"
    history = root / "docs" / "history"
    history.mkdir(parents=True)
    (root / "docs").mkdir(exist_ok=True)
    (history / "old.md").write_text("Old ref: `missing/history.py`.\n")
    (root / "docs" / "live.md").write_text("Live ref: `missing/live.py`.\n")

    mod = load_module()
    out = tmp_path / "out"
    mod.main(
        [
            "--root",
            str(root),
            "--exclude-prefix",
            "docs/history",
            "--out-dir",
            str(out),
        ]
    )

    paths = [
        f for f in read_findings(out) if f["metric"]["name"] == "doc_path_missing"
    ]
    assert len(paths) == 1
    assert paths[0]["path"] == "docs/live.md"


def test_placeholder_path_token_is_skipped_and_counted(tmp_path, capsys):
    root = tmp_path / "tree"
    root.mkdir()
    (root / "README.md").write_text(
        "Report: `docs/audits/<run-id>/run_report.json`.\n"
    )

    mod = load_module()
    out = tmp_path / "out"
    mod.main(["--root", str(root), "--out-dir", str(out)])

    status = json.loads(capsys.readouterr().out)
    assert status["skipped_placeholder_tokens"] == 1
    assert read_findings(out) == []


def test_plain_missing_path_still_emits_without_suppression(tmp_path, capsys):
    root = tmp_path / "tree"
    root.mkdir()
    (root / "README.md").write_text("Missing: `docs/audits/run_report.json`.\n")

    mod = load_module()
    out = tmp_path / "out"
    mod.main(["--root", str(root), "--out-dir", str(out)])

    status = json.loads(capsys.readouterr().out)
    paths = [
        f for f in read_findings(out) if f["metric"]["name"] == "doc_path_missing"
    ]
    assert status["skipped_placeholder_tokens"] == 0
    assert len(paths) == 1
    assert paths[0]["location"]["symbol"] == "docs/audits/run_report.json"


def test_generated_output_path_token_is_skipped_and_counted(tmp_path, capsys):
    root = tmp_path / "tree"
    root.mkdir()
    (root / "README.md").write_text(
        "Coverage: `.self_audit_out/coverage/coverage.json`.\n"
    )

    mod = load_module()
    out = tmp_path / "out"
    mod.main(["--root", str(root), "--out-dir", str(out)])

    status = json.loads(capsys.readouterr().out)
    paths = [
        f for f in read_findings(out) if f["metric"]["name"] == "doc_path_missing"
    ]
    assert status["skipped_output_path_tokens"] == 1
    assert paths == []


def test_plain_missing_path_does_not_increment_output_path_counter(tmp_path, capsys):
    root = tmp_path / "tree"
    root.mkdir()
    (root / "README.md").write_text("Missing: `docs/audits/run_report.json`.\n")

    mod = load_module()
    out = tmp_path / "out"
    mod.main(["--root", str(root), "--out-dir", str(out)])

    status = json.loads(capsys.readouterr().out)
    paths = [
        f for f in read_findings(out) if f["metric"]["name"] == "doc_path_missing"
    ]
    assert status["skipped_output_path_tokens"] == 0
    assert len(paths) == 1
