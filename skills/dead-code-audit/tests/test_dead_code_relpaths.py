import json
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]


def test_no_absolute_paths_in_findings(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "m.py").write_text("import os\n\ndef unused():\n    return 1\n")
    out = tmp_path / "out"
    subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "dead_code_audit.py"),
            "--root",
            str(tmp_path),
            "--out-dir",
            str(out),
            "--source-prefix",
            "pkg",
        ],
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    data = json.loads((out / "dead-code_findings.json").read_text())
    assert data, "expected some findings"
    assert all(not f["path"].startswith("/") for f in data), [f["path"] for f in data]
