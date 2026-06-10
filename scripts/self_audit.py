#!/usr/bin/env python3
"""Run the code-health pipeline over this package's PRODUCTION
code; emit a normalized snapshot."""

from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = (
    ROOT
    / "skills"
    / "code-health-audit-pipeline"
    / "scripts"
    / "code_health_pipeline.py"
)
SNAPSHOT = ROOT / "scripts" / "self_audit_snapshot.json"


def _prefixes() -> list[str]:
    pres = ["shared", "scripts"]
    for d in sorted((ROOT / "skills").iterdir()):
        if (d / "scripts").is_dir():
            pres.append(f"skills/{d.name}/scripts")
    return pres


def run(out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(PIPELINE),
        "--root",
        str(ROOT),
        "--out-dir",
        str(out_dir),
    ]
    for p in _prefixes():
        cmd += ["--source-prefix", p]
    subprocess.run(cmd, text=True, capture_output=True, timeout=600, check=False)
    summary = json.loads((out_dir / "code_health_summary.json").read_text())
    return sorted(
        (
            {
                "leaf": f["leaf"],
                "path": f["path"],
                "symbol": f["location"]["symbol"],
                "metric": f["metric"]["name"],
            }
            for f in summary.get("findings", [])
        ),
        key=lambda d: (d["path"], d["leaf"], d["metric"], d["symbol"]),
    )


def main() -> int:
    findings = run(ROOT / ".self_audit_out")
    SNAPSHOT.write_text(json.dumps(findings, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "ok", "count": len(findings)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
