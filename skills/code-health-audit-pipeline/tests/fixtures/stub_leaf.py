import argparse
import json
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--root")
p.add_argument("--out-dir")
p.add_argument("--source-prefix", action="append", default=[])
a = p.parse_args()
out = Path(a.out_dir)
out.mkdir(parents=True, exist_ok=True)
findings = [{
    "id": "stub1", "leaf": "stub", "signal": "DELETE", "severity": "high",
    "path": "pkg/a.py", "location": {"line_start": 1, "line_end": 1, "symbol": "f"},
    "metric": {"name": "m", "value": 0, "threshold": 0},
    "evidence": {"tool": "stub", "raw": ""}, "confidence": "high", "suggested_action": "y",
}]
(out / "stub_findings.json").write_text(json.dumps(findings))
sys.exit(1)
