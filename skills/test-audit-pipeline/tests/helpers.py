import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "audit_pipeline.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    """Import audit_pipeline.py as module 'audit_pipeline'."""
    spec = importlib.util.spec_from_file_location("audit_pipeline", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["audit_pipeline"] = mod
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    """Run audit_pipeline.py as a subprocess and return CompletedProcess."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def read_json(path):
    """Read a JSON file, return parsed content."""
    return json.loads(Path(path).read_text())
