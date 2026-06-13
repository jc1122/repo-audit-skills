"""Tests for ``scripts/check_growth.py`` — the growth gate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_growth.py"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _load_mod():
    """Import ``check_growth`` as a fresh module via importlib."""
    spec = importlib.util.spec_from_file_location("check_growth", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# baseline_rev()
# ---------------------------------------------------------------------------


def test_baseline_rev_returns_string_starting_with_v():
    """``baseline_rev()`` returns a git tag that starts with ``v``."""
    mod = _load_mod()
    rev = mod.baseline_rev()
    assert isinstance(rev, str)
    assert len(rev) > 1
    assert rev.startswith("v"), f"expected tag starting with 'v', got: {rev!r}"


# ---------------------------------------------------------------------------
# decide_from_findings_file()
# ---------------------------------------------------------------------------


class TestDecideFromFindingsFile:
    """Cover the JSON-finding decision helper directly."""

    def test_empty_list_passes(self, tmp_path):
        """An empty findings list means no unsuppressed findings → pass."""
        mod = _load_mod()
        f = tmp_path / "findings.json"
        f.write_text("[]", encoding="utf-8")

        exit_code, payload = mod.decide_from_findings_file(f)
        assert exit_code == 0
        assert payload["status"] == "pass"
        assert payload["count"] == 0

    def test_nonempty_list_fails(self, tmp_path):
        """A non-empty findings list means unsuppressed findings → fail."""
        mod = _load_mod()
        f = tmp_path / "findings.json"
        findings = [
            {
                "id": "abc123",
                "leaf": "growth-audit",
                "signal": "RESTRUCTURE",
                "severity": "low",
                "path": "<repo>",
                "location": {"line_start": 0, "line_end": 0, "symbol": "net_loc_growth"},
                "metric": {"name": "net_loc_growth", "value": 100.0, "threshold": 50.0},
                "evidence": {"tool": "git", "raw": "…"},
                "confidence": "high",
                "suggested_action": "Review growth",
            }
        ]
        f.write_text(json.dumps(findings), encoding="utf-8")

        exit_code, payload = mod.decide_from_findings_file(f)
        assert exit_code == 1
        assert payload["status"] == "fail"
        assert payload["count"] == 1

    def test_missing_file_is_hard_error(self, tmp_path):
        """A missing findings file is a hard gate error (exit 2)."""
        mod = _load_mod()
        f = tmp_path / "nonexistent.json"

        exit_code, payload = mod.decide_from_findings_file(f)
        assert exit_code == 2
        assert payload["status"] == "error"

    def test_invalid_json_is_hard_error(self, tmp_path):
        """Unparseable JSON is a hard gate error."""
        mod = _load_mod()
        f = tmp_path / "findings.json"
        f.write_text("this is not json", encoding="utf-8")

        exit_code, payload = mod.decide_from_findings_file(f)
        assert exit_code == 2
        assert payload["status"] == "error"

    def test_json_object_not_list_is_hard_error(self, tmp_path):
        """A JSON object (not a list) is a hard gate error."""
        mod = _load_mod()
        f = tmp_path / "findings.json"
        f.write_text('{"not": "a list"}', encoding="utf-8")

        exit_code, payload = mod.decide_from_findings_file(f)
        assert exit_code == 2
        assert payload["status"] == "error"
