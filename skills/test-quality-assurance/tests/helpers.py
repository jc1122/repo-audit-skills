import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "audit_test_quality.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_test_quality", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["audit_test_quality"] = mod
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def read_json(out_path):
    return json.loads(Path(out_path).read_text())


def read_md(out_path):
    return Path(out_path).read_text()
