import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "complexity_audit.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("complexity_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["complexity_audit"] = mod
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False)


def read_findings(out_dir):
    return json.loads((Path(out_dir) / "complexity_findings.json").read_text())
