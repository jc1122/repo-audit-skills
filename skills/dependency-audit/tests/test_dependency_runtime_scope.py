import json

from helpers import load_module


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_audit(root, out):
    mod = load_module()
    rc = mod.main(["--root", str(root), "--out-dir", str(out)])
    data = json.loads((out / "dependency_findings.json").read_text())
    return rc, data


def _metric_names(findings):
    return {finding["metric"]["name"] for finding in findings}


def test_optional_dependency_imported_only_from_tests_is_not_runtime_dep(tmp_path):
    root = tmp_path / "optional_only"
    _write(
        root / "pyproject.toml",
        "\n".join(
            [
                "[project]",
                'name = "optional-only"',
                'version = "0.1.0"',
                "dependencies = []",
                "",
                "[project.optional-dependencies]",
                'test = ["pytest"]',
                "",
            ]
        ),
    )
    _write(
        root / "tests" / "test_app.py",
        "import pytest\n\n\ndef test_app():\n    assert pytest is not None\n",
    )

    rc, findings = _run_audit(root, tmp_path / "out")

    assert rc == 0
    assert "runtime_dep_test_only" not in _metric_names(findings)


def test_requirements_dependency_imported_only_from_tests_is_not_runtime_dep(
    tmp_path,
):
    root = tmp_path / "requirements_only"
    _write(root / "requirements.txt", "pytest\n")
    _write(
        root / "tests" / "test_app.py",
        "import pytest\n\n\ndef test_app():\n    assert pytest is not None\n",
    )

    rc, findings = _run_audit(root, tmp_path / "out")

    assert rc == 0
    assert "runtime_dep_test_only" not in _metric_names(findings)


def test_dependency_audit_script_exports_public_helpers():
    mod = load_module()

    assert mod.DEFAULT_THRESHOLDS == {}
    assert mod.MODULE_TO_DIST["yaml"] == "pyyaml"
    assert callable(mod.collect_imports)
    assert callable(mod.declared_deps)
    assert callable(mod.analyze_tree)
    assert issubclass(mod.ToolError, RuntimeError)
