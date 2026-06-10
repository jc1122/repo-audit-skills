import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "repo_hygiene_audit.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("repo_hygiene_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True, capture_output=True, check=False,
    )


def read_findings(out_dir):
    return json.loads((Path(out_dir) / "repo-hygiene_findings.json").read_text())


# -- Git helpers with pinned environment for deterministic commits --

PIN_ENV = {
    "GIT_AUTHOR_NAME": "alice",
    "GIT_AUTHOR_EMAIL": "alice@x.test",
    "GIT_COMMITTER_NAME": "alice",
    "GIT_COMMITTER_EMAIL": "alice@x.test",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00 +0000",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00 +0000",
    "HOME": "/tmp",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
}


def _g(repo, *args):
    env = dict(os.environ, **PIN_ENV)
    subprocess.run(
        ["git", "-C", str(repo), *args],
        env=env, check=True, capture_output=True, text=True,
    )


def make_dirty_repo(tmp_path):
    """Create a git repo with intentional hygiene problems.

    Returns ``(repo, symlink_ok)`` where *symlink_ok* is True when the
    broken-symlink fixture was created successfully (``os.symlink`` is
    available and did not raise).  *repo* is the :class:`Path`.

    Problems planted:
      - committed pkg/__pycache__/x.pyc  (tracked artifact)
      - .gitignore with ``*.log`` + committed debug.log  (tracked-but-ignored)
      - committed blob.bin of 2048 bytes  (oversized tracked file,
        surfaced with config ``{"max_tracked_file_bytes": 1024}``)
      - broken symlink ``dangling -> nowhere`` (when symlink supported)
      - pytest.ini + pyproject.toml [tool.pytest.ini_options]  (conflicting configs)
      - pyproject.toml version ``1.0.0`` vs CHANGELOG.md ``## 1.1.0``  (mismatch)
      - no .github/workflows  (missing CI)
      - no LICENSE  (missing license)
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")

    # tracked artifact: committed __pycache__/x.pyc
    pycache = repo / "pkg" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "x.pyc").write_bytes(b"fake pyc content\n")

    # tracked-but-ignored: gitignore *.log, commit debug.log anyway
    (repo / ".gitignore").write_text("*.log\n")
    (repo / "debug.log").write_text("should be ignored\n")

    # oversized tracked file: 2048 bytes
    (repo / "blob.bin").write_bytes(b"\x00" * 2048)

    # broken symlink (skip gracefully on platforms without os.symlink)
    symlink_ok = False
    try:
        os.symlink("nowhere", str(repo / "dangling"))
        symlink_ok = True
    except OSError:
        pass

    # conflicting pytest configs
    (repo / "pytest.ini").write_text("[pytest]\n")
    (repo / "pyproject.toml").write_text(
        '[project]\nversion = "1.0.0"\n\n'
        "[tool.pytest.ini_options]\n"
    )

    # version mismatch: CHANGELOG has different version
    (repo / "CHANGELOG.md").write_text("## 1.1.0\n\nInitial release.\n")

    # commit everything
    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "initial")

    return repo, symlink_ok


def make_clean_repo(tmp_path):
    """Create a minimal compliant git repo.

    Returns the repo Path.  Characteristics:
      - LICENSE present
      - .github/workflows/check.yml present
      - single pytest config (pyproject.toml only)
      - agreeing versions: pyproject.toml ``1.0.0``, CHANGELOG.md ``## 1.0.0``
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")

    (repo / "LICENSE").write_text("MIT License\n")

    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "check.yml").write_text(
        "name: check\non: [push]\njobs:\n  check:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - run: echo ok\n"
    )

    (repo / "pyproject.toml").write_text(
        '[project]\nversion = "1.0.0"\n\n'
        "[tool.pytest.ini_options]\n"
    )
    (repo / "CHANGELOG.md").write_text("## 1.0.0\n\nInitial release.\n")

    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "initial")

    return repo


def make_prefixed_own_repo_shape(tmp_path):
    """Create a git repo mimicking repo-A shape.

    Layout::

        shared/
        scripts/
        skills/foo/scripts/

    Intentional root-level problems OUTSIDE those prefixes:
      - missing LICENSE
      - missing .github/workflows
      - version mismatch (pyproject.toml vs CHANGELOG.md)

    The calling test MUST pass ``--source-prefix shared --source-prefix scripts
    --source-prefix skills/foo/scripts`` and assert exit 0 + [] findings,
    proving every finding (including release-hygiene) is prefix-filtered.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _g(repo, "init", "-q", "-b", "main")

    for d in ["shared", "scripts", "skills/foo/scripts"]:
        (repo / d).mkdir(parents=True)
        (repo / d / "__init__.py").write_text("")

    # root-level problems outside prefixes
    (repo / "pyproject.toml").write_text(
        '[project]\nversion = "2.0.0"\n\n[tool.pytest.ini_options]\n'
    )
    (repo / "CHANGELOG.md").write_text("## 1.0.0\n\nOld.\n")
    (repo / "pytest.ini").write_text("[pytest]\n")
    # no LICENSE, no .github/workflows

    _g(repo, "add", "-A")
    _g(repo, "commit", "-q", "-m", "initial")

    return repo
