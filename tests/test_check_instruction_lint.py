"""Tests for the deterministic instruction-lint gate (X1.1).

Covers the two finding types:
  * instruction_dead_command  — a fenced family-script command whose script is
    missing or does not answer ``--help``.
  * instruction_missing_section — a SKILL.md missing a required heading
    (``## Overview`` / ``## Limits``).

Stdlib-only fixtures are written under ``tmp_path``; no real repo state is read.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_instruction_lint as cil  # noqa: E402


def _write_skill(root: Path, rel_dir: str, body: str) -> Path:
    skill_dir = root / rel_dir
    (skill_dir / "scripts").mkdir(parents=True, exist_ok=True)
    skill = skill_dir / "SKILL.md"
    skill.write_text(body, encoding="utf-8")
    return skill


def _categories(findings: list[dict]) -> list[str]:
    return sorted(f["location"]["symbol"] for f in findings)


# ----------------------------------------------------------------- valid skill


def test_valid_skill_skeleton_has_no_findings(tmp_path: Path) -> None:
    """A non-Python-flavoured skill with both required sections and a fenced
    command whose first token is NOT a family script (``ls -la``) yields zero
    findings."""
    _write_skill(
        tmp_path,
        "skills/good-skill",
        "# good-skill\n"
        "\n"
        "## Overview\n"
        "A perfectly valid skill.\n"
        "\n"
        "## Limits\n"
        "Advisory only.\n"
        "\n"
        "## Quick Start\n"
        "```bash\n"
        "ls -la\n"
        "git status\n"
        "```\n",
    )

    findings = cil.scan(tmp_path / "skills")

    assert findings == []


def test_valid_skill_with_resolvable_helpful_script(tmp_path: Path) -> None:
    """A fenced command pointing at an existing script that answers ``--help``
    produces no finding."""
    skill = _write_skill(
        tmp_path,
        "skills/has-script",
        "# has-script\n"
        "\n"
        "## Overview\n"
        "Body.\n"
        "\n"
        "## Limits\n"
        "Body.\n"
        "\n"
        "```bash\n"
        "python3 scripts/tool.py --root .\n"
        "```\n",
    )
    helpful = skill.parent / "scripts" / "tool.py"
    helpful.write_text(
        "import argparse\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--root')\n"
        "p.parse_args()\n",
        encoding="utf-8",
    )

    findings = cil.scan(tmp_path / "skills")

    assert findings == []


# ----------------------------------------------------------------- degenerate


def test_degenerate_doc_yields_exactly_two_findings(tmp_path: Path) -> None:
    """A SKILL.md quoting a missing script and missing ``## Limits`` yields
    exactly one ``instruction_dead_command`` and one
    ``instruction_missing_section``."""
    _write_skill(
        tmp_path,
        "skills/bad-skill",
        "# bad-skill\n"
        "\n"
        "## Overview\n"
        "Has an overview but no limits section.\n"
        "\n"
        "```bash\n"
        "python3 scripts/gone.py --help\n"
        "```\n",
    )

    findings = cil.scan(tmp_path / "skills")

    assert len(findings) == 2, findings
    cats = _categories(findings)
    assert cats == ["instruction_dead_command", "instruction_missing_section"]

    dead = next(
        f for f in findings if f["location"]["symbol"] == "instruction_dead_command"
    )
    missing = next(
        f
        for f in findings
        if f["location"]["symbol"] == "instruction_missing_section"
    )

    assert dead["signal"] == "LINT"
    assert dead["leaf"] == "instruction-lint"
    assert dead["metric"]["name"] == "instruction_dead_command"
    assert "scripts/gone.py" in dead["message"]

    assert missing["metric"]["name"] == "instruction_missing_section"
    assert "Limits" in missing["message"]


def test_dead_command_for_script_that_fails_help(tmp_path: Path) -> None:
    """An existing script that exits non-zero on ``--help`` is a dead command."""
    skill = _write_skill(
        tmp_path,
        "skills/broken-help",
        "# broken-help\n"
        "\n"
        "## Overview\n"
        "x\n"
        "\n"
        "## Limits\n"
        "x\n"
        "\n"
        "```bash\n"
        "python3 scripts/broken.py --help\n"
        "```\n",
    )
    (skill.parent / "scripts" / "broken.py").write_text(
        "import sys\nsys.exit(3)\n", encoding="utf-8"
    )

    findings = cil.scan(tmp_path / "skills")

    assert _categories(findings) == ["instruction_dead_command"]


def test_missing_both_sections_yields_two_section_findings(tmp_path: Path) -> None:
    """A SKILL.md missing both required sections (and no commands) yields two
    ``instruction_missing_section`` findings."""
    _write_skill(
        tmp_path,
        "skills/empty",
        "# empty\n\nNo required headings here.\n",
    )

    findings = cil.scan(tmp_path / "skills")

    cats = [f["location"]["symbol"] for f in findings]
    assert cats == ["instruction_missing_section", "instruction_missing_section"]
    msgs = sorted(f["message"] for f in findings)
    assert any("Overview" in m for m in msgs)
    assert any("Limits" in m for m in msgs)


# ----------------------------------------------------------------- gate / CLI


def test_gate_main_help_works(capsys) -> None:
    """``--help`` must exit cleanly (argparse SystemExit 0)."""
    try:
        cil.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:  # pragma: no cover - argparse always raises on --help
        raise AssertionError("--help did not raise SystemExit")


def test_gate_green_when_findings_match_baseline(tmp_path: Path) -> None:
    """Gate returns 0 when the snapshot equals the baseline."""
    snap = tmp_path / "snap.json"
    base = tmp_path / "base.json"
    rows = '[{"leaf": "instruction-lint", "metric": "instruction_missing_section", '
    rows += '"path": "skills/x/SKILL.md", "symbol": "instruction_missing_section"}]'
    snap.write_text(rows, encoding="utf-8")
    base.write_text(rows, encoding="utf-8")

    code = cil.main(["--snapshot", str(snap), "--baseline", str(base)])

    assert code == 0


def test_gate_red_when_new_finding_absent_from_baseline(tmp_path: Path) -> None:
    """Gate returns nonzero when a finding is not in the baseline."""
    snap = tmp_path / "snap.json"
    base = tmp_path / "base.json"
    snap.write_text(
        '[{"leaf": "instruction-lint", "metric": "instruction_dead_command", '
        '"path": "skills/x/SKILL.md", "symbol": "instruction_dead_command"}]',
        encoding="utf-8",
    )
    base.write_text("[]", encoding="utf-8")

    code = cil.main(["--snapshot", str(snap), "--baseline", str(base)])

    assert code == 1
