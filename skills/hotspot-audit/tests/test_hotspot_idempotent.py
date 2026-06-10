"""Idempotence (byte-determinism) test for hotspot-audit.

C-2/C-4 requirement: two runs against the same deterministic history must
produce byte-identical ``hotspot_findings.json``.  All tests are in-process
via ``load_module().main([...])`` so pytest-cov traces them.
"""

import io
import json
import subprocess
from contextlib import redirect_stdout
from pathlib import Path

from helpers import load_module, make_history


def test_byte_identical_across_runs(tmp_path):
    """Two runs on the same fixture -> byte-identical hotspot_findings.json."""
    repo = make_history(tmp_path)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    mod = load_module()
    mod.main(["--root", str(repo), "--out-dir", str(out_a)])
    mod.main(["--root", str(repo), "--out-dir", str(out_b)])
    bytes_a = (out_a / "hotspot_findings.json").read_bytes()
    bytes_b = (out_b / "hotspot_findings.json").read_bytes()
    assert bytes_a == bytes_b, (
        f"idempotence failure: findings differ between runs\n"
        f"--- run a ---\n{bytes_a.decode()}\n"
        f"--- run b ---\n{bytes_b.decode()}"
    )


def test_byte_identical_with_config(tmp_path):
    """Two runs with the same --config -> byte-identical hotspot_findings.json."""
    repo = make_history(tmp_path)
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"min_author_commits": 5}')
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    mod = load_module()
    mod.main(["--root", str(repo), "--out-dir", str(out_a), "--config", str(cfg)])
    mod.main(["--root", str(repo), "--out-dir", str(out_b), "--config", str(cfg)])
    bytes_a = (out_a / "hotspot_findings.json").read_bytes()
    bytes_b = (out_b / "hotspot_findings.json").read_bytes()
    assert bytes_a == bytes_b, (
        f"idempotence failure with --config: findings differ between runs\n"
        f"--- run a ---\n{bytes_a.decode()}\n"
        f"--- run b ---\n{bytes_b.decode()}"
    )


def test_byte_identical_with_max_commits(tmp_path):
    """Two runs with the same --max-commits -> byte-identical findings."""
    repo = make_history(tmp_path)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    mod = load_module()
    mod.main(["--root", str(repo), "--out-dir", str(out_a), "--max-commits", "3"])
    mod.main(["--root", str(repo), "--out-dir", str(out_b), "--max-commits", "3"])
    bytes_a = (out_a / "hotspot_findings.json").read_bytes()
    bytes_b = (out_b / "hotspot_findings.json").read_bytes()
    assert bytes_a == bytes_b, (
        f"idempotence failure with --max-commits: findings differ between runs"
    )


def test_byte_identical_with_rev(tmp_path):
    """Two runs with the same --rev -> byte-identical findings."""
    repo = make_history(tmp_path)
    # Pin to a specific commit
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    first_commit = result.stdout.strip()
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    mod = load_module()
    mod.main(["--root", str(repo), "--out-dir", str(out_a), "--rev", first_commit])
    mod.main(["--root", str(repo), "--out-dir", str(out_b), "--rev", first_commit])
    bytes_a = (out_a / "hotspot_findings.json").read_bytes()
    bytes_b = (out_b / "hotspot_findings.json").read_bytes()
    assert bytes_a == bytes_b, (
        f"idempotence failure with --rev: findings differ between runs"
    )


def test_default_run_status_line_is_deterministic(tmp_path):
    """The stdout status line JSON must also be byte-identical across runs."""
    repo = make_history(tmp_path)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    mod = load_module()

    buf_a = io.StringIO()
    with redirect_stdout(buf_a):
        rc_a = mod.main(["--root", str(repo), "--out-dir", str(out_a)])
    assert rc_a in (0, 1), f"unexpected exit {rc_a}"
    status_a = buf_a.getvalue().strip().encode()
    assert status_a, "status line must not be empty"

    buf_b = io.StringIO()
    with redirect_stdout(buf_b):
        rc_b = mod.main(["--root", str(repo), "--out-dir", str(out_b)])
    assert rc_b in (0, 1), f"unexpected exit {rc_b}"
    status_b = buf_b.getvalue().strip().encode()
    assert status_b, "status line must not be empty"

    assert status_a == status_b, (
        f"status line differs between runs:\n"
        f"  a: {status_a.decode()}\n"
        f"  b: {status_b.decode()}"
    )


def test_default_run_findings_json_is_deterministic(tmp_path):
    """The full findings JSON must be byte-identical across runs (default args)."""
    repo = make_history(tmp_path)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    mod = load_module()
    mod.main(["--root", str(repo), "--out-dir", str(out_a)])
    mod.main(["--root", str(repo), "--out-dir", str(out_b)])
    data_a = json.loads((out_a / "hotspot_findings.json").read_text())
    data_b = json.loads((out_b / "hotspot_findings.json").read_text())
    assert data_a == data_b, (
        f"findings JSON differs between default runs:\n"
        f"  a: {json.dumps(data_a, indent=2)}\n"
        f"  b: {json.dumps(data_b, indent=2)}"
    )
