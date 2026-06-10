import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "adversarial"
LEAVES = ["complexity-audit/scripts/complexity_audit.py","duplication-audit/scripts/duplication_audit.py",
          "dead-code-audit/scripts/dead_code_audit.py","structure-audit/scripts/structure_audit.py",
          "quality-audit/scripts/quality_audit.py"]
def test_every_leaf_survives_adversarial_inputs(tmp_path):
    for leaf in LEAVES:
        proc = subprocess.run([sys.executable, str(ROOT/"skills"/leaf), "--root", str(CORPUS),
                               "--out-dir", str(tmp_path/leaf.split("/")[0])],
                              text=True, capture_output=True, timeout=180)
        assert proc.returncode in (0,1,2), f"{leaf} rc={proc.returncode}"
        assert "Traceback (most recent call last)" not in proc.stderr, f"{leaf}:\n{proc.stderr}"
