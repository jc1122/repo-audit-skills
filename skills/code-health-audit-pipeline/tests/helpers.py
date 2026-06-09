import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "code_health_pipeline.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("code_health_pipeline", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False)


def finding(**kw):
    base = {
        "id": "x", "leaf": "complexity", "signal": "DELETE", "severity": "high",
        "path": "pkg/a.py", "location": {"line_start": 1, "line_end": 1, "symbol": "f"},
        "metric": {"name": "m", "value": 0, "threshold": 0},
        "evidence": {"tool": "t", "raw": ""}, "confidence": "high", "suggested_action": "y",
    }
    base.update(kw)
    return base
