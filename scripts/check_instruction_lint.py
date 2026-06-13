#!/usr/bin/env python3
"""check:instruction-lint — deterministic SKILL.md command/section drift gate.

Detects instruction drift in ``SKILL.md`` files:

* ``instruction_dead_command`` — a fenced command whose first resolvable token is
  a family script (``python3 scripts/<x>.py``, ``scripts/<x>.sh``, or any path
  ending in ``.py``/``.sh`` under the repo) that does NOT exist, or that exists
  but does NOT answer ``--help`` (non-zero exit / exception).
* ``instruction_missing_section`` — a ``SKILL.md`` missing a required literal
  heading (``## Overview`` / ``## Limits``).

Findings use the shared code-health schema (id, leaf, signal, severity, path,
location, metric, evidence, confidence, suggested_action). Non-family commands
(``ls``, ``git``, ``npm``, generic shell) are ignored.

The script doubles as a ratchet gate: ``main()`` compares the current findings
against a checked-in baseline and returns nonzero only when findings exceed the
baseline set (mirroring the sibling gates via ``gate_common.verdict``).

Stdlib only, Python >=3.11. Never mutates source; ``--help`` probes run in a
subprocess with a short timeout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_common import verdict  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = "scripts/instruction_lint_baseline.json"
BASELINE = ROOT / BASELINE_PATH
SNAPSHOT = ROOT / "scripts" / "instruction_lint_snapshot.json"

LEAF = "instruction-lint"
REQUIRED_SECTIONS = ("## Overview", "## Limits")
HELP_TIMEOUT_S = 20

# Fenced code-block fence (``` or ~~~), capturing an optional info string.
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})\s*([^\s`~]*)")
# A token that looks like a family script path ending in .py or .sh.
_SCRIPT_TOKEN = re.compile(r"^[\w./$~-]+\.(py|sh)$")
# Known interpreters whose *next* token is the script path.
_INTERPRETERS = {"python", "python3", "python3.11", "python3.12", "bash", "sh"}


# --------------------------------------------------------------------- findings


def _finding(
    category: str,
    path: str,
    line: int,
    texts: tuple[str, str, str],
) -> dict:
    """Build one shared-schema finding dict.

    ``category`` (``instruction_dead_command`` / ``instruction_missing_section``)
    is carried in both ``metric.name`` and ``location.symbol`` so it survives the
    gate's normalized 4-key projection (``leaf, path, symbol, metric``).
    ``texts`` is ``(message, suggested_action, evidence)``.
    """
    message, suggested_action, evidence = texts
    key = f"{LEAF}|{path}|{category}|{line}|{message}"
    stable_id = hashlib.sha1(key.encode("utf-8"), usedforsecurity=False).hexdigest()[
        :16
    ]
    return {
        "id": stable_id,
        "leaf": LEAF,
        "signal": "LINT",
        "severity": "medium",
        "path": path,
        "location": {"line_start": line, "line_end": line, "symbol": category},
        "metric": {"name": category, "value": 1, "threshold": 0},
        "evidence": {"tool": "instruction-lint", "raw": evidence},
        "confidence": "high",
        "message": message,
        "suggested_action": suggested_action,
    }


# --------------------------------------------------------------------- parsing


def _toggle_fence(raw: str, state: tuple[bool, str]) -> tuple[bool, str] | None:
    """If *raw* is a fence delimiter for the current *state* ``(in_fence,
    marker)``, return the new state; otherwise ``None``."""
    in_fence, marker = state
    m = _FENCE.match(raw)
    if not m or (in_fence and not raw.strip().startswith(marker)):
        return None
    return (False, "") if in_fence else (True, m.group(1))


def _fenced_command_lines(text: str) -> list[tuple[int, str]]:
    """Return ``(line_number, command_line)`` for every non-blank, non-comment
    line inside fenced code blocks, with shell line-continuations joined."""
    out: list[tuple[int, str]] = []
    state = (False, "")
    pending: tuple[int, str] | None = None
    for idx, raw in enumerate(text.splitlines(), start=1):
        toggled = _toggle_fence(raw, state)
        if toggled is not None:
            state = toggled
            continue
        line = raw.strip()
        if not state[0] or not line or line.startswith("#"):
            continue
        start, line = (pending[0], pending[1] + " " + line) if pending else (idx, line)
        pending = None
        if line.endswith("\\"):
            pending = (start, line[:-1].strip())
            continue
        out.append((start, line))
    return out


def _first_script_token(command: str) -> str | None:
    """Extract the family-script path token from *command*, or ``None``.

    Handles ``python3 scripts/x.py ...``, a bare ``scripts/x.sh ...``, or any
    leading token that is a path ending in ``.py``/``.sh``. Quoted tokens
    (``"$DIR/x.py"``) are unquoted. Returns the raw path token (still possibly
    containing ``$VAR`` / ``~``), or ``None`` for non-family commands.
    """
    tokens = command.split()
    if not tokens:
        return None
    first = tokens[0]
    if first in _INTERPRETERS:
        if len(tokens) < 2:
            return None
        candidate = tokens[1]
    else:
        candidate = first
    candidate = candidate.strip("\"'")
    if _SCRIPT_TOKEN.match(candidate):
        return candidate
    return None


def _resolve_script(token: str, skill_dir: Path) -> Path | None:
    """Resolve *token* to a filesystem path relative to the skill dir then the
    repo root. Returns ``None`` when the token contains an unexpandable
    placeholder (``$VAR``) that we cannot resolve deterministically."""
    if "$" in token:
        return None  # environment-dependent; not statically resolvable
    cleaned = token
    if cleaned.startswith("~"):
        return None  # home-relative; not a family script under the repo
    candidate = (skill_dir / cleaned).resolve()
    if candidate.exists():
        return candidate
    repo_candidate = (ROOT / cleaned).resolve()
    return repo_candidate


def _interpreter_for(path: Path) -> list[str]:
    """Return the argv prefix used to probe *path* with ``--help``."""
    if path.suffix == ".sh":
        return ["bash", str(path)]
    return [sys.executable, str(path)]


def _probe_help(path: Path) -> tuple[bool, str]:
    """Run ``<interpreter> <path> --help``; return ``(ok, reason)``."""
    cmd = _interpreter_for(path) + ["--help"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=HELP_TIMEOUT_S,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - report any launch failure
        return False, f"--help raised {type(exc).__name__}: {exc}"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip()[-200:]
        return False, f"--help exited {proc.returncode}: {tail}"
    return True, ""


# --------------------------------------------------------------------- scanning


def _rel(path: Path) -> str:
    """Repo-relative POSIX path string for *path* (falls back to absolute)."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _scan_commands(skill: Path, text: str) -> list[dict]:
    """Emit ``instruction_dead_command`` findings for *skill*."""
    findings: list[dict] = []
    rel = _rel(skill)
    skill_dir = skill.parent
    for line_no, command in _fenced_command_lines(text):
        token = _first_script_token(command)
        if token is None:
            continue
        resolved = _resolve_script(token, skill_dir)
        if resolved is None:
            continue  # not statically resolvable; ignore
        if not resolved.exists():
            findings.append(
                _finding(
                    "instruction_dead_command",
                    rel,
                    line_no,
                    (
                        f"fenced command references missing family script "
                        f"{token!r}",
                        f"fix or remove the command for {token!r} in {rel}",
                        command,
                    ),
                )
            )
            continue
        ok, reason = _probe_help(resolved)
        if not ok:
            findings.append(
                _finding(
                    "instruction_dead_command",
                    rel,
                    line_no,
                    (
                        f"family script {token!r} does not answer --help "
                        f"({reason})",
                        f"ensure {token!r} supports --help or update the doc",
                        command,
                    ),
                )
            )
    return findings


def _scan_sections(skill: Path, text: str) -> list[dict]:
    """Emit ``instruction_missing_section`` findings for *skill*."""
    findings: list[dict] = []
    rel = _rel(skill)
    headings = {
        line.strip()
        for line in text.splitlines()
        if line.lstrip().startswith("## ")
    }
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            name = section.removeprefix("## ")
            findings.append(
                _finding(
                    "instruction_missing_section",
                    rel,
                    1,
                    (
                        f"SKILL.md is missing required section {name!r}",
                        f"add a '{section}' section to {rel}",
                        f"missing heading: {section}",
                    ),
                )
            )
    return findings


def scan(root: Path) -> list[dict]:
    """Scan ``root`` for ``**/SKILL.md`` and return shared-schema findings,
    sorted deterministically by ``(path, symbol, line_start)``."""
    findings: list[dict] = []
    for skill in sorted(Path(root).glob("**/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        findings.extend(_scan_sections(skill, text))
        findings.extend(_scan_commands(skill, text))
    return sorted(
        findings,
        key=lambda f: (f["path"], f["location"]["symbol"], f["location"]["line_start"]),
    )


def normalize(findings: list[dict]) -> list[dict]:
    """Project full findings onto the gate's 4-key baseline shape
    (``leaf, path, symbol, metric``) sorted like ``gate_common``."""
    return sorted(
        (
            {
                "leaf": f["leaf"],
                "path": f["path"],
                "symbol": f["location"]["symbol"],
                "metric": f["metric"]["name"],
            }
            for f in findings
        ),
        key=lambda d: (d["path"], d["leaf"], d["metric"], d["symbol"]),
    )


# --------------------------------------------------------------------- CLI/gate


def _write_outputs(findings: list[dict], out: str | None, fmt: str) -> None:
    """Write full findings to ``--out`` (JSON) when requested."""
    if not out:
        return
    if fmt == "json":
        Path(out).write_text(
            json.dumps(findings, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:  # pragma: no cover - only json supported
        raise SystemExit(f"unsupported --format: {fmt}")


def main(argv: list[str] | None = None) -> int:
    """Scan and ratchet-gate the instruction-lint findings.

    In normal mode, scans ``--root`` and compares normalized findings against
    the baseline, returning nonzero only on regressions / stale entries. The
    ``--snapshot`` / ``--baseline`` overrides let tests drive the verdict
    directly (mirroring the sibling gates).
    """
    parser = argparse.ArgumentParser(
        description="Deterministic SKILL.md command/section drift gate."
    )
    parser.add_argument(
        "--root",
        default="skills",
        help="Directory scanned for **/SKILL.md (default: skills).",
    )
    parser.add_argument("--out", help="Write full findings JSON to this path.")
    parser.add_argument(
        "--format", default="json", choices=["json"], help="Output format."
    )
    parser.add_argument(
        "--baseline",
        help=f"Alternate baseline JSON (default: {BASELINE_PATH}).",
    )
    parser.add_argument(
        "--snapshot",
        help="Existing normalized snapshot JSON (testing only — skips the scan).",
    )
    args = parser.parse_args(argv)

    if args.snapshot:
        current = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    else:
        root = Path(args.root)
        if not root.is_absolute():
            root = ROOT / root
        findings = scan(root)
        _write_outputs(findings, args.out, args.format)
        current = normalize(findings)
        SNAPSHOT.write_text(
            json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    baseline = json.loads(
        Path(args.baseline or BASELINE).read_text(encoding="utf-8")
    )
    code, payload = verdict(current, baseline, baseline_path=BASELINE_PATH)
    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
