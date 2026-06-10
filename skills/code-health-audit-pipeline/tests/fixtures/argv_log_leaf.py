import argparse
import json
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--root")
p.add_argument("--out-dir")
p.add_argument("--source-prefix", action="append", default=[])
p.add_argument("--coverage-json", default=None)
a = p.parse_args()
out = Path(a.out_dir)
out.mkdir(parents=True, exist_ok=True)

log = {"argv": sys.argv[:], "has_coverage_json": a.coverage_json is not None}
(out / "argv_log.json").write_text(json.dumps(log))

findings = [{
    "id": "al1", "leaf": "argv-log", "signal": "TEST", "severity": "low",
    "path": "pkg/a.py", "location": {"line_start": 1, "line_end": 1, "symbol": "f"},
    "metric": {"name": "m", "value": 0, "threshold": 0},
    "evidence": {"tool": "argv-log", "raw": ""}, "confidence": "low", "suggested_action": "y",
}]
(out / "argv_log_findings.json").write_text(json.dumps(findings))
sys.exit(0)
