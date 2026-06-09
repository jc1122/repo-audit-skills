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
(out / "empty_findings.json").write_text("[]")
sys.exit(0)
