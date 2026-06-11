"""Shared ratchet-gate verdict logic.

Reusable by check scripts (check_self_audit.py and future gates) that compare
a normalized leaf-audit snapshot against a checked-in baseline.
"""

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GateSpec:
    """Per-gate configuration bundle (immutable)."""

    leaf_cmd: list[str]
    findings_file: str
    snapshot_path: str
    baseline_path: str
    description: str


def production_prefixes(root: Path) -> list[str]:
    """Prod scope: ``shared``, ``scripts``, and each skill's ``scripts/`` dir."""
    pres = ["shared", "scripts"]
    for d in sorted((root / "skills").iterdir()):
        if (d / "scripts").is_dir():
            pres.append(f"skills/{d.name}/scripts")
    return pres


def identities(findings: list[dict]) -> set[tuple]:
    """Return a deduplicated set of identity tuples for *findings*."""
    return {tuple(sorted(d.items())) for d in findings}


def normalize_findings(raw: list[dict]) -> list[dict]:
    """Map raw leaf-finding dicts to a normalized 4-key shape sorted by
    ``(path, leaf, metric, symbol)``.  Extra keys are silently dropped."""
    return sorted(
        (
            {
                "leaf": f["leaf"],
                "path": f["path"],
                "symbol": f["location"]["symbol"],
                "metric": f["metric"]["name"],
            }
            for f in raw
        ),
        key=lambda d: (d["path"], d["leaf"], d["metric"], d["symbol"]),
    )


def verdict(
    current: list[dict],
    baseline: list[dict],
    *,
    baseline_path: str,
) -> tuple[int, dict]:
    """Compare *current* (normalized) findings against the *baseline*.

    Returns ``(exit_code, payload)`` where exit_code 0 means pass and
    exit_code 1 means fail (new findings or stale baseline entries).
    """
    base = identities(baseline)
    # Regressions first: findings present now but absent from the baseline.
    regressions = [d for d in current if tuple(sorted(d.items())) not in base]
    if regressions:
        return 1, {"status": "fail", "new_findings": regressions}
    # Then stale entries: baseline ids the audit no longer produces.
    stale = [dict(t) for t in sorted(base - identities(current))]
    if stale:
        return 1, {
            "status": "fail",
            "stale_baseline": stale,
            "message": (
                "baseline entries no longer produced by the audit; "
                f"remove them from {baseline_path} in the same commit"
            ),
        }
    return 0, {
        "status": "pass",
        "count": len(current),
        "baseline": len(baseline),
    }


def _current_from_leaf(spec: GateSpec) -> list[dict] | None:
    """Run *spec.leaf_cmd*, read raw findings, normalize, write snapshot.

    Returns the normalized list, or ``None`` after printing an error
    payload when the leaf exits with returncode 2.
    """
    proc = subprocess.run(
        spec.leaf_cmd, text=True, capture_output=True, timeout=600, check=False
    )
    if proc.returncode == 2:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": (
                        f"leaf audit failed with returncode 2\n"
                        f"stdout: {proc.stdout}\n"
                        f"stderr: {proc.stderr}"
                    ),
                    "leaf_returncode": 2,
                },
                indent=2,
            )
        )
        return None

    raw_text = Path(spec.findings_file).read_text()
    raw_data = json.loads(raw_text)
    raw_findings: list[dict]
    if isinstance(raw_data, list):
        raw_findings = raw_data
    else:
        raw_findings = raw_data.get("findings", [])

    current = normalize_findings(raw_findings)
    Path(spec.snapshot_path).write_text(
        json.dumps(current, indent=2, sort_keys=True) + "\n"
    )
    return current


def gate_main(argv: list[str] | None, spec: GateSpec) -> int:
    """Run a ratchet-gate check.

    *argv* allows ``--snapshot`` / ``--baseline`` test overrides.
    *spec* bundles the leaf command, file paths, and description.
    """
    parser = argparse.ArgumentParser(description=spec.description)
    parser.add_argument(
        "--snapshot",
        help="Existing snapshot JSON (testing only — skips the leaf).",
    )
    parser.add_argument(
        "--baseline",
        help="Alternate baseline JSON (testing only).",
    )
    args = parser.parse_args(argv)

    # Obtain current (normalized) findings
    if args.snapshot:
        current = json.loads(Path(args.snapshot).read_text())
    else:
        current = _current_from_leaf(spec)
        if current is None:
            return 1

    # Load baseline
    baseline = json.loads(Path(args.baseline or spec.baseline_path).read_text())

    # Verdict & output
    code, payload = verdict(current, baseline, baseline_path=spec.baseline_path)
    print(json.dumps(payload, indent=2))
    return code
