"""CLI contract tests for hotspot-audit.

Help smoke uses subprocess; all other exit-code tests use in-process
mod.main([...]) with capsys where needed (C-4 convention).
"""

import json
import os
import subprocess as sp

from helpers import load_module, make_clean_repo, make_history, run_cli


# ---------------------------------------------------------------------------
# subprocess help smoke (the ONLY subprocess test per C-4)
# ---------------------------------------------------------------------------

def test_help_exits_zero():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--root" in result.stdout


# ---------------------------------------------------------------------------
# in-process exit-code / contract tests
# ---------------------------------------------------------------------------

def test_missing_required_args_exits_two(capsys):
    """--root and --out-dir are required; missing either -> exit 2 + status-error JSON."""
    mod = load_module()
    rc = mod.main([])
    assert rc == 2
    out = capsys.readouterr().out
    data = json.loads(out.strip())
    assert data["status"] == "error"
    assert "required" in data["message"].lower()


def test_clean_git_exits_zero(tmp_path, capsys):
    """A minimal clean git repo with one small file yields exit 0 and [] findings."""
    repo = make_clean_repo(tmp_path)
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir)])
    assert rc == 0
    # Verify stdout status line
    out = capsys.readouterr().out
    data = json.loads(out.strip())
    assert data["status"] == "ok"
    assert data["findings"] == 0
    assert data["leaf"] == "hotspot"


def test_dirty_fixture_exits_one(tmp_path):
    """make_history fixture produces findings -> exit 1."""
    repo = make_history(tmp_path)
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir)])
    assert rc == 1


def test_non_git_root_exits_two(tmp_path, capsys):
    """Plain directory (no .git) -> exit 2 with 'not a git repository'."""
    mod = load_module()
    plain = tmp_path / "plain"
    plain.mkdir()
    rc = mod.main(["--root", str(plain), "--out-dir", str(tmp_path / "o")])
    assert rc == 2
    assert "not a git repository" in capsys.readouterr().out


def test_max_commits_three_produces_fewer_findings(tmp_path):
    """--max-commits 3 limits history -> zero findings and exit 0."""
    repo = make_history(tmp_path)
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir),
                   "--max-commits", "3"])
    # With 3 commits no file reaches min_churn_commits=5
    # so we expect zero findings and exit 0.
    assert rc == 0, f"expected exit 0 with --max-commits 3, got {rc}"
    data = json.loads((out_dir / "hotspot_findings.json").read_text())
    assert len(data) == 0, f"expected 0 findings with --max-commits 3, got {len(data)}"


def test_rev_first_commit_produces_zero_findings(tmp_path):
    """--rev pinned to the root (first) commit -> zero findings."""
    repo = make_history(tmp_path)
    # Get the first commit SHA
    result = sp.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    first_commit = result.stdout.strip()
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir),
                   "--rev", first_commit])
    # Single commit of history -> all files churn=1 < min_churn_commits=5 -> 0 findings
    assert rc == 0
    data = json.loads((out_dir / "hotspot_findings.json").read_text())
    assert len(data) == 0, f"expected 0 findings with --rev first commit, got {len(data)}"


def test_unreachable_rev_exits_two(tmp_path, capsys):
    """--rev with a nonexistent commit hash -> exit 2 error."""
    repo = make_history(tmp_path)
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir),
                   "--rev", "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"])
    assert rc == 2
    captured = capsys.readouterr().out
    assert "error" in captured.lower() or "failed" in captured.lower()


def test_empty_history_exits_two(tmp_path, capsys):
    """A git repo with no commits -> exit 2."""
    repo = tmp_path / "empty"
    repo.mkdir()
    env = dict(os.environ, **{
        "GIT_AUTHOR_NAME": "alice", "GIT_AUTHOR_EMAIL": "alice@x.test",
        "GIT_COMMITTER_NAME": "alice", "GIT_COMMITTER_EMAIL": "alice@x.test",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00 +0000",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00 +0000",
        "HOME": "/tmp", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
    })
    sp.run(["git", "-C", str(repo), "init", "-q", "-b", "main"],
           env=env, check=True, capture_output=True, text=True)
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir)])
    assert rc == 2
    captured = capsys.readouterr().out
    assert "no commits" in captured.lower() or "empty" in captured.lower() or "error" in captured.lower()


# ---------------------------------------------------------------------------
# additional contract / coverage-oriented tests (Wave 2 hardening)
# ---------------------------------------------------------------------------


def test_invalid_config_exits_two(tmp_path, capsys):
    """Malformed --config JSON -> exit 2 in-process."""
    repo = make_history(tmp_path)
    cfg = tmp_path / "bad.json"
    cfg.write_text("not json")
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir),
                   "--config", str(cfg)])
    assert rc == 2
    captured = capsys.readouterr().out
    data = json.loads(captured.strip())
    assert data["status"] == "error"


def test_invalid_config_missing_file_exits_two(tmp_path, capsys):
    """--config pointing to a nonexistent file -> exit 2."""
    repo = make_history(tmp_path)
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir),
                   "--config", str(tmp_path / "does_not_exist.json")])
    assert rc == 2
    captured = capsys.readouterr().out
    data = json.loads(captured.strip())
    assert data["status"] == "error"


def test_format_md_accepted_and_still_writes_both_outputs(tmp_path):
    """--format md writes both hotspot_report.md and hotspot_findings.json."""
    repo = make_history(tmp_path)
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir),
                   "--format", "md"])
    assert rc == 1, "make_history fixture produces findings"
    # Both output files must exist
    findings = out_dir / "hotspot_findings.json"
    report = out_dir / "hotspot_report.md"
    assert findings.exists(), "hotspot_findings.json must be written with --format md"
    assert report.exists(), "hotspot_report.md must be written with --format md"
    # findings.json must be valid JSON
    data = json.loads(findings.read_text())
    assert len(data) > 0
    # report.md must contain at least the title
    md_text = report.read_text()
    assert "# hotspot-audit report" in md_text.lower() or "# hotspot" in md_text.lower()


def test_status_stdout_includes_rev_and_max_commits(tmp_path, capsys):
    """Status line JSON must include resolved rev SHA and max_commits."""
    repo = make_history(tmp_path)
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir)])
    assert rc == 1
    status = json.loads(capsys.readouterr().out.strip())
    assert status["status"] == "ok"
    assert "rev" in status, f"status must include 'rev' key: {status}"
    assert "max_commits" in status, f"status must include 'max_commits' key: {status}"
    # rev must be a 40-char hex SHA
    assert len(status["rev"]) == 40, f"rev must be full SHA: {status['rev']}"
    # max_commits must be an integer (default 500)
    assert isinstance(status["max_commits"], int)


def test_status_stdout_respects_explicit_max_commits(tmp_path, capsys):
    """Status line max_commits reflects the user-provided value."""
    repo = make_history(tmp_path)
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir),
                   "--max-commits", "10"])
    assert rc == 1
    status = json.loads(capsys.readouterr().out.strip())
    assert status["max_commits"] == 10


def test_default_run_evidence_contains_short_sha_and_window(tmp_path):
    """Every finding on a default run records resolved short SHA and window."""
    repo = make_history(tmp_path)
    # Compute the expected short SHA from git
    head_sha = sp.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    short_sha = head_sha[:12]
    out_dir = tmp_path / "out"
    mod = load_module()
    rc = mod.main(["--root", str(repo), "--out-dir", str(out_dir)])
    assert rc == 1
    data = json.loads((out_dir / "hotspot_findings.json").read_text())
    assert len(data) > 0, "expected findings to check evidence"
    for f in data:
        evidence = f["evidence"]["raw"]
        assert short_sha in evidence, (
            f"evidence_raw must contain resolved short SHA {short_sha!r}: {evidence!r}"
        )
        # Default max_commits=500, but fixture has only 8 commits; evidence
        # should mention the commit count (window size) or the definitive
        # history length.
        assert "commits" in evidence.lower(), (
            f"evidence_raw should mention commit window: {evidence!r}"
        )
