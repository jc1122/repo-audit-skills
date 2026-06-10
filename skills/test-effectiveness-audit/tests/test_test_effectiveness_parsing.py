"""Tests for mutmut output parsing functions.

These test the verbatim functions from the A6 task:
  - parse_results_text
  - module_totals
  - key_to_module

The implementation script (test_effectiveness_audit.py) does not exist in W1;
these tests will fail to import until W2 creates it.  That is expected.
"""
import json
from pathlib import Path

try:
    from helpers import load_module, FIXTURES
except ImportError:
    import pytest

    pytest.skip("helpers module not yet available", allow_module_level=True)

_mod = None


def _get_mod():
    global _mod
    if _mod is None:
        _mod = load_module()
    return _mod


# ---------------------------------------------------------------------------
# parse_results_text
# ---------------------------------------------------------------------------

CAPTURED_RESULTS = """\
    calc.x_weak__mutmut_1: no tests
    calc.x_weak__mutmut_2: no tests
    calc.x_weak__mutmut_3: no tests
    calc.x_weak__mutmut_4: no tests
"""


def test_parse_results_text_maps_keys_to_statuses():
    mod = _get_mod()
    problems = mod.parse_results_text(CAPTURED_RESULTS)
    assert problems == {
        "calc.x_weak__mutmut_1": "no tests",
        "calc.x_weak__mutmut_2": "no tests",
        "calc.x_weak__mutmut_3": "no tests",
        "calc.x_weak__mutmut_4": "no tests",
    }


def test_parse_results_text_preserves_whitespace_in_status():
    mod = _get_mod()
    problems = mod.parse_results_text("    a.x_f__mutmut_1: survived\n")
    assert problems == {"a.x_f__mutmut_1": "survived"}


def test_parse_results_text_ignores_non_mutmut_lines():
    """Lines without '__mutmut_' are skipped per the verbatim guard."""
    mod = _get_mod()
    text = "    a.x_f__mutmut_1: survived\n    some other output\n    b.x_g__mutmut_2: timeout\n"
    problems = mod.parse_results_text(text)
    assert problems == {
        "a.x_f__mutmut_1": "survived",
        "b.x_g__mutmut_2": "timeout",
    }


def test_captured_results_shape():
    """The committed captured results.txt must contain exactly the four weak
    mutants with 'no tests'.  The add() mutant is killed and therefore absent
    from mutmut results output."""
    text = (FIXTURES / "captured" / "results.txt").read_text()
    assert "calc.x_weak__mutmut_1: no tests" in text
    assert "calc.x_weak__mutmut_2: no tests" in text
    assert "calc.x_weak__mutmut_3: no tests" in text
    assert "calc.x_weak__mutmut_4: no tests" in text
    # The add() mutant was killed — killed mutants do not appear in results
    assert "x_add" not in text


def test_parse_results_text_empty_input():
    mod = _get_mod()
    assert mod.parse_results_text("") == {}
    assert mod.parse_results_text("\n\n") == {}


# ---------------------------------------------------------------------------
# module_totals
# ---------------------------------------------------------------------------


def test_module_totals_from_meta(tmp_path: Path):
    """Read calc.py.meta via mutants/src/calc.py.meta layout → {"src/calc.py": 5}."""
    mod = _get_mod()
    work = tmp_path / "work"
    mutants_dir = work / "mutants" / "src"
    mutants_dir.mkdir(parents=True)

    meta_src = FIXTURES / "captured" / "calc.py.meta"
    (mutants_dir / "calc.py.meta").write_text(meta_src.read_text())

    totals = mod.module_totals(work)
    assert totals == {"src/calc.py": 5}


def test_module_totals_multiple_files(tmp_path: Path):
    mod = _get_mod()
    work = tmp_path / "work"
    mutants_dir = work / "mutants"
    mutants_dir.mkdir(parents=True)
    # Write as files, not directories
    (mutants_dir / "a.py.meta").write_text(
        json.dumps({"exit_code_by_key": {"k1": 1, "k2": 1}})
    )
    (mutants_dir / "b.py.meta").write_text(
        json.dumps({"exit_code_by_key": {"k3": 1, "k4": 1, "k5": 1}})
    )

    totals = mod.module_totals(work)
    assert totals == {"a.py": 2, "b.py": 3}


# ---------------------------------------------------------------------------
# key_to_module
# ---------------------------------------------------------------------------


def test_key_to_module():
    mod = _get_mod()
    assert mod.key_to_module("src.calc.x_weak__mutmut_3") == "src/calc.py"


def test_key_to_module_deep_pkg():
    mod = _get_mod()
    assert mod.key_to_module("pkg.sub.mod.x_func__mutmut_1") == "pkg/sub/mod.py"


def test_key_to_module_single_component():
    mod = _get_mod()
    assert mod.key_to_module("simple.x_foo__mutmut_7") == "simple.py"


# ---------------------------------------------------------------------------
# problem status semantics
# ---------------------------------------------------------------------------


def test_only_survived_and_no_tests_are_problems(tmp_path: Path):
    """Only survived and 'no tests' statuses count as problems;
    timeout, suspicious, skipped do NOT count as problems.

    parse_results_text() returns EVERY entry that mutmut results outputs
    (verbatim plan contract: it preserves all statuses).  The A6 kill-rate
    rule then filters problems to {survived, no tests}; timeout/suspicious/
    skipped count as killed so they do not drag the rate down.
    """
    mod = _get_mod()
    work = tmp_path / "work"
    mutants_dir = work / "mutants" / "pkg"
    mutants_dir.mkdir(parents=True)

    # 7 mutants total: 1 killed, 2 survived, 2 no_tests, 1 timeout, 1 suspicious
    # problems = survived(2) + no_tests(2) = 4
    (mutants_dir / "mod.py.meta").write_text(
        json.dumps(
            {
                "exit_code_by_key": {
                    "pkg.mod.x_killed__mutmut_1": 1,
                    "pkg.mod.x_surv__mutmut_1": 0,
                    "pkg.mod.x_surv__mutmut_2": 0,
                    "pkg.mod.x_notest__mutmut_1": 33,
                    "pkg.mod.x_notest__mutmut_2": 33,
                    "pkg.mod.x_timeout__mutmut_1": None,
                    "pkg.mod.x_susp__mutmut_1": None,
                }
            }
        )
    )

    results_text = """\
    pkg.mod.x_surv__mutmut_1: survived
    pkg.mod.x_surv__mutmut_2: survived
    pkg.mod.x_notest__mutmut_1: no tests
    pkg.mod.x_notest__mutmut_2: no tests
    pkg.mod.x_timeout__mutmut_1: timeout
    pkg.mod.x_susp__mutmut_1: suspicious
"""

    all_entries = mod.parse_results_text(results_text)

    # parse_results_text returns EVERY entry (killed mutants are absent from
    # mutmut results output entirely, so they are naturally excluded).
    assert "pkg.mod.x_surv__mutmut_1" in all_entries
    assert "pkg.mod.x_surv__mutmut_2" in all_entries
    assert "pkg.mod.x_notest__mutmut_1" in all_entries
    assert "pkg.mod.x_notest__mutmut_2" in all_entries
    # Timeout and suspicious ARE returned by parse_results_text (verbatim contract)
    assert "pkg.mod.x_timeout__mutmut_1" in all_entries
    assert "pkg.mod.x_susp__mutmut_1" in all_entries
    # Killed mutants are absent from results text (mutmut only lists problems)
    assert "pkg.mod.x_killed__mutmut_1" not in all_entries

    # The A6 kill-rate rule: problems = subset with status in {survived, no tests}
    PROBLEM_STATUSES = {"survived", "no tests"}
    problems = {
        k: v for k, v in all_entries.items() if v in PROBLEM_STATUSES
    }

    assert len(problems) == 4
    assert set(problems.keys()) == {
        "pkg.mod.x_surv__mutmut_1",
        "pkg.mod.x_surv__mutmut_2",
        "pkg.mod.x_notest__mutmut_1",
        "pkg.mod.x_notest__mutmut_2",
    }
    assert all(v in PROBLEM_STATUSES for v in problems.values())
