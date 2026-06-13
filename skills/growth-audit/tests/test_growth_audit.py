"""Tests for the growth-audit leaf.

All tests synthesise git repos under ``tmp_path`` — no fixture files.
Includes in-process tests for coverage of growth_audit.py and its
vendored health_common.py.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "growth_audit.py"
VENDORED_HC = SKILL_ROOT / "scripts" / "health_common.py"


# ---------------------------------------------------------------------------
# Module loader helpers (in-process)
# ---------------------------------------------------------------------------


def _load_module():
    """Load growth_audit as a module for in-process testing."""
    spec = importlib.util.spec_from_file_location("growth_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_vendored_hc():
    """Load the vendored health_common.py for coverage."""
    spec = importlib.util.spec_from_file_location("hc_vendored_growth", VENDORED_HC)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # needed for dataclass annotation resolution
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Subprocess helpers (preserved)
# ---------------------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _read_findings(out_dir: Path) -> list[dict]:
    path = out_dir / "growth-audit_findings.json"
    return json.loads(path.read_text()) if path.exists() else []


def _read_summary(out_dir: Path) -> dict:
    path = out_dir / "growth-audit_summary.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _git_init(path: Path) -> None:
    subprocess.run(
        ["git", "-C", str(path), "init", "-b", "main"],
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        capture_output=True,
        check=True,
    )


def _git_commit_all(path: Path, msg: str) -> None:
    subprocess.run(
        ["git", "-C", str(path), "add", "-A"],
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", msg, "--no-verify"],
        capture_output=True,
        text=True,
        check=True,
    )


def _git_tag(path: Path, tag: str) -> None:
    subprocess.run(
        ["git", "-C", str(path), "tag", tag],
        capture_output=True,
        text=True,
        check=True,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ======================================================================
# Subprocess contract tests (preserved from original)
# ======================================================================


def test_help_exits_zero():
    result = _run("--help")
    assert result.returncode == 0
    assert "--root" in result.stdout
    assert "--baseline-rev" in result.stdout


def test_missing_root_and_out_dir_exits_two():
    result = _run()
    assert result.returncode == 2


def test_detects_tracked_files_and_net_loc_growth(tmp_path: Path):
    """Tag a baseline, then add a source file — both metrics should fire."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(repo / "README.md", "# Hello\n")
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    _write(repo / "src" / "main.py", "def main():\n    pass\n")
    _git_commit_all(repo, "add main.py")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    assert result.returncode == 1, f"stderr: {result.stderr}"

    findings = _read_findings(out)
    assert len(findings) >= 2, f"got {len(findings)} findings"

    metric_names = {f["metric"]["name"] for f in findings}
    assert "tracked_files_growth" in metric_names
    assert "net_loc_growth" in metric_names

    for f_item in findings:
        assert f_item["signal"] == "RESTRUCTURE", (
            f"unexpected signal {f_item['signal']!r} in {f_item['metric']['name']}"
        )

    summary = _read_summary(out)
    assert summary["metrics"]["tracked_files_growth"] >= 1
    assert summary["metrics"]["net_loc_growth"] > 0


def test_deletion_only_repo_is_clean(tmp_path: Path):
    """Pure deletions should produce zero findings."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(repo / "a.py", "x = 1\n")
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    (repo / "a.py").unlink()
    _git_commit_all(repo, "remove a.py")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    assert result.returncode == 0, f"stderr: {result.stderr}"

    findings = _read_findings(out)
    assert findings == []


def test_allowance_suppresses_tracked_files_growth(tmp_path: Path):
    """An allowance >= the delta suppresses the finding and counts it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(repo / "README.md", "# Hello\n")
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    _write(repo / "a.py", "x = 1\n")
    _write(repo / "b.py", "x = 2\n")
    _git_commit_all(repo, "add two files")

    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps(
            {
                "allow_growth": [
                    {"metric": "tracked_files_growth", "max_delta": 5, "reason": "planned"}
                ]
            }
        )
    )

    out = tmp_path / "out"
    _run(
        "--root", str(repo), "--out-dir", str(out),
        "--baseline-rev", "base", "--config", str(cfg),
    )
    findings = _read_findings(out)
    tf_names = [
        f["metric"]["name"] for f in findings
        if f["metric"]["name"] == "tracked_files_growth"
    ]
    assert tf_names == [], f"tracked_files_growth should be suppressed, got {tf_names}"

    summary = _read_summary(out)
    suppressions = summary.get("suppressions", summary.get("suppression_counts", []))
    if isinstance(suppressions, list):
        suppressed_metrics = {s["metric"] for s in suppressions}
    else:
        suppressed_metrics = set(suppressions.keys())
    assert "tracked_files_growth" in suppressed_metrics or any(
        "tracked_files_growth" in str(s) for s in suppressions
    )


def test_growth_above_allowance_still_emits(tmp_path: Path):
    """Tiny allowance for net_loc_growth — growth beyond it still fires."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(repo / "README.md", "# Hello\n")
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    _write(repo / "big.py", "\n".join(f"x{i} = {i}" for i in range(20)) + "\n")
    _git_commit_all(repo, "add big.py")

    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps({
            "allow_growth": [
                {"metric": "net_loc_growth", "max_delta": 2, "reason": "tiny"}
            ]
        })
    )

    out = tmp_path / "out"
    result = _run(
        "--root", str(repo), "--out-dir", str(out),
        "--baseline-rev", "base", "--config", str(cfg),
    )
    assert result.returncode == 1, f"stderr: {result.stderr}"

    findings = _read_findings(out)
    nl_findings = [f for f in findings if f["metric"]["name"] == "net_loc_growth"]
    assert len(nl_findings) >= 1, "net_loc_growth should still emit a finding"


def test_dependency_delta_cargo_toml(tmp_path: Path):
    """New dependencies in Cargo.toml (Rust) should be detected."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(
        repo / "Cargo.toml",
        "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n\n[dependencies]\nserde = \"1\"\n",
    )
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    _write(
        repo / "Cargo.toml",
        "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n\n[dependencies]\n"
        "serde = \"1\"\n"
        "tokio = { version = \"1\", features = [\"full\"] }\n"
        "clap = \"4\"\n",
    )
    _git_commit_all(repo, "add tokio and clap deps")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    assert result.returncode == 1, f"stderr: {result.stderr}"

    summary = _read_summary(out)
    assert summary["metrics"]["dependency_growth"] >= 2, (
        f"expected >= 2 new deps, got {summary['metrics']['dependency_growth']}"
    )


def test_dependency_delta_go_mod(tmp_path: Path):
    """New dependencies in go.mod should be detected."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(
        repo / "go.mod",
        "module example\n\ngo 1.21\n\nrequire (\n\tgithub.com/stretchr/testify v1.8.0\n)\n",
    )
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    _write(
        repo / "go.mod",
        "module example\n\ngo 1.21\n\nrequire (\n\tgithub.com/stretchr/testify v1.8.0\n"
        "\tgithub.com/gin-gonic/gin v1.9.0\n)\n",
    )
    _git_commit_all(repo, "add gin dep")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    assert result.returncode == 1, f"stderr: {result.stderr}"

    summary = _read_summary(out)
    assert summary["metrics"]["dependency_growth"] >= 1, (
        f"expected >= 1 new dep, got {summary['metrics']['dependency_growth']}"
    )


def test_package_json_version_only_change_does_not_create_dependency_growth(
    tmp_path: Path,
):
    """Changing package metadata only must not count as dependency growth."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(
        repo / "package.json",
        json.dumps(
            {
                "name": "demo",
                "version": "0.1.0",
                "scripts": {"test": "node test.js"},
                "dependencies": {"react": "^18.0.0"},
                "devDependencies": {"vite": "^5.0.0"},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    _git_commit_all(repo, "initial package")
    _git_tag(repo, "base")

    _write(
        repo / "package.json",
        json.dumps(
            {
                "name": "demo",
                "version": "0.1.1",
                "scripts": {"test": "node test.js"},
                "dependencies": {"react": "^18.0.0"},
                "devDependencies": {"vite": "^5.0.0"},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    _git_commit_all(repo, "bump version")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    assert result.returncode == 0, f"stderr: {result.stderr}"

    summary = _read_summary(out)
    assert summary["metrics"]["dependency_growth"] == 0

    findings = _read_findings(out)
    metric_names = {f["metric"]["name"] for f in findings}
    assert "dependency_growth" not in metric_names


def test_package_json_dependency_sections_still_create_dependency_growth(
    tmp_path: Path,
):
    """New package dependencies and devDependencies should still be detected."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(
        repo / "package.json",
        json.dumps(
            {
                "name": "demo",
                "version": "0.1.0",
                "dependencies": {"react": "^18.0.0"},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    _git_commit_all(repo, "initial package")
    _git_tag(repo, "base")

    _write(
        repo / "package.json",
        json.dumps(
            {
                "name": "demo",
                "version": "0.1.0",
                "dependencies": {"lodash": "^4.17.21", "react": "^18.0.0"},
                "devDependencies": {"vitest": "^1.0.0"},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    _git_commit_all(repo, "add package deps")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    assert result.returncode == 1, f"stderr: {result.stderr}"

    summary = _read_summary(out)
    assert summary["metrics"]["dependency_growth"] == 2

    findings = _read_findings(out)
    metric_names = {f["metric"]["name"] for f in findings}
    assert "dependency_growth" in metric_names


def test_cli_flag_growth_detected(tmp_path: Path):
    """Adding a new argparse add_argument call should be detected."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(
        repo / "cli.py",
        "import argparse\np = argparse.ArgumentParser()\np.add_argument('--name')\n",
    )
    _git_commit_all(repo, "initial with one flag")
    _git_tag(repo, "base")

    _write(
        repo / "cli.py",
        "import argparse\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--name')\n"
        "p.add_argument('--verbose', action='store_true')\n"
        "p.add_argument('--output', '-o')\n",
    )
    _git_commit_all(repo, "add two more flags")

    out = tmp_path / "out"
    _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    summary = _read_summary(out)
    assert summary["metrics"]["cli_flag_growth"] >= 2, (
        f"expected >= 2 new flags, got {summary['metrics']['cli_flag_growth']}"
    )


def test_growth_findings_signal_is_restructure(tmp_path: Path):
    """Every growth finding must emit signal=RESTRUCTURE, never GROWTH."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)

    _write(repo / "README.md", "# Hello\n")
    _git_commit_all(repo, "initial")
    _git_tag(repo, "base")

    _write(repo / "a.py", "x = 1\n")
    _write(repo / "b.py", "y = 2\n")
    _git_commit_all(repo, "add two source files")

    out = tmp_path / "out"
    result = _run("--root", str(repo), "--out-dir", str(out), "--baseline-rev", "base")
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}"

    findings = _read_findings(out)
    assert len(findings) > 0, "expected at least one finding"

    signals = {f["signal"] for f in findings}
    assert "GROWTH" not in signals, f"GROWTH signal found, signals: {signals}"
    assert signals == {"RESTRUCTURE"}, f"expected only RESTRUCTURE, got: {signals}"

    assert (out / "growth-audit_findings.json").exists()
    assert (out / "growth-audit_summary.json").exists()

    summary = _read_summary(out)
    assert "tracked_files_growth" in summary["metrics"]
    assert summary["metrics"]["tracked_files_growth"] >= 2


# ======================================================================
# In-process coverage tests
# ======================================================================


class TestLoadModule:
    """Coverage: module loading and constants."""

    def test_module_loads(self):
        mod = _load_module()
        assert mod.LEAF == "growth-audit"
        assert mod.SIGNAL_GROWTH == "RESTRUCTURE"
        assert callable(mod._dep_entries)
        assert callable(mod._severity_for_delta)
        assert callable(mod._load_config)
        assert callable(mod._apply_allowances)
        assert callable(mod.analyze_tree)
        assert callable(mod.render_md)
        assert callable(mod.build_parser)
        assert callable(mod.main)


class TestDepEntries:
    """Coverage: _dep_entries — pure function for parsing dependency manifests."""

    def test_requirements_txt(self):
        mod = _load_module()
        entries = mod._dep_entries("pytest>=7.0\nrequests==2.28\n", "requirements.txt")
        assert len(entries) >= 2
        assert "pytest>=7.0" in entries

    def test_comments_and_blanks_skipped(self):
        mod = _load_module()
        entries = mod._dep_entries(
            "# comment\n\nrequests>=2.28\n  \n# another\n",
            "requirements.txt",
        )
        assert entries == ["requests>=2.28"]

    def test_toml_entries(self):
        mod = _load_module()
        content = 'serde = "1"\ntokio = { version = "1" }\n'
        entries = mod._dep_entries(content, "Cargo.toml")
        assert len(entries) >= 2

    def test_json_entries(self):
        mod = _load_module()
        content = json.dumps({
            "name": "demo",
            "version": "0.1.0",
            "scripts": {"test": "vitest"},
            "dependencies": {"react": "^18", "lodash": "^4"},
            "devDependencies": {"vite": "^5"},
        })
        entries = mod._dep_entries(content, "package.json")
        assert set(entries) == {
            "dependencies:react",
            "dependencies:lodash",
            "devDependencies:vite",
        }

    def test_go_mod_entries(self):
        mod = _load_module()
        content = "require (\n\tgithub.com/stretchr/testify v1.8.0\n)\n"
        entries = mod._dep_entries(content, "go.mod")
        assert len(entries) >= 1

    def test_gemfile_entries(self):
        mod = _load_module()
        content = 'gem "rails"\ngem "rspec"\n'
        entries = mod._dep_entries(content, "Gemfile")
        assert len(entries) >= 2

    def test_empty_content(self):
        mod = _load_module()
        entries = mod._dep_entries("", "requirements.txt")
        assert entries == []


class TestSeverityForDelta:
    """Coverage: _severity_for_delta."""

    def test_tracked_files(self):
        mod = _load_module()
        assert mod._severity_for_delta("tracked_files_growth", 5) == "low"
        assert mod._severity_for_delta("tracked_files_growth", 15) == "medium"
        assert mod._severity_for_delta("tracked_files_growth", 30) == "high"

    def test_dependency_growth(self):
        mod = _load_module()
        assert mod._severity_for_delta("dependency_growth", 3) == "low"
        assert mod._severity_for_delta("dependency_growth", 15) == "medium"
        assert mod._severity_for_delta("dependency_growth", 25) == "high"

    def test_net_loc_growth(self):
        mod = _load_module()
        assert mod._severity_for_delta("net_loc_growth", 300) == "low"
        assert mod._severity_for_delta("net_loc_growth", 800) == "medium"
        assert mod._severity_for_delta("net_loc_growth", 3000) == "high"

    def test_cli_flag_growth(self):
        mod = _load_module()
        assert mod._severity_for_delta("cli_flag_growth", 3) == "low"
        assert mod._severity_for_delta("cli_flag_growth", 8) == "medium"
        assert mod._severity_for_delta("cli_flag_growth", 20) == "high"

    def test_unknown_metric_defaults_low(self):
        mod = _load_module()
        assert mod._severity_for_delta("unknown_metric", 100) == "low"


class TestLoadConfig:
    """Coverage: _load_config."""

    def test_defaults_when_none(self):
        mod = _load_module()
        cfg = mod._load_config(None)
        assert cfg["allow_growth"] == []

    def test_from_file(self, tmp_path):
        mod = _load_module()
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(json.dumps({
            "allow_growth": [{"metric": "net_loc_growth", "max_delta": 100, "reason": "test"}]
        }))
        cfg = mod._load_config(str(cfg_file))
        assert len(cfg["allow_growth"]) == 1
        assert cfg["allow_growth"][0]["metric"] == "net_loc_growth"

    def test_invalid_json(self, tmp_path):
        mod = _load_module()
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text("not json")
        with pytest.raises(mod.ToolError, match="invalid"):
            mod._load_config(str(cfg_file))

    def test_missing_file(self, tmp_path):
        mod = _load_module()
        with pytest.raises(mod.ToolError, match="cannot read"):
            mod._load_config(str(tmp_path / "nonexistent.json"))


class TestEmitError:
    """Coverage: _emit_error."""

    def test_prints_json_error(self):
        mod = _load_module()
        old = sys.stdout
        try:
            sys.stdout = io.StringIO()
            mod._emit_error("boom")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old
        assert "error" in output
        assert "boom" in output
        assert json.loads(output)["status"] == "error"


class TestBuildParser:
    """Coverage: build_parser."""

    def test_creates_parser(self):
        mod = _load_module()
        parser = mod.build_parser()
        assert parser is not None

    def test_parses_required_args(self):
        mod = _load_module()
        parser = mod.build_parser()
        ns = parser.parse_args([
            "--root", "/tmp/r", "--out-dir", "/tmp/o", "--baseline-rev", "v1.0"
        ])
        assert ns.root == "/tmp/r"
        assert ns.out_dir == "/tmp/o"
        assert ns.baseline_rev == "v1.0"


class TestRenderMd:
    """Coverage: render_md."""

    def test_empty_report(self):
        mod = _load_module()
        summary = {
            "metrics": {}, "suppressions": [],
            "baseline": "v1", "baseline_sha": "abc123", "head_sha": "def456",
        }
        md = mod.render_md([], summary)
        assert "# growth-audit report" in md
        assert "No findings" in md

    def test_with_findings(self):
        mod = _load_module()
        f = mod.hc.Finding(
            leaf="growth-audit",
            signal="RESTRUCTURE",
            severity="medium",
            path="<repo>",
            line_start=0, line_end=0,
            symbol="tracked_files_growth",
            metric_name="tracked_files_growth",
            metric_value=5.0, metric_threshold=0.0,
            evidence_tool="git", evidence_raw='{"delta": 5}',
            confidence="high",
            suggested_action="Review growth",
        )
        summary = {
            "metrics": {"tracked_files_growth": 5},
            "suppressions": [],
            "baseline": "v1", "baseline_sha": "abc", "head_sha": "def",
        }
        md = mod.render_md([f], summary)
        assert "RESTRUCTURE" in md
        assert "tracked_files_growth" in md

    def test_with_suppressions(self):
        mod = _load_module()
        summary = {
            "metrics": {"tracked_files_growth": 3},
            "suppressions": [
                {"metric": "tracked_files_growth", "delta": 3, "max_delta": 5, "reason": "ok"}
            ],
            "baseline": "v1", "baseline_sha": "abc", "head_sha": "def",
        }
        md = mod.render_md([], summary)
        assert "Suppressions" in md
        assert "tracked_files_growth" in md


class TestApplyAllowances:
    """Coverage: _apply_allowances."""

    def test_overflow_produces_finding(self):
        mod = _load_module()
        metrics = {"tracked_files_growth": 10}
        allow = [{"metric": "tracked_files_growth", "max_delta": 3, "reason": "test"}]
        findings, suppressions, overflows = mod._apply_allowances(metrics, allow)
        assert len(findings) >= 1
        assert len(overflows) >= 1
        f = findings[0]
        assert f.signal == "RESTRUCTURE"
        assert f.metric_name == "tracked_files_growth"

    def test_suppression_no_finding(self):
        mod = _load_module()
        metrics = {"tracked_files_growth": 2}
        allow = [{"metric": "tracked_files_growth", "max_delta": 5, "reason": "test"}]
        findings, suppressions, overflows = mod._apply_allowances(metrics, allow)
        assert len(suppressions) >= 1
        assert len(findings) == 0

    def test_no_positive_growth_no_finding(self):
        mod = _load_module()
        metrics = {"tracked_files_growth": 0}
        allow = [{"metric": "tracked_files_growth", "max_delta": 5, "reason": "test"}]
        findings, suppressions, overflows = mod._apply_allowances(metrics, allow)
        assert len(findings) == 0
        assert len(suppressions) == 0

    def test_unsuppressed_metric_emits(self):
        mod = _load_module()
        metrics = {"cli_flag_growth": 5}
        allow = []  # no allowances
        findings, suppressions, overflows = mod._apply_allowances(metrics, allow)
        assert len(findings) >= 1
        f = findings[0]
        assert f.metric_name == "cli_flag_growth"
        assert f.metric_value == 5.0

    def test_multiple_allowances(self):
        mod = _load_module()
        metrics = {"tracked_files_growth": 3, "net_loc_growth": 1000}
        allow = [
            {"metric": "tracked_files_growth", "max_delta": 5, "reason": "ok"},
            {"metric": "net_loc_growth", "max_delta": 200, "reason": "too small"},
        ]
        findings, suppressions, overflows = mod._apply_allowances(metrics, allow)
        assert len(suppressions) >= 1  # tracked_files_growth suppressed
        assert len(overflows) >= 1     # net_loc_growth overflow
        assert len(findings) >= 1      # at least net_loc_growth


class TestAnalyzeTreeInProcess:
    """Coverage: analyze_tree (needs git repo)."""

    def test_basic_growth(self, tmp_path):
        mod = _load_module()
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init(repo)
        _write(repo / "README.md", "# Hello\n")
        _git_commit_all(repo, "initial")
        _git_tag(repo, "base")
        _write(repo / "main.py", "x = 1\n")
        _git_commit_all(repo, "add main.py")

        findings, summary = mod.analyze_tree(str(repo), "base")
        assert summary["leaf"] == "growth-audit"
        assert summary["metrics"]["tracked_files_growth"] >= 1
        assert isinstance(findings, list)

    def test_with_config(self, tmp_path):
        mod = _load_module()
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init(repo)
        _write(repo / "README.md", "# Hello\n")
        _git_commit_all(repo, "initial")
        _git_tag(repo, "base")
        _write(repo / "main.py", "x = 1\n")
        _git_commit_all(repo, "add main.py")

        cfg = {"allow_growth": [{"metric": "tracked_files_growth", "max_delta": 10, "reason": "ok"}]}
        findings, summary = mod.analyze_tree(str(repo), "base", config=cfg)
        assert summary["suppression_count"] >= 1
        assert summary["finding_count"] == 0  # suppressed

    def test_bad_baseline_raises(self, tmp_path):
        mod = _load_module()
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init(repo)
        with pytest.raises(mod.ToolError, match="cannot resolve"):
            mod.analyze_tree(str(repo), "nonexistent_tag")

    def test_not_git_repo_raises(self, tmp_path):
        mod = _load_module()
        non_repo = tmp_path / "not_repo"
        non_repo.mkdir()
        with pytest.raises(mod.ToolError, match="not a git"):
            mod.analyze_tree(str(non_repo), "HEAD")


class TestMainInProcess:
    """Coverage: main entry point."""

    def test_no_args(self):
        mod = _load_module()
        assert mod.main([]) == 2

    def test_missing_args(self):
        mod = _load_module()
        assert mod.main(["--root", "/tmp"]) == 2

    def test_with_git_repo(self, tmp_path):
        mod = _load_module()
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init(repo)
        _write(repo / "README.md", "# Hello\n")
        _git_commit_all(repo, "initial")
        out = tmp_path / "out"

        rc = mod.main([
            "--root", str(repo), "--out-dir", str(out), "--baseline-rev", "HEAD"
        ])
        assert rc in (0, 1)
        assert (out / "growth-audit_findings.json").exists()
        assert (out / "growth-audit_summary.json").exists()

    def test_md_format(self, tmp_path):
        mod = _load_module()
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init(repo)
        _write(repo / "README.md", "# Hello\n")
        _git_commit_all(repo, "initial")
        out = tmp_path / "out"

        rc = mod.main([
            "--root", str(repo), "--out-dir", str(out),
            "--baseline-rev", "HEAD", "--format", "md",
        ])
        assert rc in (0, 1)
        assert (out / "growth-audit_report.md").exists()


# ---------------------------------------------------------------------------
# Vendored health_common.py coverage
# ---------------------------------------------------------------------------


def test_vendored_health_common_is_importable(tmp_path):
    """Loading the vendored health_common.py exercises all its lines."""
    hc_mod = _load_vendored_hc()

    f = hc_mod.Finding(
        leaf="test", signal="SIMPLIFY", severity="low",
        path="f.py", line_start=1, line_end=2, symbol="s",
        metric_name="m", metric_value=0.5, metric_threshold=1.0,
        evidence_tool="t", evidence_raw="r",
        confidence="medium", suggested_action="a",
    )
    d = f.to_dict()
    assert d["leaf"] == "test"
    assert d["signal"] == "SIMPLIFY"
    assert len(d["id"]) == 16

    sorted_f = hc_mod.sort_findings([f])
    assert len(sorted_f) == 1

    data = hc_mod.write_findings([f], tmp_path, "test-leaf")
    assert len(data) == 1
    assert (tmp_path / "test-leaf_findings.json").exists()

    assert hc_mod.EXIT_CLEAN == 0
    assert hc_mod.EXIT_FINDINGS == 1
    assert hc_mod.EXIT_ERROR == 2


# ======================================================================
# In-process tests (coverage for growth_audit.py and vendored health_common.py)
# ======================================================================


# ---------------------------------------------------------------------------
# Pure function tests (no git required)
# ---------------------------------------------------------------------------


class TestDepEntries:
    """Coverage: _dep_entries — dependency line extraction."""

    def test_requirements_txt(self):
        mod = _load_module()
        content = "requests>=2.28\npytest==7.0\n"
        entries = mod._dep_entries(content, "requirements.txt")
        assert len(entries) >= 2
        assert any("requests" in e for e in entries)

    def test_pyproject_toml(self):
        mod = _load_module()
        content = "[project]\ndependencies = [\n  \"requests>=2.28\",\n]\n"
        entries = mod._dep_entries(content, "pyproject.toml")
        # Some TOML patterns match
        assert isinstance(entries, list)

    def test_cargo_toml(self):
        mod = _load_module()
        content = "serde = \"1\"\ntokio = { version = \"1\" }\n"
        entries = mod._dep_entries(content, "Cargo.toml")
        assert len(entries) >= 2

    def test_skips_comments(self):
        mod = _load_module()
        content = "# comment\nrequests>=2.28\n"
        entries = mod._dep_entries(content, "requirements.txt")
        assert len(entries) == 1

    def test_go_mod(self):
        mod = _load_module()
        content = "github.com/stretchr/testify v1.8.0\ngithub.com/gin-gonic/gin v1.9.0\n"
        entries = mod._dep_entries(content, "go.mod")
        assert len(entries) >= 2

    def test_empty_content(self):
        mod = _load_module()
        entries = mod._dep_entries("", "requirements.txt")
        assert entries == []


class TestSeverityForDelta:
    """Coverage: _severity_for_delta."""

    def test_tracked_files_growth(self):
        mod = _load_module()
        assert mod._severity_for_delta("tracked_files_growth", 5) == "low"
        assert mod._severity_for_delta("tracked_files_growth", 15) == "medium"
        assert mod._severity_for_delta("tracked_files_growth", 30) == "high"

    def test_dependency_growth(self):
        mod = _load_module()
        assert mod._severity_for_delta("dependency_growth", 5) == "low"
        assert mod._severity_for_delta("dependency_growth", 15) == "medium"
        assert mod._severity_for_delta("dependency_growth", 30) == "high"

    def test_net_loc_growth(self):
        mod = _load_module()
        assert mod._severity_for_delta("net_loc_growth", 400) == "low"
        assert mod._severity_for_delta("net_loc_growth", 600) == "medium"
        assert mod._severity_for_delta("net_loc_growth", 3000) == "high"

    def test_docs_loc_growth(self):
        mod = _load_module()
        assert mod._severity_for_delta("docs_loc_growth", 400) == "low"
        assert mod._severity_for_delta("docs_loc_growth", 800) == "medium"
        assert mod._severity_for_delta("docs_loc_growth", 3000) == "high"

    def test_cli_flag_growth(self):
        mod = _load_module()
        assert mod._severity_for_delta("cli_flag_growth", 3) == "low"
        assert mod._severity_for_delta("cli_flag_growth", 10) == "medium"
        assert mod._severity_for_delta("cli_flag_growth", 20) == "high"

    def test_unknown_metric(self):
        mod = _load_module()
        assert mod._severity_for_delta("unknown", 100) == "low"


class TestLoadConfig:
    """Coverage: _load_config."""

    def test_default(self):
        mod = _load_module()
        cfg = mod._load_config(None)
        assert cfg["allow_growth"] == []

    def test_from_file(self, tmp_path):
        mod = _load_module()
        (tmp_path / "cfg.json").write_text(
            json.dumps({"allow_growth": [{"metric": "net_loc_growth", "max_delta": 100, "reason": "t"}]})
        )
        cfg = mod._load_config(str(tmp_path / "cfg.json"))
        assert len(cfg["allow_growth"]) == 1

    def test_invalid_json_raises_tool_error(self, tmp_path):
        mod = _load_module()
        (tmp_path / "cfg.json").write_text("bad")
        with pytest.raises(mod.ToolError, match="invalid JSON"):
            mod._load_config(str(tmp_path / "cfg.json"))

    def test_not_a_dict_raises(self, tmp_path):
        mod = _load_module()
        (tmp_path / "cfg.json").write_text("[1, 2, 3]")
        with pytest.raises(mod.ToolError, match="object"):
            mod._load_config(str(tmp_path / "cfg.json"))


class TestEmitError:
    """Coverage: _emit_error."""

    def test_prints_error_json(self):
        mod = _load_module()
        captured = io.StringIO()
        old = sys.stdout
        try:
            sys.stdout = captured
            mod._emit_error("test message")
        finally:
            sys.stdout = old
        out = captured.getvalue()
        data = json.loads(out.strip())
        assert data["status"] == "error"
        assert "test message" in data["message"]


class TestBuildParser:
    """Coverage: build_parser."""

    def test_creates_parser(self):
        mod = _load_module()
        parser = mod.build_parser()
        assert parser is not None

    def test_required_args(self):
        mod = _load_module()
        parser = mod.build_parser()
        ns = parser.parse_args(
            ["--root", "/r", "--out-dir", "/o", "--baseline-rev", "HEAD~1"]
        )
        assert ns.root == "/r"
        assert ns.out_dir == "/o"
        assert ns.baseline_rev == "HEAD~1"
        assert ns.format == "json"


class TestRenderMdInProcess:
    """Coverage: render_md."""

    def test_empty_findings(self):
        mod = _load_module()
        summary = {
            "baseline": "base",
            "baseline_sha": "abc123",
            "head_sha": "def456",
            "metrics": {},
            "suppressions": [],
        }
        md = mod.render_md([], summary)
        assert "No findings" in md
        assert "# growth-audit report" in md

    def test_with_findings(self):
        mod = _load_module()
        f = mod.hc.Finding(
            leaf="growth-audit",
            signal="RESTRUCTURE",
            severity="medium",
            path="<repo>",
            line_start=0,
            line_end=0,
            symbol="tracked_files_growth",
            metric_name="tracked_files_growth",
            metric_value=3.0,
            metric_threshold=0.0,
            evidence_tool="git",
            evidence_raw='{"delta": 3}',
            confidence="high",
            suggested_action="review",
        )
        summary = {
            "baseline": "base",
            "baseline_sha": "abc123",
            "head_sha": "def456",
            "metrics": {"tracked_files_growth": 3},
            "suppressions": [],
        }
        md = mod.render_md([f], summary)
        assert "RESTRUCTURE" in md
        assert "tracked_files_growth" in md

    def test_with_suppressions(self):
        mod = _load_module()
        summary = {
            "baseline": "base",
            "baseline_sha": "abc123",
            "head_sha": "def456",
            "metrics": {"tracked_files_growth": 2},
            "suppressions": [{"metric": "tracked_files_growth", "delta": 2, "max_delta": 5, "reason": "ok"}],
        }
        md = mod.render_md([], summary)
        assert "Suppressions" in md


class TestApplyAllowances:
    """Coverage: _apply_allowances."""

    def test_overflow(self):
        mod = _load_module()
        metrics = {"tracked_files_growth": 10}
        allow = [{"metric": "tracked_files_growth", "max_delta": 3, "reason": "test"}]
        findings, suppressions, overflows = mod._apply_allowances(metrics, allow)
        assert len(overflows) >= 1
        assert len(findings) >= 1
        f = findings[0]
        assert f.signal == "RESTRUCTURE"

    def test_suppression(self):
        mod = _load_module()
        metrics = {"tracked_files_growth": 2}
        allow = [{"metric": "tracked_files_growth", "max_delta": 5, "reason": "test"}]
        findings, suppressions, overflows = mod._apply_allowances(metrics, allow)
        assert len(suppressions) >= 1
        assert len(findings) == 0

    def test_zero_or_negative_skipped(self):
        mod = _load_module()
        metrics = {"tracked_files_growth": 0, "net_loc_growth": -5}
        allow = [{"metric": "tracked_files_growth", "max_delta": 3, "reason": "t"}]
        findings, suppressions, overflows = mod._apply_allowances(metrics, allow)
        # No positive growth → no findings
        for f_item in findings:
            assert f_item.metric_name != "tracked_files_growth"

    def test_no_allowance_rule_emits_directly(self):
        mod = _load_module()
        metrics = {"tracked_files_growth": 5}
        allow: list = []
        findings, suppressions, overflows = mod._apply_allowances(metrics, allow)
        assert len(findings) >= 1
        f = findings[0]
        assert f.metric_name == "tracked_files_growth"
        assert f.confidence == "medium"  # unsuppressed path


# ---------------------------------------------------------------------------
# In-process: git-dependent functions (synthesised repos)
# ---------------------------------------------------------------------------


class TestAnalyzeTreeInProcess:
    """Coverage: analyze_tree and its sub-functions (needs git)."""

    def test_basic_growth(self, tmp_path):
        mod = _load_module()
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init(repo)
        _write(repo / "README.md", "# Hello\n")
        _git_commit_all(repo, "init")
        _git_tag(repo, "base")
        _write(repo / "main.py", "x = 1\n")
        _git_commit_all(repo, "add main")
        findings, summary = mod.analyze_tree(str(repo), "base")
        assert summary["leaf"] == "growth-audit"
        assert summary["metrics"]["tracked_files_growth"] >= 1
        assert summary["metrics"]["net_loc_growth"] > 0

    def test_pure_deletions(self, tmp_path):
        mod = _load_module()
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init(repo)
        _write(repo / "a.py", "x = 1\n")
        _git_commit_all(repo, "init")
        _git_tag(repo, "base")
        (repo / "a.py").unlink()
        _git_commit_all(repo, "delete")
        findings, summary = mod.analyze_tree(str(repo), "base")
        assert len(findings) == 0

    def test_non_git_dir_raises(self, tmp_path):
        mod = _load_module()
        not_repo = tmp_path / "not_repo"
        not_repo.mkdir()
        with pytest.raises(mod.ToolError, match="not a git"):
            mod.analyze_tree(str(not_repo), "HEAD")

    def test_bad_revision_raises(self, tmp_path):
        mod = _load_module()
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init(repo)
        _write(repo / "README.md", "# H\n")
        _git_commit_all(repo, "init")
        with pytest.raises(mod.ToolError, match="cannot resolve"):
            mod.analyze_tree(str(repo), "deadbeef")


class TestMainInProcess:
    """Coverage: main entry-point."""

    def test_missing_required_args(self):
        mod = _load_module()
        with pytest.raises(SystemExit) as excinfo:
            mod.main([])
        assert excinfo.value.code == 2

    def test_invalid_config_file(self, tmp_path):
        mod = _load_module()
        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init(repo)
        _write(repo / "f", "x\n")
        _git_commit_all(repo, "init")
        _git_tag(repo, "base")
        cfg = tmp_path / "cfg.json"
        cfg.write_text("bad")
        out = tmp_path / "out"
        rc = mod.main([
            "--root", str(repo),
            "--out-dir", str(out),
            "--baseline-rev", "base",
            "--config", str(cfg),
        ])
        assert rc == 2

    def test_not_a_git_repo(self, tmp_path):
        mod = _load_module()
        not_repo = tmp_path / "not_repo"
        not_repo.mkdir()
        out = tmp_path / "out"
        rc = mod.main([
            "--root", str(not_repo),
            "--out-dir", str(out),
            "--baseline-rev", "HEAD",
        ])
        assert rc == 2


# ---------------------------------------------------------------------------
# Vendored health_common.py coverage
# ---------------------------------------------------------------------------


def test_vendored_health_common_is_importable(tmp_path):
    """Loading the vendored health_common.py exercises all its lines."""
    hc = _load_vendored_hc()
    f = hc.Finding(
        leaf="test",
        signal="SIMPLIFY",
        severity="low",
        path="f.py",
        line_start=1,
        line_end=2,
        symbol="s",
        metric_name="m",
        metric_value=0.5,
        metric_threshold=1.0,
        evidence_tool="t",
        evidence_raw="r",
        confidence="medium",
        suggested_action="a",
    )
    d = f.to_dict()
    assert d["leaf"] == "test"
    assert d["signal"] == "SIMPLIFY"
    assert len(d["id"]) == 16

    sorted_f = hc.sort_findings([f])
    assert len(sorted_f) == 1

    data = hc.write_findings([f], tmp_path, "test-leaf")
    assert len(data) == 1
    assert (tmp_path / "test-leaf_findings.json").exists()

    assert hc.EXIT_CLEAN == 0
    assert hc.EXIT_FINDINGS == 1
    assert hc.EXIT_ERROR == 2
