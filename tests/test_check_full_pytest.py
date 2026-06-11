import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_full_pytest.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_full_pytest", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_suite_dirs_discovers_root_and_skill_tests(tmp_path, monkeypatch):
    mod = _load()
    (tmp_path / "tests").mkdir()
    (tmp_path / "skills" / "alpha" / "tests").mkdir(parents=True)
    (tmp_path / "skills" / "beta" / "tests").mkdir(parents=True)
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    assert [path.relative_to(tmp_path).as_posix() for path in mod.suite_dirs()] == [
        "tests",
        "skills/alpha/tests",
        "skills/beta/tests",
    ]


def test_run_suite_executes_in_isolated_cwd(tmp_path):
    mod = _load()
    suite = tmp_path / "tests"
    suite.mkdir()
    (suite / "test_ok.py").write_text(
        "from pathlib import Path\n\n"
        "def test_cwd_is_suite_parent():\n"
        "    assert Path.cwd().name == 'suite-root'\n",
        encoding="utf-8",
    )
    cwd = tmp_path / "suite-root"
    cwd.mkdir()
    suite.rename(cwd / "tests")

    class Queue:
        def __init__(self):
            self.items = []

        def put(self, item):
            self.items.append(item)

    queue = Queue()
    old_cwd = os.getcwd()
    old_path = list(sys.path)
    try:
        mod._run_suite(str(cwd / "tests"), str(cwd), queue)
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_path

    code, stdout, stderr = queue.items[0]
    assert code == 0
    assert "1 passed" in stdout
    assert stderr == ""


def test_main_writes_snapshot_and_reports_failures(tmp_path, monkeypatch, capsys):
    mod = _load()
    suites = [tmp_path / "tests", tmp_path / "skills" / "broken" / "tests"]
    for suite in suites:
        suite.mkdir(parents=True)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "SNAPSHOT", tmp_path / "full_pytest_snapshot.json")
    monkeypatch.setattr(mod, "suite_dirs", lambda: suites)

    class FakeQueue:
        def __init__(self):
            self.item = None

        def put(self, item):
            self.item = item

        def get(self):
            return self.item

        def empty(self):
            return self.item is None

    class FakeProcess:
        def __init__(self, target, args):
            self.args = args
            self.exitcode = None

        def start(self):
            suite = self.args[0]
            queue = self.args[2]
            if "broken" in suite:
                queue.put((1, "FAILED\n2 failed\n", ""))
            else:
                queue.put((0, "1 passed\n", ""))
            self.exitcode = 0

        def join(self):
            return None

    class FakeContext:
        Queue = FakeQueue
        Process = FakeProcess

    monkeypatch.setattr(mod.multiprocessing, "get_context", lambda name: FakeContext)

    assert mod.main() == 1
    out = capsys.readouterr().out
    assert "full-pytest: 1/2 suites green" in out
    assert "FAIL skills/broken/tests" in out
    assert "2 failed" in mod.SNAPSHOT.read_text(encoding="utf-8")
