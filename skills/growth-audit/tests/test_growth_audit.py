"""Tests for the growth-audit leaf.

All tests synthesise git repos under ``tmp_path`` — no fixture files.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "growth_audit.py"
)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _read_findings(out_dir: Path) -> list[dict]:
    path = out_dir / "growth-audit_findings.json"
    return json.loads(path.read_text()) if path.exists() else []


def _read_summary(out_dir: Path) -> dict:
    path = out_dir / "growth-audit_summary.json"
    return json.loads(path.read_text()) if path.exists() else {}


# ---------------------------------------------------------------------------
# helpers: build synthetic git repos inside tmp_path
# ---------------------------------------------------------------------------


def _git_init(path: Path) -> None:
    subprocess.run(
        ["git", "-C", str(path), "init", "-b", "main"],
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        capture_output=True,
        check=True,
    )


def _git_commit_all(path: Path, msg: str) -> None:
    subprocess.run(
        ["git", "-C", str(path), "add", "-A"],
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", msg, "--no-verify"],
        capture_output=True,
        text=True,
        check=True,
    )


def _git_tag(path: Path, tag: str) -> None:
    subprocess.run(
        ["git", "-C", str(path), "tag", tag],
        capture_output=True,
        text=True,
        check=True,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# test: CLI fundamentals
# ---------------------------------------------------------------------------


def test_help_exits_zero():
    result = _run("--help")
    assert result.returncode == 0
    assert "--root" in result.stdout
    assert "--baseline-rev" in result.stdout


def test_missing_root_and_out_dir_exits_two():
    result = _run()
    assert result.returncode == 2


# ---------------------------------------------------------------------------
# test: growth detection
# ---------------------------------------------------------------------------


def test_detects_tracked_files_and_net_loc_growth(tmp_path: Path):
    """Tag a baseline, then add a source file — both metrics should fire."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    # baseline
    _write(repo / "README.md", "# Hello\n")
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    # grow: add a source file
    _write(repo / "src" / "main.py", "def main():\n    pass\n")
    _git_commit_all(repo, "add main.py")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    assert result.returncode == 1, f"stderr: {result.stderr}"

    findings = _read_findings(out)
    assert len(findings) >= 2, f"got {len(findings)} findings"

    metric_names = {f["metric"]["name"] for f in findings}
    assert "tracked_files_growth" in metric_names
    assert "net_loc_growth" in metric_names

    summary = _read_summary(out)
    assert summary["metrics"]["tracked_files_growth"] >= 1
    assert summary["metrics"]["net_loc_growth"] > 0


def test_deletion_only_repo_is_clean(tmp_path: Path):
    """Pure deletions should produce zero findings."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(repo / "a.py", "x = 1\n")
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    # delete the file
    (repo / "a.py").unlink()
    _git_commit_all(repo, "remove a.py")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    assert result.returncode == 0, f"stderr: {result.stderr}"

    findings = _read_findings(out)
    assert findings == []


# ---------------------------------------------------------------------------
# test: allowance / suppression
# ---------------------------------------------------------------------------


def test_allowance_suppresses_tracked_files_growth(tmp_path: Path):
    """An allowance >= the delta suppresses the finding and counts it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(repo / "README.md", "# Hello\n")
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    # add 2 new files
    _write(repo / "a.py", "x = 1\n")
    _write(repo / "b.py", "x = 2\n")
    _git_commit_all(repo, "add two files")

    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps(
            {
                "allow_growth": [
                    {
                        "metric": "tracked_files_growth",
                        "max_delta": 5,
                        "reason": "planned",
                    }
                ]
            }
        )
    )

    out = tmp_path / "out"
    result = _run(
        "--root", str(repo),
        "--out-dir", str(out),
        "--baseline-rev", "base",
        "--config", str(cfg),
    )
    # May still have findings for other metrics, but tracked_files_growth must
    # not appear as a finding.
    findings = _read_findings(out)
    tf_names = [
        f["metric"]["name"]
        for f in findings
        if f["metric"]["name"] == "tracked_files_growth"
    ]
    assert tf_names == [], f"tracked_files_growth should be suppressed, got {tf_names}"

    summary = _read_summary(out)
    # The summary must record the suppression
    suppressions = summary.get("suppressions", summary.get("suppression_counts", []))
    if isinstance(suppressions, list):
        suppressed_metrics = {s["metric"] for s in suppressions}
    else:
        suppressed_metrics = set(suppressions.keys())
    assert "tracked_files_growth" in suppressed_metrics or any(
        "tracked_files_growth" in str(s) for s in suppressions
    )


def test_growth_above_allowance_still_emits(tmp_path: Path):
    """Tiny allowance for net_loc_growth — growth beyond it still fires."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(repo / "README.md", "# Hello\n")
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    # add 20 lines of code
    _write(repo / "big.py", "\n".join(f"x{i} = {i}" for i in range(20)) + "\n")
    _git_commit_all(repo, "add big.py")

    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps(
            {
                "allow_growth": [
                    {"metric": "net_loc_growth", "max_delta": 2, "reason": "tiny"}
                ]
            }
        )
    )

    out = tmp_path / "out"
    result = _run(
        "--root", str(repo),
        "--out-dir", str(out),
        "--baseline-rev", "base",
        "--config", str(cfg),
    )
    assert result.returncode == 1, f"stderr: {result.stderr}"

    findings = _read_findings(out)
    nl_findings = [
        f for f in findings if f["metric"]["name"] == "net_loc_growth"
    ]
    assert len(nl_findings) >= 1, "net_loc_growth should still emit a finding"


# ---------------------------------------------------------------------------
# test: non-Python/package.json dependency detection
# ---------------------------------------------------------------------------


def test_dependency_delta_cargo_toml(tmp_path: Path):
    """New dependencies in Cargo.toml (Rust) should be detected."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(
        repo / "Cargo.toml",
        "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n\n[dependencies]\n"
        "serde = \"1\"\n",
    )
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    _write(
        repo / "Cargo.toml",
        "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n\n[dependencies]\n"
        "serde = \"1\"\n"
        "tokio = { version = \"1\", features = [\"full\"] }\n"
        "clap = \"4\"\n",
    )
    _git_commit_all(repo, "add tokio and clap deps")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    assert result.returncode == 1, f"stderr: {result.stderr}"

    summary = _read_summary(out)
    assert summary["metrics"]["dependency_growth"] >= 2, (
        f"expected >= 2 new deps, got {summary['metrics']['dependency_growth']}"
    )


def test_dependency_delta_go_mod(tmp_path: Path):
    """New dependencies in go.mod should be detected."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(
        repo / "go.mod",
        "module example\n\ngo 1.21\n\nrequire (\n\tgithub.com/stretchr/testify v1.8.0\n)\n",
    )
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    _write(
        repo / "go.mod",
        "module example\n\ngo 1.21\n\nrequire (\n\tgithub.com/stretchr/testify v1.8.0\n"
        "\tgithub.com/gin-gonic/gin v1.9.0\n)\n",
    )
    _git_commit_all(repo, "add gin dep")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    assert result.returncode == 1, f"stderr: {result.stderr}"

    summary = _read_summary(out)
    assert summary["metrics"]["dependency_growth"] >= 1, (
        f"expected >= 1 new dep, got {summary['metrics']['dependency_growth']}"
    )


# ---------------------------------------------------------------------------
# test: CLI flag growth
# ---------------------------------------------------------------------------


def test_cli_flag_growth_detected(tmp_path: Path):
    """Adding a new argparse add_argument call should be detected."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(
        repo / "cli.py",
        "import argparse\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--name')\n",
    )
    _git_commit_all(repo, "initial with one flag")
    _git_tag(repo, "base")

    _write(
        repo / "cli.py",
        "import argparse\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--name')\n"
        "p.add_argument('--verbose', action='store_true')\n"
        "p.add_argument('--output', '-o')\n",
    )
    _git_commit_all(repo, "add two more flags")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    # May or may not produce findings depending on other metrics,
    # but cli_flag_growth should be present in summary
    summary = _read_summary(out)
    assert summary["metrics"]["cli_flag_growth"] >= 2, (
        f"expected >= 2 new flags, got {summary['metrics']['cli_flag_growth']}"
    )
