"""Prong 1: Pure-function unit tests for triage_redundancy.py.

All tests import the module via helpers.load_module() and call functions
directly with small synthetic inputs. This is the bulk of in-process coverage.
"""
from __future__ import annotations

import ast
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

from helpers import load_module

# Load the module once for the session
triage = load_module()


# ── dotted_name ─────────────────────────────────────────────────────
class TestDottedName:
    def test_simple_name(self):
        node = ast.parse("x").body[0].value
        assert triage.dotted_name(node) == "x"

    def test_attribute(self):
        node = ast.parse("os.path.join").body[0].value
        assert triage.dotted_name(node) == "os.path.join"

    def test_deep_attribute(self):
        node = ast.parse("np.testing.assert_array_equal").body[0].value
        assert triage.dotted_name(node) == "np.testing.assert_array_equal"

    def test_non_name_attribute(self):
        node = ast.parse("42").body[0].value
        assert triage.dotted_name(node) == ""


# ── extract_calls ──────────────────────────────────────────────────
class TestExtractCalls:
    def test_single_call(self):
        fn = ast.parse("def f(): foo()").body[0]
        assert triage.extract_calls(fn) == {"foo"}

    def test_multiple_calls(self):
        fn = ast.parse("def f(): foo(); bar.baz()").body[0]
        assert triage.extract_calls(fn) == {"foo", "bar.baz"}

    def test_no_calls(self):
        fn = ast.parse("def f(): x = 1").body[0]
        assert triage.extract_calls(fn) == set()

    def test_nested_calls(self):
        fn = ast.parse("def f(): print(len(x))").body[0]
        assert triage.extract_calls(fn) == {"print", "len"}


# ── tokenize_normalized ────────────────────────────────────────────
class TestTokenizeNormalized:
    def test_basic(self):
        tokens = triage.tokenize_normalized("assert x + y == 5")
        assert "NUM" in tokens
        assert "assert" not in tokens  # stopword

    def test_string_literal_collapsed(self):
        tokens = triage.tokenize_normalized('x = "hello"')
        assert "STR" in tokens

    def test_number_collapsed(self):
        tokens = triage.tokenize_normalized("x = 42")
        assert "NUM" in tokens

    def test_stopwords_removed(self):
        tokens = triage.tokenize_normalized("def foo(self): return True")
        assert "def" not in tokens
        assert "self" not in tokens
        assert "return" not in tokens
        assert "True" not in tokens

    def test_short_tokens_removed(self):
        tokens = triage.tokenize_normalized("a b abc")
        # 'a' and 'b' are len <= 2, should be removed; 'abc' len 3 kept
        assert "abc" in tokens
        assert "a" not in tokens
        assert "b" not in tokens

    def test_empty(self):
        tokens = triage.tokenize_normalized("")
        assert tokens == frozenset()


# ── jaccard_sim ────────────────────────────────────────────────────
class TestJaccardSim:
    def test_identical(self):
        a = frozenset(["x", "y"])
        b = frozenset(["x", "y"])
        assert triage.jaccard_sim(a, b) == 1.0

    def test_disjoint(self):
        a = frozenset(["x"])
        b = frozenset(["y"])
        assert triage.jaccard_sim(a, b) == 0.0

    def test_partial(self):
        a = frozenset(["a", "b"])
        b = frozenset(["b", "c"])
        assert triage.jaccard_sim(a, b) == 1 / 3

    def test_empty_both(self):
        assert triage.jaccard_sim(frozenset(), frozenset()) == 1.0

    def test_empty_one(self):
        assert triage.jaccard_sim(frozenset(), frozenset(["a"])) == 0.0


# ── count_assertions ───────────────────────────────────────────────
class TestCountAssertions:
    def test_one_assert(self):
        fn = ast.parse("def f(): assert True").body[0]
        assert triage.count_assertions(fn) == 1

    def test_multiple_asserts(self):
        fn = ast.parse("def f():\n assert True\n assert False\n assert 1").body[0]
        assert triage.count_assertions(fn) == 3

    def test_no_assert(self):
        fn = ast.parse("def f(): x = 1").body[0]
        assert triage.count_assertions(fn) == 0


# ── detect_parametrized ────────────────────────────────────────────
class TestDetectParametrized:
    def test_parametrized(self):
        fn = ast.parse(
            "@pytest.mark.parametrize('x', [1,2])\ndef test_f(): pass"
        ).body[0]
        assert triage.detect_parametrized(fn) is True

    def test_not_parametrized(self):
        fn = ast.parse("def test_f(): pass").body[0]
        assert triage.detect_parametrized(fn) is False

    def test_other_decorator(self):
        fn = ast.parse("@skip\ndef test_f(): pass").body[0]
        assert triage.detect_parametrized(fn) is False


# ── infer_assertion_types ──────────────────────────────────────────
class TestInferAssertionTypes:
    def test_general_assert(self):
        fn = ast.parse("def f(): assert x == 1").body[0]
        calls = triage.extract_calls(fn)
        src = "assert x == 1"
        result = triage.infer_assertion_types(fn, calls, src)
        assert "general_assert" in result

    def test_isinstance_checked(self):
        fn = ast.parse("def f(): isinstance(x, int)").body[0]
        calls = triage.extract_calls(fn)
        src = "isinstance(x, int)"
        result = triage.infer_assertion_types(fn, calls, src)
        assert "type_check" in result

    def test_length_contract(self):
        fn = ast.parse("def f(): assert len(x) == 5").body[0]
        calls = triage.extract_calls(fn)
        src = "assert len(x) == 5"
        result = triage.infer_assertion_types(fn, calls, src)
        assert "length_contract" in result

    def test_exception_raises(self):
        src = "with pytest.raises(ValueError):\n    foo()"
        fn = ast.parse(
            "def f():\n with pytest.raises(ValueError):\n  foo()"
        ).body[0]
        calls = triage.extract_calls(fn)
        result = triage.infer_assertion_types(fn, calls, src)
        assert "exception" in result

    def test_empty(self):
        fn = ast.parse("def f(): pass").body[0]
        result = triage.infer_assertion_types(fn, set(), "")
        assert result == set()


# ── infer_entrypoint ───────────────────────────────────────────────
class TestInferEntrypoint:
    def test_with_file_fallback(self):
        result = triage.infer_entrypoint(set(), "", file_fallback="tests/test_x.py")
        assert result == "tests/test_x.py::<module>"

    def test_with_class_fallback(self):
        result = triage.infer_entrypoint(
            set(), "", file_fallback="tests/test_x.py", class_fallback="TestFoo"
        )
        assert result == "tests/test_x.py::TestFoo"

    def test_class_fallback_only(self):
        result = triage.infer_entrypoint(set(), "", class_fallback="TestFoo")
        assert result == "TestFoo"

    def test_unknown(self):
        result = triage.infer_entrypoint(set(), "")
        assert result == "unknown"


# ── infer_intent ───────────────────────────────────────────────────
class TestInferIntent:
    def test_version(self):
        result = triage.infer_intent("test_version_check", "x", set(), "")
        assert result == "introspection"

    def test_exception(self):
        result = triage.infer_intent("test_foo", "x", {"exception"}, "")
        assert result == "error_semantics"

    def test_mutability_contract(self):
        result = triage.infer_intent("test_foo", "x", {"mutability_contract"}, "")
        assert result == "shape_dtype_contract"

    def test_dtype_contract(self):
        result = triage.infer_intent("test_foo", "x", {"dtype_contract"}, "")
        assert result == "shape_dtype_contract"

    def test_array_equality(self):
        result = triage.infer_intent("test_foo", "x", {"array_equality"}, "")
        assert result == "parity_equivalence"

    def test_monkeypatch_in_name(self):
        result = triage.infer_intent("test_with_monkeypatch", "x", set(), "")
        assert result == "mock_isolation"

    def test_mock_in_name(self):
        result = triage.infer_intent("test_mock_thing", "x", set(), "")
        assert result == "mock_isolation"

    def test_lifecycle(self):
        result = triage.infer_intent("test_lifecycle_stuff", "x", set(), "")
        assert result == "lifecycle_contract"

    def test_ffi_ctypes(self):
        result = triage.infer_intent("test_ctypes_call", "x", set(), "")
        assert result == "ffi_contract"

    def test_ffi_cdll(self):
        result = triage.infer_intent("test_with_cdll", "x", set(), "")
        assert result == "ffi_contract"

    def test_monkeypatch_in_src(self):
        result = triage.infer_intent("test_x", "x", set(), "x = monkeypatch")
        assert result == "mock_isolation"

    def test_ctypes_in_src(self):
        result = triage.infer_intent("test_x", "x", set(), "x = ctypes.CDLL")
        assert result == "ffi_contract"

    def test_default(self):
        result = triage.infer_intent("test_basic", "x", set(), "")
        assert result == "shape_dtype_contract"


# ── infer_test_status ──────────────────────────────────────────────
class TestInferTestStatus:
    def test_passed(self):
        assert triage.infer_test_status(0, "1 passed") == "passed"

    def test_skipped(self):
        assert triage.infer_test_status(0, "1 skipped") == "skipped"

    def test_failed(self):
        assert triage.infer_test_status(1, "1 failed") == "failed"

    def test_nonzero_with_skip(self):
        assert triage.infer_test_status(1, "1 skipped") == "failed"


# ── normalize_source_path_for_coverage ─────────────────────────────
class TestNormalizeSourcePathForCoverage:
    def test_absolute_under_root(self):
        root = Path("/repo")
        result = triage.normalize_source_path_for_coverage("/repo/src/foo.py", root)
        assert result == "src/foo.py"

    def test_windows_backslash(self):
        root = Path("/repo")
        result = triage.normalize_source_path_for_coverage(
            "\\repo\\src\\foo.py", root
        )
        assert result == "src/foo.py"

    def test_dot_slash(self):
        root = Path("/repo")
        result = triage.normalize_source_path_for_coverage("./src/foo.py", root)
        assert result == "src/foo.py"

    def test_no_prefix(self):
        root = Path("/repo")
        result = triage.normalize_source_path_for_coverage(
            "/other/src/foo.py", root
        )
        assert result == "/other/src/foo.py"


# ── Coercers ───────────────────────────────────────────────────────
class TestAsBool:
    def test_true_bool(self):
        assert triage.as_bool(True) is True

    def test_false_bool(self):
        assert triage.as_bool(False) is False

    def test_true_int(self):
        assert triage.as_bool(1) is True

    def test_false_int(self):
        assert triage.as_bool(0) is False

    def test_string_true(self):
        assert triage.as_bool("true") is True

    def test_string_one(self):
        assert triage.as_bool("1") is True

    def test_string_yes(self):
        assert triage.as_bool("yes") is True

    def test_string_false(self):
        assert triage.as_bool("false") is False

    def test_string_empty(self):
        assert triage.as_bool("") is False


class TestAsInt:
    def test_int(self):
        assert triage.as_int(42) == 42

    def test_string(self):
        assert triage.as_int("42") == 42

    def test_float_str(self):
        assert triage.as_int("3.14") == 0

    def test_invalid(self):
        assert triage.as_int("abc") == 0

    def test_none(self):
        assert triage.as_int(None) == 0


class TestAsFloat:
    def test_float(self):
        assert triage.as_float(3.14) == 3.14

    def test_int(self):
        assert triage.as_float(42) == 42.0

    def test_string(self):
        assert triage.as_float("3.14") == 3.14

    def test_invalid(self):
        assert triage.as_float("abc") == 0.0

    def test_none(self):
        assert triage.as_float(None) == 0.0


class TestAsBoolAny:
    def test_bool(self):
        assert triage.as_bool_any(True) is True

    def test_int_true(self):
        assert triage.as_bool_any(1) is True

    def test_int_false(self):
        assert triage.as_bool_any(0) is False

    def test_string(self):
        assert triage.as_bool_any("true") is True

    def test_other(self):
        assert triage.as_bool_any("no") is False


class TestTriState:
    def test_true(self):
        assert triage.tri_state(True) == "pass"

    def test_false(self):
        assert triage.tri_state(False) == "fail"

    def test_none(self):
        assert triage.tri_state(None) == "unknown"


# ── chunked ────────────────────────────────────────────────────────
class TestChunked:
    def test_even_split(self):
        assert triage.chunked([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

    def test_uneven(self):
        assert triage.chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

    def test_size_one(self):
        assert triage.chunked([1, 2, 3], 1) == [[1], [2], [3]]

    def test_size_larger(self):
        assert triage.chunked([1, 2], 10) == [[1, 2]]

    def test_empty(self):
        assert triage.chunked([], 3) == []

    def test_size_zero(self):
        assert triage.chunked([1, 2], 0) == [[1, 2]]

    def test_size_negative(self):
        assert triage.chunked([1, 2], -1) == [[1, 2]]

    def test_empty_size_zero(self):
        assert triage.chunked([], 0) == []


# ── unique_preserve ────────────────────────────────────────────────
class TestUniquePreserve:
    def test_removes_dupes(self):
        assert triage.unique_preserve(["a", "b", "a", "c"]) == ["a", "b", "c"]

    def test_filters_empty(self):
        assert triage.unique_preserve(["a", "", "b", ""]) == ["a", "b"]

    def test_preserves_order(self):
        assert triage.unique_preserve(["c", "a", "b", "a"]) == ["c", "a", "b"]

    def test_empty_list(self):
        assert triage.unique_preserve([]) == []


# ── build_default_mutation_probes ──────────────────────────────────
class TestBuildDefaultMutationProbes:
    def test_returns_empty(self):
        assert triage.build_default_mutation_probes() == []


# ── load_mutation_probes_from_config ───────────────────────────────
class TestLoadMutationProbesFromConfig:
    def test_valid_config(self, tmp_path):
        config = tmp_path / "probes.json"
        config.write_text(json.dumps([
            {"probe_id": "P001", "file": "src/foo.py", "old": "return x", "new": "return y"}
        ]))
        probes = triage.load_mutation_probes_from_config(config)
        assert len(probes) == 1
        assert probes[0].probe_id == "P001"
        assert probes[0].old == "return x"
        assert probes[0].new == "return y"

    def test_missing_key(self, tmp_path):
        config = tmp_path / "probes.json"
        config.write_text(json.dumps([{"probe_id": "P001"}]))
        with pytest.raises(SystemExit):
            triage.load_mutation_probes_from_config(config)

    def test_empty(self, tmp_path):
        config = tmp_path / "probes.json"
        config.write_text("[]")
        probes = triage.load_mutation_probes_from_config(config)
        assert probes == []

    def test_invalid_json(self, tmp_path):
        config = tmp_path / "probes.json"
        config.write_text("{bad")
        with pytest.raises(SystemExit):
            triage.load_mutation_probes_from_config(config)


# ── apply_mutation_probe ───────────────────────────────────────────
class TestApplyMutationProbe:
    def test_single_replacement(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("return x")
        probe = triage.MutationProbe("P001", "target.py", "return x", "return y")
        ok, err = triage.apply_mutation_probe(tmp_path, probe)
        assert ok
        assert err == ""
        assert target.read_text() == "return y"

    def test_count_mismatch(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("return x\nreturn x")
        probe = triage.MutationProbe("P001", "target.py", "return x", "return y")
        ok, err = triage.apply_mutation_probe(tmp_path, probe)
        assert not ok
        assert "count mismatch" in err

    def test_file_missing(self, tmp_path):
        probe = triage.MutationProbe("P001", "nonexistent.py", "old", "new")
        ok, err = triage.apply_mutation_probe(tmp_path, probe)
        assert not ok
        assert "missing" in err

    def test_no_occurrence(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("something else")
        probe = triage.MutationProbe("P001", "target.py", "return x", "return y")
        ok, err = triage.apply_mutation_probe(tmp_path, probe)
        assert not ok


# ── resolve_python_exe ─────────────────────────────────────────────
class TestResolvePythonExe:
    def test_absolute_path(self, tmp_path):
        exe = tmp_path / "python3"
        exe.write_text("")
        exe.chmod(0o755)
        result = triage.resolve_python_exe(tmp_path, str(exe))
        assert result == str(exe)

    def test_which_fallback(self):
        result = triage.resolve_python_exe(Path("/"), "python3")
        assert result == "python3" or "python" in result

    def test_relative_with_slash(self, tmp_path):
        (tmp_path / "venv").mkdir()
        exe = tmp_path / "venv" / "python"
        exe.write_text("")
        exe.chmod(0o755)
        result = triage.resolve_python_exe(tmp_path, "venv/python")
        assert str(exe) in result


# ── resolve_optional_path ──────────────────────────────────────────
class TestResolveOptionalPath:
    def test_empty_string(self):
        assert triage.resolve_optional_path(Path("/"), "") is None

    def test_absolute_path(self):
        result = triage.resolve_optional_path(Path("/"), "/tmp")
        assert result == Path("/tmp")

    def test_relative_path(self):
        result = triage.resolve_optional_path(Path("/repo"), "artifacts")
        assert result == Path("/repo/artifacts")


# ── discover_import_roots ──────────────────────────────────────────
class TestDiscoverImportRoots:
    def test_with_src_dir(self, tmp_path):
        (tmp_path / "src").mkdir()
        result = triage.discover_import_roots(tmp_path)
        assert str(tmp_path / "src") in result
        assert str(tmp_path) in result

    def test_without_src_dir(self, tmp_path):
        result = triage.discover_import_roots(tmp_path)
        assert result == [str(tmp_path)]


# ── parse_test_metadata ────────────────────────────────────────────
class TestParseTestMetadata:
    def test_single_simple_test(self, tmp_path):
        test_file = tmp_path / "fixture_test.py"
        test_file.write_text("def test_pass(): assert True")
        result = triage.parse_test_metadata(tmp_path, ["fixture_test.py"])
        assert len(result) == 1
        t = result[0]
        assert t.test_name == "test_pass"
        assert t.assert_count == 1
        assert t.is_parametrized is False

    def test_parametrized_test(self, tmp_path):
        test_file = tmp_path / "fixture_test.py"
        test_file.write_text(
            "import pytest\n"
            "@pytest.mark.parametrize('x', [1,2])\n"
            "def test_f(x): assert x > 0"
        )
        result = triage.parse_test_metadata(tmp_path, ["fixture_test.py"])
        assert len(result) == 1
        assert result[0].is_parametrized is True

    def test_class_based_test(self, tmp_path):
        test_file = tmp_path / "fixture_test.py"
        test_file.write_text(
            "class TestFoo:\n"
            "    def test_bar(self):\n"
            "        assert True\n"
        )
        result = triage.parse_test_metadata(tmp_path, ["fixture_test.py"])
        assert len(result) == 1
        t = result[0]
        assert t.class_name == "TestFoo"
        assert t.test_name == "test_bar"

    def test_non_test_skipped(self, tmp_path):
        test_file = tmp_path / "fixture_test.py"
        test_file.write_text("def helper(): pass\ndef test_real(): assert True")
        result = triage.parse_test_metadata(tmp_path, ["fixture_test.py"])
        assert len(result) == 1
        assert result[0].test_name == "test_real"

    def test_missing_file(self, tmp_path):
        result = triage.parse_test_metadata(tmp_path, ["nonexistent.py"])
        assert result == []

    def test_multiple_files(self, tmp_path):
        (tmp_path / "a_test.py").write_text("def test_a(): assert True")
        (tmp_path / "b_test.py").write_text("def test_b(): assert False")
        result = triage.parse_test_metadata(
            tmp_path, ["a_test.py", "b_test.py"]
        )
        assert len(result) == 2
        names = {t.test_name for t in result}
        assert names == {"test_a", "test_b"}

    def test_sorted_by_nodeid(self, tmp_path):
        (tmp_path / "z_test.py").write_text("def test_z(): pass")
        (tmp_path / "a_test.py").write_text("def test_a(): pass")
        result = triage.parse_test_metadata(
            tmp_path, ["z_test.py", "a_test.py"]
        )
        assert result[0].test_name == "test_a"


# ── CSV read/write ─────────────────────────────────────────────────
class TestCsvRoundTrip:
    def test_write_and_read(self, tmp_path):
        path = tmp_path / "out.csv"
        rows = [{"a": "1", "b": "hello"}, {"a": "2", "b": "world"}]
        triage.write_csv(path, rows, ["a", "b"])
        assert path.exists()
        result = triage.read_csv_rows(path)
        assert result == rows

    def test_write_extra_keys(self, tmp_path):
        path = tmp_path / "out.csv"
        rows = [{"a": "1", "b": "hello"}]
        triage.write_csv(path, rows, ["a"])
        result = triage.read_csv_rows(path)
        assert result[0] == {"a": "1"}

    def test_write_missing_keys(self, tmp_path):
        path = tmp_path / "out.csv"
        rows = [{"a": "1"}]
        triage.write_csv(path, rows, ["a", "b"])
        result = triage.read_csv_rows(path)
        assert result[0]["b"] == ""


# ── parse_ranked_by_nodeid ─────────────────────────────────────────
class TestParseRankedByNodeid:
    def test_valid_csv(self, tmp_path):
        path = tmp_path / "ranked.csv"
        triage.write_csv(
            path,
            [{"test_nodeid": "t1", "val": "x"}, {"test_nodeid": "t2", "val": "y"}],
            ["test_nodeid", "val"],
        )
        result = triage.parse_ranked_by_nodeid(path)
        assert result == {
            "t1": {"test_nodeid": "t1", "val": "x"},
            "t2": {"test_nodeid": "t2", "val": "y"},
        }

    def test_missing_file(self):
        result = triage.parse_ranked_by_nodeid(Path("/nonexistent"))
        assert result == {}

    def test_none_path(self):
        result = triage.parse_ranked_by_nodeid(None)
        assert result == {}

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.csv"
        path.write_text("test_nodeid\n")
        result = triage.parse_ranked_by_nodeid(path)
        assert result == {}


# ── parse_inventory_assertions ─────────────────────────────────────
class TestParseInventoryAssertions:
    def test_with_assertions(self, tmp_path):
        path = tmp_path / "inv.csv"
        triage.write_csv(
            path,
            [
                {"test_nodeid": "t1", "assertion_types": "type_check;general_assert"},
                {"test_nodeid": "t2", "assertion_types": "exception"},
            ],
            ["test_nodeid", "assertion_types"],
        )
        result = triage.parse_inventory_assertions(path)
        assert result == {
            "t1": {"type_check", "general_assert"},
            "t2": {"exception"},
        }

    def test_empty_assertions(self, tmp_path):
        path = tmp_path / "inv.csv"
        triage.write_csv(
            path,
            [{"test_nodeid": "t1", "assertion_types": ""}],
            ["test_nodeid", "assertion_types"],
        )
        result = triage.parse_inventory_assertions(path)
        assert result == {"t1": set()}

    def test_missing(self):
        assert triage.parse_inventory_assertions(Path("/nonexistent")) == {}


# ── parse_coverage_json ────────────────────────────────────────────
class TestParseCoverageJson:
    def test_with_data(self, tmp_path):
        root = tmp_path
        (root / "src").mkdir(exist_ok=True)
        src_file = root / "src" / "foo.py"
        src_file.write_text("")
        json_path = tmp_path / "cov.json"
        json_path.write_text(
            json.dumps(
                {
                    "files": {
                        str(src_file): {
                            "executed_lines": [1, 2, 3],
                            "executed_branches": [[1, 0], [1, 1]],
                        }
                    }
                }
            )
        )
        lines, branches = triage.parse_coverage_json(json_path, root)
        assert "L|src/foo.py|1" in lines
        assert "B|src/foo.py|1|0" in branches
        assert "B|src/foo.py|1|1" in branches

    def test_missing_file(self, tmp_path):
        lines, branches = triage.parse_coverage_json(
            tmp_path / "nonexistent.json", tmp_path
        )
        assert lines == set()
        assert branches == set()

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{bad")
        lines, branches = triage.parse_coverage_json(path, tmp_path)
        assert lines == set()

    def test_source_prefix_filter(self, tmp_path):
        root = tmp_path
        (root / "src").mkdir(exist_ok=True)
        (root / "tests").mkdir(exist_ok=True)
        src_file = root / "src" / "foo.py"
        test_file = root / "tests" / "bar.py"
        src_file.write_text("")
        test_file.write_text("")
        json_path = tmp_path / "cov.json"
        json_path.write_text(
            json.dumps(
                {
                    "files": {
                        str(src_file): {"executed_lines": [1]},
                        str(test_file): {"executed_lines": [2]},
                    }
                }
            )
        )
        lines, _ = triage.parse_coverage_json(json_path, root, source_prefix="src/")
        assert len(lines) == 1
        assert "L|src/foo.py|1" in lines


# ── select_branch_anchor ───────────────────────────────────────────
class TestSelectBranchAnchor:
    def test_with_peers(self):
        tests = [
            triage.TestMeta(
                nodeid="a::test_x", file="a.py", class_name="", test_name="test_x",
                entrypoint="ep", intent="int", assertion_types={"general_assert"},
                assert_count=1, src_tokens=frozenset({"foo", "bar"}),
            ),
            triage.TestMeta(
                nodeid="a::test_y", file="a.py", class_name="", test_name="test_y",
                entrypoint="ep", intent="int", assertion_types={"general_assert"},
                assert_count=2, src_tokens=frozenset({"foo", "baz"}),
            ),
        ]
        anchor = triage.select_branch_anchor(tests[0], tests[1:], {})
        assert anchor is not None
        assert anchor.nodeid == "a::test_y"  # higher assert count

    def test_no_peers(self):
        t = triage.TestMeta(
            nodeid="a::test_x", file="a.py", class_name="", test_name="test_x",
            entrypoint="ep", intent="int", assertion_types=set(),
            assert_count=1, src_tokens=frozenset(),
        )
        assert triage.select_branch_anchor(t, [], {}) is None

    def test_prefers_non_delete(self):
        t1 = triage.TestMeta(
            nodeid="a::test_x", file="a.py", class_name="", test_name="test_x",
            entrypoint="ep", intent="int", assertion_types={"general_assert"},
            assert_count=1, src_tokens=frozenset({"a"}),
        )
        t2 = triage.TestMeta(
            nodeid="a::test_y", file="a.py", class_name="", test_name="test_y",
            entrypoint="ep", intent="int", assertion_types={"general_assert"},
            assert_count=1, src_tokens=frozenset({"a"}),
        )
        t3 = triage.TestMeta(
            nodeid="a::test_z", file="a.py", class_name="", test_name="test_z",
            entrypoint="ep", intent="int", assertion_types={"general_assert"},
            assert_count=5, src_tokens=frozenset({"a"}),
        )
        # t2 is DELETE_SAFE_HIGH, t3 is not
        decision = {"a::test_y": "DELETE_SAFE_HIGH"}
        anchor = triage.select_branch_anchor(t1, [t2, t3], decision)
        assert anchor.nodeid == "a::test_z"


# ── enforce_cluster_anchor ─────────────────────────────────────────
class TestEnforceClusterAnchor:
    def test_all_delete_tagged(self):
        rows = [
            {
                "test_nodeid": "t1", "entrypoint": "ep", "intent": "int",
                "validation_decision": "DELETE_SAFE_HIGH",
                "assert_count": 1, "report_unique_line_count": 0,
                "report_unique_branch_count": 0, "report_mutants_unique_to_api": 0,
                "max_src_similarity": 0.5,
            },
            {
                "test_nodeid": "t2", "entrypoint": "ep", "intent": "int",
                "validation_decision": "DELETE_SAFE_HIGH",
                "assert_count": 3, "report_unique_line_count": 0,
                "report_unique_branch_count": 0, "report_mutants_unique_to_api": 0,
                "max_src_similarity": 0.9,
            },
        ]
        triage.enforce_cluster_anchor(rows)
        decisions = {r["test_nodeid"]: r["validation_decision"] for r in rows}
        # The one with higher assert_count should be kept
        assert decisions["t2"] == "KEEP_FOR_CONTRACT"

    def test_mixed_decisions(self):
        rows = [
            {
                "test_nodeid": "t1", "entrypoint": "ep", "intent": "int",
                "validation_decision": "DELETE_SAFE_HIGH",
                "assert_count": 1, "report_unique_line_count": 0,
                "report_unique_branch_count": 0, "report_mutants_unique_to_api": 0,
                "max_src_similarity": 0.5,
            },
            {
                "test_nodeid": "t2", "entrypoint": "ep", "intent": "int",
                "validation_decision": "KEEP_FOR_SIGNAL",
                "assert_count": 2, "report_unique_line_count": 0,
                "report_unique_branch_count": 0, "report_mutants_unique_to_api": 0,
                "max_src_similarity": 0.5,
            },
        ]
        triage.enforce_cluster_anchor(rows)
        # t1 should remain DELETE since not all are DELETE
        assert rows[0]["validation_decision"] == "DELETE_SAFE_HIGH"


# ── bool_low_signal ────────────────────────────────────────────────
_sentinel = object()


class TestBoolLowSignal:
    def _make_meta(self, assertion_types=_sentinel):
        if assertion_types is _sentinel:
            assertion_types = {"general_assert"}
        return triage.TestMeta(
            nodeid="t1", file="f.py", class_name="", test_name="test_x",
            entrypoint="ep", intent="int",
            assertion_types=assertion_types,
            assert_count=1, src_tokens=frozenset(),
        )

    def test_ranked_low_signal(self):
        meta = self._make_meta()
        ranked = {
            "unique_line_count": "0", "unique_branch_count": "0",
            "mutants_unique_to_api": "0", "cross_suite_overlap_ratio": "1.0",
        }
        result = triage.bool_low_signal(meta, ranked, None)
        assert result is True

    def test_ranked_not_low_signal(self):
        meta = self._make_meta()
        ranked = {
            "unique_line_count": "5", "unique_branch_count": "0",
            "mutants_unique_to_api": "0", "cross_suite_overlap_ratio": "1.0",
        }
        result = triage.bool_low_signal(meta, ranked, None)
        assert result is False

    def test_ast_fallback(self):
        meta = self._make_meta({"general_assert"})
        result = triage.bool_low_signal(meta, {}, None)
        assert result is True

    def test_ast_complex_assertions(self):
        meta = self._make_meta({"exception"})
        result = triage.bool_low_signal(meta, {}, None)
        assert result is False

    def test_ast_empty_assertions(self):
        meta = self._make_meta(set())
        result = triage.bool_low_signal(meta, {}, None)
        assert result is False  # conservative: empty assertions -> not low signal

    def test_branch_equiv_has_unique(self):
        meta = self._make_meta()
        branch = {"branch_candidate_only_count": 3}
        result = triage.bool_low_signal(meta, {}, None, branch_equiv_row=branch)
        assert result is False

    def test_branch_equiv_no_unique(self):
        meta = self._make_meta({"general_assert"})
        branch = {"branch_candidate_only_count": 0}
        result = triage.bool_low_signal(meta, {}, None, branch_equiv_row=branch)
        assert result is True


# ── build_runtime_env ──────────────────────────────────────────────
class TestBuildRuntimeEnv:
    def test_basic(self, tmp_path):
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        env = triage.build_runtime_env(
            tmp_path, out_dir, "python3", allow_numba_stub=False
        )
        assert "PYTHONPATH" in env
        assert str(tmp_path) in env["PYTHONPATH"]

    def test_with_extra_env(self, tmp_path):
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        env = triage.build_runtime_env(
            tmp_path, out_dir, "python3",
            allow_numba_stub=False,
            extra_env={"MY_VAR": "hello"},
        )
        assert env.get("MY_VAR") == "hello"


# ── ensure_numba_stub ──────────────────────────────────────────────
class TestEnsureNumbaStub:
    def test_creates_stub(self, tmp_path):
        stub = triage.ensure_numba_stub(tmp_path)
        assert stub.exists()
        numba_init = stub / "numba" / "__init__.py"
        assert numba_init.exists()
        content = numba_init.read_text()
        assert "def njit" in content


# ── prepend_pythonpath ─────────────────────────────────────────────
class TestPrependPythonpath:
    def test_adds_prefix(self):
        env = {"OTHER": "val"}
        result = triage.prepend_pythonpath(env, "/extra/path")
        assert result["PYTHONPATH"] == "/extra/path"
        assert result["OTHER"] == "val"

    def test_merges_existing(self):
        env = {"PYTHONPATH": "/existing"}
        result = triage.prepend_pythonpath(env, "/extra")
        assert result["PYTHONPATH"] == "/extra" + triage.os.pathsep + "/existing"

    def test_empty_prefix(self):
        env = {"PYTHONPATH": "/existing"}
        result = triage.prepend_pythonpath(env, "")
        assert result["PYTHONPATH"] == "/existing"


# ── has_xdist_plugin ──────────────────────────────────────────────
class TestHasXdistPlugin:
    def test_in_process(self):
        # In-process test: xdist may or may not be installed
        result = triage.has_xdist_plugin(Path("."), "python3", triage.os.environ.copy())
        assert isinstance(result, bool)
