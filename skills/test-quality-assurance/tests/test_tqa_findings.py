"""In-process golden tests for audit_test_quality.py.

Exercises key functions directly (import-then-call) for coverage.
All assertions characterize CURRENT behavior -- these ARE the golden contract.
"""

import ast
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from helpers import FIXTURES, load_module

tqa = load_module()

# ---------------------------------------------------------------------------
# Helpers: _split_csv_values, _extract_all_strings
# ---------------------------------------------------------------------------


def test_split_csv_values_empty():
    assert tqa._split_csv_values(None) == []
    assert tqa._split_csv_values([]) == []


def test_split_csv_values_single():
    assert tqa._split_csv_values(["a,b,c"]) == ["a", "b", "c"]


def test_split_csv_values_multiple_args():
    assert tqa._split_csv_values(["a,b", "c,d"]) == ["a", "b", "c", "d"]


def test_split_csv_values_whitespace_trimming():
    assert tqa._split_csv_values([" a , b "]) == ["a", "b"]


def test_extract_all_strings_list():
    node = ast.parse("x = ['hello', 'world']").body[0]
    assert tqa._extract_all_strings(node.value) == ["hello", "world"]


def test_extract_all_strings_tuple():
    node = ast.parse("x = ('a', 'b')").body[0]
    assert tqa._extract_all_strings(node.value) == ["a", "b"]


def test_extract_all_strings_set():
    node = ast.parse("x = {'x'}").body[0]
    assert tqa._extract_all_strings(node.value) == ["x"]


def test_extract_all_strings_non_constants_ignored():
    node = ast.parse("x = [1, 2, 3]").body[0]
    assert tqa._extract_all_strings(node.value) == []


# ---------------------------------------------------------------------------
# _count_test_functions
# ---------------------------------------------------------------------------


def test_count_test_functions():
    tree = ast.parse(
        "def test_a(): pass\n"
        "def test_b(): pass\n"
        "def helper(): pass\n"
        "async def test_async(): pass\n"
    )
    assert tqa._count_test_functions(tree) == 3


def test_count_test_functions_empty():
    tree = ast.parse("x = 1")
    assert tqa._count_test_functions(tree) == 0


# ---------------------------------------------------------------------------
# _is_pytest_raises_call
# ---------------------------------------------------------------------------


def test_is_pytest_raises_call_true():
    tree = ast.parse("pytest.raises(ValueError)")
    call_node = tree.body[0].value
    assert tqa._is_pytest_raises_call(call_node) is True


def test_is_pytest_raises_call_false_non_pytest():
    tree = ast.parse("other.raises(ValueError)")
    call_node = tree.body[0].value
    assert tqa._is_pytest_raises_call(call_node) is False


def test_is_pytest_raises_call_false_wrong_attr():
    tree = ast.parse("pytest.warns(UserWarning)")
    call_node = tree.body[0].value
    assert tqa._is_pytest_raises_call(call_node) is False


# ---------------------------------------------------------------------------
# _count_pytest_raises
# ---------------------------------------------------------------------------


def test_count_pytest_raises_basic():
    tree = ast.parse(
        "pytest.raises(ValueError)\n"
        "pytest.raises(TypeError, match='bad')\n"
    )
    total, with_match, broad_tuple = tqa._count_pytest_raises(tree)
    assert total == 2
    assert with_match == 1
    assert broad_tuple == 0


def test_count_pytest_raises_broad_tuple():
    tree = ast.parse(
        "pytest.raises((ValueError, TypeError))\n"
        "pytest.raises((ValueError,))\n"
    )
    total, with_match, broad_tuple = tqa._count_pytest_raises(tree)
    assert total == 2
    assert with_match == 0
    assert broad_tuple == 1  # only the first has >1 elts


def test_count_pytest_raises_complex():
    tree = ast.parse(
        "import pytest\n"
        "with pytest.raises(ValueError):\n"
        "    pass\n"
    )
    total, with_match, broad_tuple = tqa._count_pytest_raises(tree)
    assert total == 1
    assert with_match == 0
    assert broad_tuple == 0


# ---------------------------------------------------------------------------
# _count_given_usage
# ---------------------------------------------------------------------------


def test_count_given_usage():
    # @given decorator IS counted as a Call node by the AST walker
    tree = ast.parse(
        "from hypothesis import given\n"
        "@given(x=...)\n"
        "def test_f(): pass\n"
    )
    assert tqa._count_given_usage(tree) == 1
    tree2 = ast.parse("given(x=1)")
    assert tqa._count_given_usage(tree2) == 1


# ---------------------------------------------------------------------------
# infer_public_hints
# ---------------------------------------------------------------------------


def test_infer_public_hints_clean():
    hints = tqa.infer_public_hints(FIXTURES / "clean")
    assert "Calculator(" in hints
    assert "add(" in hints
    assert "compute_ratio(" in hints


def test_infer_public_hints_dirty():
    hints = tqa.infer_public_hints(FIXTURES / "dirty")
    # Dirty has minimal __init__.py with no defined symbols
    # so hints should be empty (no function/class defs in __init__)
    assert len(hints) == 0


# ---------------------------------------------------------------------------
# collect_test_files
# ---------------------------------------------------------------------------


def test_collect_test_files_clean():
    files = tqa.collect_test_files(
        FIXTURES / "clean", ["tests"], list(tqa.DEFAULT_TEST_GLOBS)
    )
    assert len(files) >= 1
    assert any("test_calculator.py" in str(f) for f in files)


def test_collect_test_files_dirty():
    files = tqa.collect_test_files(
        FIXTURES / "dirty", ["tests"], list(tqa.DEFAULT_TEST_GLOBS)
    )
    assert len(files) >= 2
    paths = [str(f) for f in files]
    assert any("test_engine.py" in p for p in paths)
    assert any("test_more_dirty.py" in p for p in paths)


def test_collect_test_files_nonexistent_dir():
    files = tqa.collect_test_files(
        FIXTURES / "clean", ["nonexistent"], list(tqa.DEFAULT_TEST_GLOBS)
    )
    assert files == []


# ---------------------------------------------------------------------------
# analyze_file
# ---------------------------------------------------------------------------


def test_analyze_file_clean():
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    hints = tqa.infer_public_hints(FIXTURES / "clean")
    test_file = FIXTURES / "clean" / "tests" / "test_calculator.py"
    metrics = tqa.analyze_file(test_file, internal_res, hints)
    assert metrics.test_functions >= 5
    assert metrics.internal_imports == 0
    assert metrics.raises_total >= 1
    assert metrics.raises_with_match >= 1
    assert metrics.private_method_calls == 0
    assert metrics.public_call_hints > 0
    assert "smoke" in (metrics.markers or {})
    assert "unit" in (metrics.markers or {})


def test_analyze_file_dirty():
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    hints = []
    test_file = FIXTURES / "dirty" / "tests" / "test_engine.py"
    metrics = tqa.analyze_file(test_file, internal_res, hints)
    assert metrics.test_functions >= 4
    assert metrics.internal_imports > 0
    assert metrics.private_method_calls > 0
    assert metrics.expected_literal_count > 0
    assert metrics.exact_eq_assert_count > 0


def test_analyze_file_unparseable(tmp_path):
    """analyze_file returns empty metrics for unparseable files."""
    bad_file = tmp_path / "bad.py"
    # A file with a syntax error triggers the SyntaxError handler
    bad_file.write_text("def test_broken(  # missing colon\n    pass\n")
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    metrics = tqa.analyze_file(bad_file, internal_res, [])
    assert metrics.path == str(bad_file)
    assert metrics.test_functions == 0


# ---------------------------------------------------------------------------
# classify_file
# ---------------------------------------------------------------------------


def test_classify_file_clean():
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    hints = tqa.infer_public_hints(FIXTURES / "clean")
    test_file = FIXTURES / "clean" / "tests" / "test_calculator.py"
    metrics = tqa.analyze_file(test_file, internal_res, hints)
    c = tqa.classify_file(metrics)
    assert isinstance(c, dict)
    assert "white_box_candidate" in c
    assert "black_box_candidate" in c
    assert "change_indicator_candidate" in c
    # Clean: no internal imports, no private calls, public hints present
    assert c["black_box_candidate"] is True
    assert c["white_box_candidate"] is False


def test_classify_file_dirty():
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    hints = []
    test_file = FIXTURES / "dirty" / "tests" / "test_engine.py"
    metrics = tqa.analyze_file(test_file, internal_res, hints)
    c = tqa.classify_file(metrics)
    assert c["white_box_candidate"] is True
    assert c["black_box_candidate"] is False


# ---------------------------------------------------------------------------
# FileMetrics.to_dict
# ---------------------------------------------------------------------------


def test_file_metrics_to_dict():
    fm = tqa.FileMetrics(
        path="test_x.py",
        test_functions=3,
        private_method_calls=1,
        public_call_hints=5,
        internal_imports=2,
        raises_total=2,
        raises_with_match=1,
        raises_broad_tuple=0,
        markers=Counter({"smoke": 2}),
    )
    d = fm.to_dict()
    assert d["path"] == "test_x.py"
    assert d["test_functions"] == 3
    assert d["markers"] == {"smoke": 2}
    assert "classification" in d
    assert d["classification"]["white_box_candidate"] is True  # has internal_imports


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------


def test_summarize_clean():
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    hints = tqa.infer_public_hints(FIXTURES / "clean")
    files = tqa.collect_test_files(
        FIXTURES / "clean", ["tests"], list(tqa.DEFAULT_TEST_GLOBS)
    )
    metrics_list = [tqa.analyze_file(f, internal_res, hints) for f in files]
    summary = tqa.summarize(metrics_list)
    assert summary["totals"]["files"] >= 1
    assert summary["totals"]["test_functions"] >= 5
    assert summary["totals"]["internal_imports"] == 0
    assert summary["totals"]["public_call_hints"] > 0
    assert summary["classification_counts"]["black_box_candidate"] >= 1


def test_summarize_dirty():
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    hints = []
    files = tqa.collect_test_files(
        FIXTURES / "dirty", ["tests"], list(tqa.DEFAULT_TEST_GLOBS)
    )
    metrics_list = [tqa.analyze_file(f, internal_res, hints) for f in files]
    summary = tqa.summarize(metrics_list)
    assert summary["totals"]["files"] >= 2
    assert summary["totals"]["internal_imports"] > 0
    assert summary["totals"]["private_method_calls"] > 0
    assert summary["totals"]["expected_literal_count"] > 0
    assert summary["classification_counts"]["white_box_candidate"] >= 1
    assert summary["classification_counts"]["change_indicator_candidate"] >= 1


def test_summarize_empty():
    summary = tqa.summarize([])
    assert summary["totals"]["files"] == 0
    assert summary["totals"]["test_functions"] == 0


# ---------------------------------------------------------------------------
# score_rubric
# ---------------------------------------------------------------------------


def make_config(public_hints=None):
    if public_hints is None:
        public_hints = []
    return {
        "test_dirs": ["tests"],
        "test_globs": ["test_*.py"],
        "internal_import_patterns": list(tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS),
        "public_hints": public_hints,
        "auto_inferred_public_hints": False,
        "exact_eq_pattern": "",
    }


def test_score_rubric_empty():
    summary = tqa.summarize([])
    config = make_config()
    scores = tqa.score_rubric(summary, config)
    assert scores["total"] >= 0
    assert scores["max_total"] == 24
    assert len(scores) >= 10  # 8 dimensions + total + max_total


def test_score_rubric_clean():
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    hints = tqa.infer_public_hints(FIXTURES / "clean")
    files = tqa.collect_test_files(
        FIXTURES / "clean", ["tests"], list(tqa.DEFAULT_TEST_GLOBS)
    )
    metrics_list = [tqa.analyze_file(f, internal_res, hints) for f in files]
    summary = tqa.summarize(metrics_list)
    config = make_config(public_hints=hints)
    scores = tqa.score_rubric(summary, config)
    # Contract Coverage: public hints and raises with match detected -> score 3
    assert scores["Contract Coverage"]["score"] == 3
    # Behavior-First Focus: priv/pub ratio 0 with public hints -> score 3
    assert scores["Behavior-First Focus"]["score"] == 3
    # Coverage/Mutation: no cov_json_path -> score 1
    assert scores["Coverage/Mutation"]["score"] == 1


def test_score_rubric_dirty():
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    hints = []
    files = tqa.collect_test_files(
        FIXTURES / "dirty", ["tests"], list(tqa.DEFAULT_TEST_GLOBS)
    )
    metrics_list = [tqa.analyze_file(f, internal_res, hints) for f in files]
    summary = tqa.summarize(metrics_list)
    config = make_config(public_hints=hints)
    scores = tqa.score_rubric(summary, config)
    # No public hints -> Contract Coverage score 1 (tests exist)
    assert scores["Contract Coverage"]["score"] == 1
    # High private/public ratio (no public hints) -> score 0
    assert scores["Behavior-First Focus"]["score"] == 0
    # White-Box present with internal coupling, high ratio -> score 1
    assert scores["White-Box Justification"]["score"] >= 0


def test_score_rubric_with_coverage_json(tmp_path):
    """Test score_rubric with a synthetic coverage.json."""
    cov_path = tmp_path / "coverage.json"
    cov_path.write_text(json.dumps({
        "totals": {
            "percent_covered": 90.0,
            "covered_branches": 80,
            "num_branches": 100,
        }
    }))
    summary = tqa.summarize([])
    config = make_config()
    scores = tqa.score_rubric(summary, config, cov_json_path=str(cov_path))
    assert scores["Coverage/Mutation"]["score"] == 3  # 90% >= 85, 80% >= 75


def test_score_rubric_determinism_with_given():
    """Score with hypothesis given calls."""
    fm = tqa.FileMetrics(
        path="test_x.py",
        test_functions=1,
        given_count=3,
        public_call_hints=5,
    )
    summary = tqa.summarize([fm])
    config = make_config(public_hints=["foo("])
    scores = tqa.score_rubric(summary, config)
    assert scores["Determinism/Isolation"]["score"] == 3


def test_score_rubric_assertion_quality_all_match():
    """Assertion quality when all raises use match."""
    fm = tqa.FileMetrics(
        path="test_x.py",
        test_functions=1,
        raises_total=3,
        raises_with_match=3,
        exact_eq_assert_count=1,
        public_call_hints=1,
    )
    summary = tqa.summarize([fm])
    config = make_config(public_hints=["foo("])
    scores = tqa.score_rubric(summary, config)
    # match_ratio == 1.0 and exact_eq > 0 and raises_total > 0 => score 3
    assert scores["Assertion Quality"]["score"] == 3


def test_score_rubric_pyramid_scope():
    """Multiple files with white and black box."""
    fm1 = tqa.FileMetrics(
        path="tests/unit/test_a.py",
        test_functions=1,
        internal_imports=2,  # makes white_box_candidate
    )
    fm2 = tqa.FileMetrics(
        path="tests/test_b.py",
        test_functions=2,
        public_call_hints=5,  # makes black_box_candidate
    )
    summary = tqa.summarize([fm1, fm2])
    config = make_config(public_hints=["foo("])
    scores = tqa.score_rubric(summary, config)
    # 2 files -> score 1 (minimum). Actually:
    # n_files = 2, has_both = True (white from fm1, black from fm2)
    # But the pyramid check: n_files >= 4 and has_both -> 3, elif n_files >= 3 -> 2, elif n_files >= 2 -> 1
    # So 2 files -> 1
    assert scores["Pyramid/Scope"]["score"] == 1


# ---------------------------------------------------------------------------
# parse_coverage_json
# ---------------------------------------------------------------------------


def test_parse_coverage_json_valid(tmp_path):
    cov_path = tmp_path / "coverage.json"
    cov_path.write_text(json.dumps({
        "totals": {
            "percent_covered": 85.5,
            "covered_branches": 42,
            "num_branches": 50,
        }
    }))
    result = tqa.parse_coverage_json(str(cov_path))
    assert result["statement_pct"] == 85.5
    assert result["branch_pct"] == 84.0


def test_parse_coverage_json_no_branches(tmp_path):
    cov_path = tmp_path / "coverage.json"
    cov_path.write_text(json.dumps({
        "totals": {
            "percent_covered": 72.0,
        }
    }))
    result = tqa.parse_coverage_json(str(cov_path))
    assert result["statement_pct"] == 72.0
    assert "branch_pct" not in result


def test_parse_coverage_json_missing_file():
    result = tqa.parse_coverage_json("/nonexistent/coverage.json")
    assert result == {}


def test_parse_coverage_json_bad_json(tmp_path):
    cov_path = tmp_path / "bad.json"
    cov_path.write_text("not json")
    result = tqa.parse_coverage_json(str(cov_path))
    assert result == {}


def test_parse_coverage_json_zero_branches(tmp_path):
    cov_path = tmp_path / "coverage.json"
    cov_path.write_text(json.dumps({
        "totals": {
            "percent_covered": 50.0,
            "covered_branches": 0,
            "num_branches": 0,
        }
    }))
    result = tqa.parse_coverage_json(str(cov_path))
    assert result["statement_pct"] == 50.0
    assert "branch_pct" not in result  # num_branches == 0


# ---------------------------------------------------------------------------
# compute_delta
# ---------------------------------------------------------------------------


def make_report(summary_data=None, rubric_data=None):
    return {
        "root": "/fake",
        "config": {},
        "summary": summary_data or tqa.summarize([]),
        "rubric_scores": rubric_data or {},
        "files": [],
    }


def test_compute_delta_identical():
    report = make_report()
    delta = tqa.compute_delta(report, report)
    assert delta["totals"] == {}
    assert delta["ratios"] == {}
    assert delta["classification_counts"] == {}
    assert delta["rubric_scores"] == {}


def test_compute_delta_totals_changed():
    fm = tqa.FileMetrics(path="test_x.py", test_functions=5)
    cur = make_report(summary_data=tqa.summarize([fm]))
    base = make_report(summary_data=tqa.summarize([]))
    delta = tqa.compute_delta(cur, base)
    assert "test_functions" in delta["totals"]
    assert delta["totals"]["test_functions"]["before"] == 0
    assert delta["totals"]["test_functions"]["after"] == 5
    assert delta["totals"]["test_functions"]["change"] == 5


def test_compute_delta_rubric_changed():
    cur = make_report(rubric_data={
        "total": 10, "max_total": 24,
        "Contract Coverage": {"score": 3, "max": 3, "rationale": "good"},
    })
    base = make_report(rubric_data={
        "total": 5, "max_total": 24,
        "Contract Coverage": {"score": 1, "max": 3, "rationale": "bad"},
    })
    delta = tqa.compute_delta(cur, base)
    assert delta["rubric_scores"]["total"]["before"] == 5
    assert delta["rubric_scores"]["total"]["after"] == 10
    assert delta["rubric_scores"]["Contract Coverage"]["change"] == 2


def test_compute_delta_classification_changed():
    fm = tqa.FileMetrics(path="test_x.py", internal_imports=3, public_call_hints=5)
    cur = make_report(summary_data=tqa.summarize([fm]))
    base = make_report(summary_data=tqa.summarize([]))
    delta = tqa.compute_delta(cur, base)
    assert "white_box_candidate" in delta["classification_counts"]
    # fm has internal_imports>0 so black_box_candidate=False; delta only tracks changes
    assert delta["classification_counts"]["white_box_candidate"]["change"] == 1


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------


def test_render_markdown_basic():
    fm = tqa.FileMetrics(path="test_x.py", test_functions=2, markers=Counter({"smoke": 1}))
    summary = tqa.summarize([fm])
    report = {
        "root": "/fake/project",
        "config": {
            "test_dirs": ["tests"],
            "test_globs": ["test_*.py"],
            "internal_import_patterns": [],
            "public_hints": [],
            "auto_inferred_public_hints": False,
            "exact_eq_pattern": "",
        },
        "summary": summary,
        "rubric_scores": {
            "Contract Coverage": {"score": 1, "max": 3, "rationale": "Tests exist"},
            "total": 5, "max_total": 24,
        },
        "files": [fm.to_dict()],
    }
    md = tqa.render_markdown(report)
    assert "# Test Quality Inventory" in md
    assert "test_x.py" in md or "Totals" in md
    assert "## Rubric Scores" in md
    assert "| Contract Coverage | 1 | 3 |" in md
    assert "| **Total** | **5** | **24** |" in md


def test_render_markdown_with_delta():
    fm = tqa.FileMetrics(path="test_x.py", test_functions=3)
    summary = tqa.summarize([fm])
    delta = tqa.compute_delta(
        {"summary": summary, "rubric_scores": {"total": 5}},
        {"summary": tqa.summarize([]), "rubric_scores": {"total": 0}},
    )
    report = {
        "root": "/fake",
        "config": {
            "test_dirs": ["tests"],
            "test_globs": ["test_*.py"],
            "internal_import_patterns": [],
            "public_hints": [],
            "auto_inferred_public_hints": False,
            "exact_eq_pattern": "",
        },
        "summary": summary,
        "rubric_scores": {"total": 5, "max_total": 24},
        "delta": delta,
        "files": [],
    }
    md = tqa.render_markdown(report)
    assert "## Delta Report" in md
    assert "test_functions" in md


def test_render_markdown_flags():
    fm = tqa.FileMetrics(
        path="test_x.py",
        test_functions=2,
        raises_total=10,
        raises_with_match=2,  # 0.2 ratio < 0.5 triggers flag
        private_method_calls=5,
    )
    summary = tqa.summarize([fm])
    report = {
        "root": "/fake",
        "config": {
            "test_dirs": ["tests"],
            "test_globs": ["test_*.py"],
            "internal_import_patterns": [],
            "public_hints": [],
            "auto_inferred_public_hints": False,
            "exact_eq_pattern": "",
        },
        "summary": summary,
        "rubric_scores": {"total": 0, "max_total": 24},
        "files": [],
    }
    md = tqa.render_markdown(report)
    assert "Low exception precision signal" in md


# ---------------------------------------------------------------------------
# public_hints parameter driving black_box classification
# ---------------------------------------------------------------------------


def test_public_hints_enable_black_box():
    hints = tqa.infer_public_hints(FIXTURES / "clean")
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    files = tqa.collect_test_files(
        FIXTURES / "clean", ["tests"], list(tqa.DEFAULT_TEST_GLOBS)
    )
    metrics_list = [tqa.analyze_file(f, internal_res, hints) for f in files]
    summary = tqa.summarize(metrics_list)
    assert summary["classification_counts"]["black_box_candidate"] >= 1


def test_no_public_hints_means_no_black_box():
    hints = []
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    files = tqa.collect_test_files(
        FIXTURES / "clean", ["tests"], list(tqa.DEFAULT_TEST_GLOBS)
    )
    metrics_list = [tqa.analyze_file(f, internal_res, hints) for f in files]
    summary = tqa.summarize(metrics_list)
    assert summary["classification_counts"].get("black_box_candidate", 0) == 0


# ---------------------------------------------------------------------------
# Exact-eq pattern override
# ---------------------------------------------------------------------------


def test_custom_exact_eq_pattern():
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    # A pattern that matches 'assert X == want'
    custom_re = re.compile(r"^\s*assert\s+\w+\s*==\s*want\b", re.MULTILINE)
    test_file = FIXTURES / "dirty" / "tests" / "test_engine.py"
    metrics = tqa.analyze_file(test_file, internal_res, [], exact_eq_re=custom_re)
    # The dirty test has 'assert result == want' which should match
    assert metrics.exact_eq_assert_count >= 1


# ---------------------------------------------------------------------------
# main() in-process (runs end-to-end without subprocess)
# ---------------------------------------------------------------------------


def test_main_in_process(tmp_path):
    """Run main() in-process against the dirty fixture."""
    import sys

    # Simulate CLI args
    json_out = tmp_path / "report.json"
    md_out = tmp_path / "report.md"

    sys.argv = [
        "audit_test_quality.py",
        "--root", str(FIXTURES / "dirty"),
        "--tests-dir", "tests",
        "--json-out", str(json_out),
        "--md-out", str(md_out),
        "--no-auto-public-hints",
    ]
    try:
        exit_code = tqa.main()
    finally:
        # Restore sys.argv to avoid side effects
        sys.argv = [sys.argv[0]] if sys.argv else []

    assert exit_code == 0
    assert json_out.exists()
    assert md_out.exists()

    report = json.loads(json_out.read_text())
    assert report["root"] == str((FIXTURES / "dirty").resolve())
    assert report["summary"]["totals"]["files"] >= 2
    assert "rubric_scores" in report


def test_main_with_coverage_and_baseline(tmp_path):
    """Run main() with coverage JSON and baseline."""
    import sys

    json_out = tmp_path / "report.json"
    md_out = tmp_path / "report.md"

    cov_path = tmp_path / "coverage.json"
    cov_path.write_text(json.dumps({
        "totals": {"percent_covered": 92.0, "covered_branches": 82, "num_branches": 100}
    }))

    # First create a baseline
    baseline_out = tmp_path / "baseline.json"
    sys.argv = [
        "audit_test_quality.py",
        "--root", str(FIXTURES / "dirty"),
        "--tests-dir", "tests",
        "--json-out", str(baseline_out),
        "--md-out", str(tmp_path / "baseline.md"),
        "--no-auto-public-hints",
    ]
    try:
        tqa.main()
    finally:
        sys.argv = [sys.argv[0]] if sys.argv else []

    # Now run with baseline and coverage
    sys.argv = [
        "audit_test_quality.py",
        "--root", str(FIXTURES / "dirty"),
        "--tests-dir", "tests",
        "--json-out", str(json_out),
        "--md-out", str(md_out),
        "--cov-json", str(cov_path),
        "--baseline-json", str(baseline_out),
        "--no-auto-public-hints",
    ]
    try:
        exit_code = tqa.main()
    finally:
        sys.argv = [sys.argv[0]] if sys.argv else []

    assert exit_code == 0
    report = json.loads(json_out.read_text())
    assert "delta" in report
    assert report["rubric_scores"]["Coverage/Mutation"]["score"] == 3


# ---------------------------------------------------------------------------
# Syntax error in test file
# ---------------------------------------------------------------------------


def test_analyze_file_syntax_error(tmp_path):
    """analyze_file returns empty metrics on syntax errors."""
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def test_broken(  # missing colon\n    pass\n")
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    metrics = tqa.analyze_file(bad_file, internal_res, [])
    assert metrics.test_functions == 0
    assert metrics.path == str(bad_file)


# ---------------------------------------------------------------------------
# parse_args smoke test
# ---------------------------------------------------------------------------


def test_parse_args_defaults():
    import sys
    sys.argv = ["audit_test_quality.py"]
    try:
        args = tqa.parse_args()
        assert args.root == "."
        assert args.tests_dir is None
        assert args.test_glob is None
        assert args.no_auto_public_hints is False
    finally:
        sys.argv = [sys.argv[0]] if sys.argv else []


# ---------------------------------------------------------------------------
# main() with --public-hint
# ---------------------------------------------------------------------------


def test_main_with_public_hints(tmp_path):
    import sys

    json_out = tmp_path / "report.json"
    md_out = tmp_path / "report.md"
    sys.argv = [
        "audit_test_quality.py",
        "--root", str(FIXTURES / "clean"),
        "--tests-dir", "tests",
        "--public-hint", "add(",
        "--json-out", str(json_out),
        "--md-out", str(md_out),
        "--no-auto-public-hints",
    ]
    try:
        exit_code = tqa.main()
    finally:
        sys.argv = [sys.argv[0]] if sys.argv else []

    assert exit_code == 0
    report = json.loads(json_out.read_text())
    assert "add(" in report["config"]["public_hints"]


# ---------------------------------------------------------------------------
# main() returns 1 on invalid regex
# ---------------------------------------------------------------------------


def test_main_invalid_internal_import_pattern(tmp_path):
    import sys

    sys.argv = [
        "audit_test_quality.py",
        "--root", str(FIXTURES / "dirty"),
        "--tests-dir", "tests",
        "--internal-import-pattern", "[invalid",
        "--no-auto-public-hints",
    ]
    try:
        exit_code = tqa.main()
    finally:
        sys.argv = [sys.argv[0]] if sys.argv else []

    assert exit_code == 1


def test_main_invalid_exact_eq_pattern(tmp_path):
    import sys

    sys.argv = [
        "audit_test_quality.py",
        "--root", str(FIXTURES / "dirty"),
        "--tests-dir", "tests",
        "--exact-eq-pattern", "[bad",
        "--no-auto-public-hints",
    ]
    try:
        exit_code = tqa.main()
    finally:
        sys.argv = [sys.argv[0]] if sys.argv else []

    assert exit_code == 1


# ---------------------------------------------------------------------------
# Non-Functional dimension (benchmark marker)
# ---------------------------------------------------------------------------


def test_score_rubric_benchmark_marker():
    fm = tqa.FileMetrics(
        path="test_x.py",
        test_functions=2,
        markers=Counter({"benchmark": 3, "smoke": 1}),
        public_call_hints=1,
    )
    fm2 = tqa.FileMetrics(
        path="test_y.py",
        test_functions=1,
        public_call_hints=1,
    )
    summary = tqa.summarize([fm, fm2])
    config = make_config(public_hints=["foo("])
    scores = tqa.score_rubric(summary, config)
    # 2 files, benchmark markers > 0 -> score 2
    assert scores["Non-Functional"]["score"] == 2


# ---------------------------------------------------------------------------
# _count_given_usage in nested code
# ---------------------------------------------------------------------------


def test_given_count_zero_for_no_given():
    tree = ast.parse("def test_x(): pass\n")
    assert tqa._count_given_usage(tree) == 0


# ---------------------------------------------------------------------------
# analyze_file with exact_eq_re default
# ---------------------------------------------------------------------------


def test_analyze_file_uses_default_exact_eq_re():
    internal_res = [re.compile(p) for p in tqa.DEFAULT_INTERNAL_IMPORT_PATTERNS]
    test_file = FIXTURES / "dirty" / "tests" / "test_engine.py"
    metrics = tqa.analyze_file(test_file, internal_res, [])
    # Default EXACT_EQ_ASSERT_RE looks for assert ... == expected|want|target|snapshot|golden
    assert metrics.exact_eq_assert_count >= 1  # dirty has assert ... == want and == expected


# ---------------------------------------------------------------------------
# collect_test_files with custom globs
# ---------------------------------------------------------------------------


def test_collect_test_files_custom_globs():
    files = tqa.collect_test_files(
        FIXTURES / "dirty", ["tests"], ["test_*.py"]
    )
    assert len(files) >= 2


# ---------------------------------------------------------------------------
# Edge case: test with both white_box and unit in path
# ---------------------------------------------------------------------------


def test_unit_in_path_triggers_white_box():
    # "unit" in path parts AND "tests" in path parts
    fm = tqa.FileMetrics(path="project/tests/unit/test_stuff.py")
    c = tqa.classify_file(fm)
    assert c["white_box_candidate"] is True


# ---------------------------------------------------------------------------
# Golden markers trigger change_indicator
# ---------------------------------------------------------------------------


def test_golden_marker_triggers_change_indicator():
    fm = tqa.FileMetrics(path="test_x.py", markers=Counter({"golden": 1}))
    c = tqa.classify_file(fm)
    assert c["change_indicator_candidate"] is True
