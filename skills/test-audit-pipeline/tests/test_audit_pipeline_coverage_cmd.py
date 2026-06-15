"""Tests for the xdist-gated coverage command builder + detector (Phase 3 C1)."""

import importlib.util
import sys
from pathlib import Path

from helpers import load_module

ap = load_module()


def test_build_coverage_cmd_omits_n_without_xdist():
    cmd = ap._build_coverage_cmd(
        python="py", test_marker="not slow", cov_source="scripts",
        cov_json=Path("/tmp/cov.json"), xdist_available=False,
    )
    assert "-n" not in cmd
    assert cmd[:5] == ["py", "-m", "pytest", "-m", "not slow"]
    assert "--cov=scripts" in cmd
    assert "--cov-branch" in cmd
    assert "--cov-report=json:/tmp/cov.json" in cmd
    assert cmd[-1] == "-q"


def test_build_coverage_cmd_includes_n_with_xdist():
    cmd = ap._build_coverage_cmd(
        python="py", test_marker="not slow", cov_source="scripts",
        cov_json=Path("/tmp/cov.json"), xdist_available=True,
    )
    # exactly one consecutive ["-n", "0"] pair
    i = cmd.index("-n")
    assert cmd[i + 1] == "0"
    assert cmd.count("-n") == 1


def test_xdist_available_false_for_bogus_interpreter():
    assert ap._xdist_available("/nonexistent/python-xyz") is False


def test_xdist_available_matches_current_env():
    expected = importlib.util.find_spec("xdist") is not None
    assert ap._xdist_available(sys.executable) is expected
