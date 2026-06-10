import importlib.util
import json
import os
import subprocess as sp
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "hotspot_audit.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"

PIN_ENV = {
    "GIT_AUTHOR_NAME": "alice", "GIT_AUTHOR_EMAIL": "alice@x.test",
    "GIT_COMMITTER_NAME": "alice", "GIT_COMMITTER_EMAIL": "alice@x.test",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00 +0000",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00 +0000",
    "HOME": "/tmp", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
}


def _g(repo, *args, author=None):
    env = dict(os.environ, **PIN_ENV)
    if author:
        env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = author
        env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = f"{author}@x.test"
    sp.run(["git", "-C", str(repo), *args], env=env, check=True, capture_output=True, text=True)


def make_history(tmp_path):
    """8 deterministic commits: hot.py churns 6x at 200 nloc (product 1200 >= 1000);
    a.py+b.py co-change 5x; hot.py is also the knowledge fixture (6/6 alice commits,
    surfaced only via a lowered min_author_commits config); bob touches only b.py once.

    Fixture math (recomputed 2026-06-10):
      a.py churn: 5 (commits c0..c4)
      b.py churn: 6 (commits c0..c4 + bob-touch)
      co-changes a.py<->b.py: 5 (commits c0..c4)
      ratio = 5 / min(5, 6) = 1.0

    hot.py: 200 nloc x 6 churn = 1200.0 product
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")
    for i in range(6):
        (repo / "hot.py").write_text(
            "\n".join(f"x{j} = {j}  # rev {i}" for j in range(200)) + "\n")
        if i < 5:
            (repo / "a.py").write_text(f"a = {i}\n")
            (repo / "b.py").write_text(f"b = {i}\n")
        _g(repo, "add", "-A")
        _g(repo, "commit", "-q", "-m", f"c{i}")
    (repo / "b.py").write_text("b = 99\n")
    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "bob-touch", author="bob")
    (repo / "calm.py").write_text("calm = 1\n")
    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "calm")
    return repo


def make_clean_repo(tmp_path):
    """Minimal git repo that produces zero findings (all files below thresholds)."""
    repo = tmp_path / "clean"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")
    (repo / "small.py").write_text("x = 1\n")
    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "initial")
    return repo


def load_module():
    spec = importlib.util.spec_from_file_location("hotspot_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return sp.run(
        [sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False
    )


def read_findings(out_dir):
    return json.loads((Path(out_dir) / "hotspot_findings.json").read_text())
