import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "coverage_gap_audit.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"

# C3 pilot: normal import (not spec_from_file) for mutmut — see c3-evidence
sys.path.insert(0, str(SKILL_ROOT / "scripts"))


def load_module():
    import coverage_gap_audit
    return coverage_gap_audit


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False
    )


def read_findings(out_dir):
    return json.loads((Path(out_dir) / "coverage-gap_findings.json").read_text())
