import subprocess, sys
from pathlib import Path
SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL/"scripts"/"complexity_audit.py"; DIRTY = SKILL/"tests"/"fixtures"/"dirty"; FINDINGS="complexity_findings.json"
def _run(out):
    subprocess.run([sys.executable,str(SCRIPT),"--root",str(DIRTY),"--out-dir",str(out),"--source-prefix","pkg"],
                   text=True,capture_output=True,timeout=180,check=False)
    return (out/FINDINGS).read_bytes()
def test_byte_identical_across_runs(tmp_path):
    assert _run(tmp_path/"a") == _run(tmp_path/"b")
