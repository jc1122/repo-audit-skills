#!/usr/bin/env python3
"""
Quick static inventory for test-suite quality signals.

This script is intentionally lightweight and language-agnostic at the metric layer.
It does not execute tests; it inspects test sources and reports useful ratios:
    - public vs private API usage patterns
    - internal implementation import coupling
    - marker distribution
    - exception assertion precision
    - snapshot/change-indicator heuristics
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MARKER_RE = re.compile(r"@pytest\.mark\.([a-zA-Z_][a-zA-Z0-9_]*)")
PRIVATE_METHOD_CALL_RE = re.compile(r"\.\_[A-Za-z0-9_]+\s*\(")
EXPECTED_LITERAL_RE = re.compile(r"^\s*expected\s*=\s*\(", re.MULTILINE)
EXACT_EQ_ASSERT_RE = re.compile(
    r"^\s*assert\s+\w+\s*==\s*(?:expected|want|target|snapshot|golden)\b",
    re.MULTILINE,
)
# Structural pytest markers that dominate counts but carry no test-category signal.
PYTEST_BUILTIN_MARKERS = frozenset(
    {
        "parametrize",
        "skip",
        "skipif",
        "xfail",
        "usefixtures",
        "filterwarnings",
        "timeout",
    }
)
DEFAULT_INTERNAL_IMPORT_PATTERNS = (
    r"from\s+[\w\.]+\.(?:core|internal|impl|private)\s+import",
    r"import\s+[\w\.]+\.(?:core|internal|impl|private)\b",
)
DEFAULT_TEST_GLOBS = ("test_*.py", "*_test.py")


@dataclass
class FileMetrics:
    path: str
    test_functions: int = 0
    private_method_calls: int = 0
    public_call_hints: int = 0
    internal_imports: int = 0
    raises_total: int = 0
    raises_with_match: int = 0
    raises_broad_tuple: int = 0
    expected_literal_count: int = 0
    exact_eq_assert_count: int = 0
    given_count: int = 0
    markers: Counter[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "test_functions": self.test_functions,
            "private_method_calls": self.private_method_calls,
            "public_call_hints": self.public_call_hints,
            "internal_imports": self.internal_imports,
            "raises_total": self.raises_total,
            "raises_with_match": self.raises_with_match,
            "raises_broad_tuple": self.raises_broad_tuple,
            "expected_literal_count": self.expected_literal_count,
            "exact_eq_assert_count": self.exact_eq_assert_count,
            "given_count": self.given_count,
            "markers": dict(self.markers or {}),
            "classification": classify_file(self),
        }


def _split_csv_values(values: list[str] | None) -> list[str]:
    if not values:
        return []
    items: list[str] = []
    for raw in values:
        for value in raw.split(","):
            cleaned = value.strip()
            if cleaned:
                items.append(cleaned)
    return items


def _extract_all_strings(node: ast.AST) -> list[str]:
    strings: list[str] = []
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                strings.append(elt.value)
    return strings


def infer_public_hints(root: Path) -> list[str]:
    """Infer likely public call hints from __init__.py exports.

    The goal is portability, not perfect precision. We scan top-level package
    initializers and use discovered public names as `name(` hints.
    """
    hints: set[str] = set()
    init_files = sorted(root.glob("src/**/__init__.py")) + sorted(
        root.glob("*/__init__.py")
    )
    for init_file in init_files:
        if ".venv" in init_file.parts:
            continue
        try:
            tree = ast.parse(
                init_file.read_text(encoding="utf-8"), filename=str(init_file)
            )
        except (SyntaxError, ValueError, OSError, UnicodeDecodeError):
            continue

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith("_"):
                    hints.add(f"{node.name}(")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        for exported in _extract_all_strings(node.value):
                            if exported and not exported.startswith("_"):
                                hints.add(f"{exported}(")
    return sorted(hints)


def _extract_mark_names(node: ast.AST, out: list[str]) -> None:
    if isinstance(node, (ast.List, ast.Tuple)):
        for elt in node.elts:
            _extract_mark_names(elt, out)
    elif isinstance(node, ast.Call):
        _extract_mark_names(node.func, out)
    elif isinstance(node, ast.Attribute) and (
        isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "pytest"
    ):
        out.append(node.attr)


def _collect_pytestmark_names(tree: ast.AST) -> list[str]:
    """Extract marker names from module-level pytestmark assignments."""
    names: list[str] = []
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets
        ):
            continue
        _extract_mark_names(node.value, names)
    return names


def _is_pytest_raises_call(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Attribute):
        if node.func.attr != "raises":
            return False
        if isinstance(node.func.value, ast.Name) and node.func.value.id == "pytest":
            return True
    return False


def _count_test_functions(tree: ast.AST) -> int:
    count = 0
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ) and node.name.startswith("test_"):
            count += 1
    return count


def _count_given_usage(tree: ast.AST) -> int:
    count = 0
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "given"
        ):
            count += 1
    return count


def _count_pytest_raises(tree: ast.AST) -> tuple[int, int, int]:
    total = 0
    with_match = 0
    broad_tuple = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_pytest_raises_call(node):
            total += 1
            if any(k.arg == "match" for k in node.keywords if k.arg is not None):
                with_match += 1
            if (
                node.args
                and isinstance(node.args[0], ast.Tuple)
                and len(node.args[0].elts) > 1
            ):
                broad_tuple += 1
    return total, with_match, broad_tuple


def classify_file(metrics: FileMetrics) -> dict[str, bool]:
    path_parts = set(Path(metrics.path).parts)
    is_white_box = (
        ("unit" in path_parts and "tests" in path_parts)
        or metrics.internal_imports > 0
        or metrics.private_method_calls > 0
    )
    is_black_box = metrics.public_call_hints > 0 and metrics.internal_imports == 0
    is_change_indicator = (
        metrics.expected_literal_count > 0 and metrics.exact_eq_assert_count > 0
    ) or ("golden" in (metrics.markers or {}))
    return {
        "white_box_candidate": is_white_box,
        "black_box_candidate": is_black_box,
        "change_indicator_candidate": is_change_indicator,
    }


def analyze_file(
    path: Path,
    internal_import_res: list[re.Pattern[str]],
    public_hints: list[str],
    exact_eq_re: re.Pattern[str] = EXACT_EQ_ASSERT_RE,
) -> FileMetrics:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as exc:
        print(
            f"warning: skipping unparseable file {path}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return FileMetrics(path=str(path))
    markers = Counter(MARKER_RE.findall(text))
    markers.update(_collect_pytestmark_names(tree))
    raises_total, raises_with_match, raises_broad_tuple = _count_pytest_raises(tree)
    public_call_hints = sum(text.count(hint) for hint in public_hints)
    internal_imports = sum(
        len(pattern.findall(text)) for pattern in internal_import_res
    )
    return FileMetrics(
        path=str(path),
        test_functions=_count_test_functions(tree),
        private_method_calls=len(PRIVATE_METHOD_CALL_RE.findall(text)),
        public_call_hints=public_call_hints,
        internal_imports=internal_imports,
        raises_total=raises_total,
        raises_with_match=raises_with_match,
        raises_broad_tuple=raises_broad_tuple,
        expected_literal_count=len(EXPECTED_LITERAL_RE.findall(text)),
        exact_eq_assert_count=len(exact_eq_re.findall(text)),
        given_count=_count_given_usage(tree),
        markers=markers,
    )


def collect_test_files(
    root: Path, test_dirs: list[str], test_globs: list[str]
) -> list[Path]:
    files: set[Path] = set()
    for test_dir in test_dirs:
        base = root / test_dir
        if not base.exists():
            print(
                f"warning: test dir not found, skipping: {base}",
                file=sys.stderr,
                flush=True,
            )
            continue
        for glob_pattern in test_globs:
            for path in base.rglob(glob_pattern):
                if path.is_file():
                    files.add(path)
    return sorted(files)


def _marker_and_classification_counts(
    file_metrics: list[FileMetrics],
) -> tuple[Counter[str], Counter[str]]:
    marker_totals: Counter[str] = Counter()
    classifications: Counter[str] = Counter()

    for m in file_metrics:
        marker_totals.update(m.markers or {})
        c = classify_file(m)
        for key, value in c.items():
            if value:
                classifications[key] += 1
    return marker_totals, classifications


def _summary_totals(file_metrics: list[FileMetrics]) -> dict[str, int]:
    totals = {
        "files": len(file_metrics),
        "test_functions": 0,
        "private_method_calls": 0,
        "public_call_hints": 0,
        "internal_imports": 0,
        "raises_total": 0,
        "raises_with_match": 0,
        "raises_broad_tuple": 0,
        "hypothesis_given_calls": 0,
        "expected_literal_count": 0,
        "exact_eq_assert_count": 0,
    }
    for m in file_metrics:
        totals["test_functions"] += m.test_functions
        totals["private_method_calls"] += m.private_method_calls
        totals["public_call_hints"] += m.public_call_hints
        totals["internal_imports"] += m.internal_imports
        totals["raises_total"] += m.raises_total
        totals["raises_with_match"] += m.raises_with_match
        totals["raises_broad_tuple"] += m.raises_broad_tuple
        totals["hypothesis_given_calls"] += m.given_count
        totals["expected_literal_count"] += m.expected_literal_count
        totals["exact_eq_assert_count"] += m.exact_eq_assert_count
    return totals


def _summary_ratios(totals: dict[str, int]) -> dict[str, float]:
    total_private = totals["private_method_calls"]
    total_public = totals["public_call_hints"]
    total_raises = totals["raises_total"]
    raises_match = totals["raises_with_match"]
    broad_tuple_raises = totals["raises_broad_tuple"]
    return {
        "private_to_public_call_ratio": round(
            total_private / max(total_public, 1), 3
        ),
        "raises_with_match_ratio": round(raises_match / max(total_raises, 1), 3),
        "broad_tuple_raises_ratio": round(
            broad_tuple_raises / max(total_raises, 1), 3
        ),
    }


def summarize(file_metrics: list[FileMetrics]) -> dict[str, Any]:
    marker_totals, classifications = _marker_and_classification_counts(file_metrics)
    totals = _summary_totals(file_metrics)

    return {
        "totals": totals,
        "ratios": _summary_ratios(totals),
        "classification_counts": dict(classifications),
        "markers": dict(marker_totals),
    }


def parse_coverage_json(cov_json_path: str) -> dict[str, float]:
    """Parse a coverage.json file and extract statement/branch percentages."""
    try:
        data = json.loads(Path(cov_json_path).read_text(encoding="utf-8"))
        totals = data.get("totals", {})
        result: dict[str, float] = {}
        if "percent_covered" in totals:
            result["statement_pct"] = round(float(totals["percent_covered"]), 2)
        if "covered_branches" in totals and "num_branches" in totals:
            num = totals["num_branches"]
            if num > 0:
                result["branch_pct"] = round(
                    100.0 * totals["covered_branches"] / num, 2
                )
        return result
    except (json.JSONDecodeError, FileNotFoundError, KeyError, TypeError) as exc:
        print(
            f"warning: could not parse coverage JSON {cov_json_path}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return {}


def _score_entry(score: int, rationale: str) -> dict[str, Any]:
    return {"score": score, "max": 3, "rationale": rationale}


def _score_contract_coverage(totals: dict[str, Any]) -> dict[str, Any]:
    if totals["public_call_hints"] > 0 and totals["raises_with_match"] > 0:
        return _score_entry(3, "Public call hints and precise raises detected")
    if totals["public_call_hints"] > 0:
        return _score_entry(2, "Public call hints detected but no precise raises")
    if totals["test_functions"] > 0:
        return _score_entry(1, "Tests exist but no public call hints")
    return _score_entry(0, "No test functions detected")


def _score_behavior_first(
    totals: dict[str, Any], ratios: dict[str, Any]
) -> dict[str, Any]:
    priv_pub_ratio = ratios["private_to_public_call_ratio"]
    if priv_pub_ratio < 0.3 and totals["public_call_hints"] > 0:
        return _score_entry(
            3, f"Low private/public ratio ({priv_pub_ratio}) with public hints"
        )
    if priv_pub_ratio < 0.5:
        return _score_entry(2, f"Moderate private/public ratio ({priv_pub_ratio})")
    if priv_pub_ratio < 1.0:
        return _score_entry(1, f"High private/public ratio ({priv_pub_ratio})")
    return _score_entry(0, f"Very high private/public ratio ({priv_pub_ratio})")


def _score_white_box(
    totals: dict[str, Any], classes: dict[str, Any], priv_pub_ratio: float
) -> dict[str, Any]:
    has_white_box = classes.get("white_box_candidate", 0) > 0
    has_internals = totals["internal_imports"] > 0 or totals["private_method_calls"] > 0
    if has_white_box and has_internals and priv_pub_ratio < 0.5:
        return _score_entry(
            3, "White-box tests present with controlled internal coupling"
        )
    if priv_pub_ratio < 1.0:
        return _score_entry(2, "Private/public ratio under control")
    if has_white_box:
        return _score_entry(1, "White-box tests present but high internal coupling")
    return _score_entry(0, "No white-box classification signal")


def _score_determinism(totals: dict[str, Any]) -> dict[str, Any]:
    if totals["hypothesis_given_calls"] > 0:
        return _score_entry(3, "Hypothesis property tests detected (seed discipline)")
    return _score_entry(2, "Default (static analysis cannot fully assess)")


def _score_assertion_quality(
    totals: dict[str, Any], ratios: dict[str, Any]
) -> dict[str, Any]:
    match_ratio = ratios["raises_with_match_ratio"]
    if (
        match_ratio == 1.0
        and totals["exact_eq_assert_count"] > 0
        and totals["raises_total"] > 0
    ):
        return _score_entry(
            3, "All raises use match and exact-equality asserts present"
        )
    if match_ratio >= 0.5:
        return _score_entry(2, f"Raises match ratio {match_ratio} >= 0.5")
    if totals["raises_total"] > 0:
        return _score_entry(1, f"Raises present but low match ratio ({match_ratio})")
    return _score_entry(0, "No pytest.raises calls detected")


def _score_pyramid_scope(
    totals: dict[str, Any], classes: dict[str, Any]
) -> dict[str, Any]:
    n_files = totals["files"]
    has_both = (
        classes.get("white_box_candidate", 0) > 0
        and classes.get("black_box_candidate", 0) > 0
    )
    if n_files >= 4 and has_both:
        return _score_entry(
            3, f"{n_files} files with both white-box and black-box candidates"
        )
    if n_files >= 3:
        return _score_entry(2, f"{n_files} files (layering signal)")
    if n_files >= 2:
        return _score_entry(1, f"{n_files} files (minimal layering)")
    return _score_entry(0, f"Only {n_files} file(s)")


def _score_coverage_mutation(cov_json_path: str) -> dict[str, Any]:
    if not cov_json_path:
        return _score_entry(1, "unknown (no coverage data provided)")
    cov_data = parse_coverage_json(cov_json_path)
    stmt_pct = cov_data.get("statement_pct", 0.0)
    branch_pct = cov_data.get("branch_pct", 0.0)
    if stmt_pct >= 85 and branch_pct >= 75:
        return _score_entry(
            3, f"Statement {stmt_pct:.1f}% >= 85% and branch {branch_pct:.1f}% >= 75%"
        )
    if stmt_pct >= 85:
        return _score_entry(
            2, f"Statement {stmt_pct:.1f}% >= 85% (branch {branch_pct:.1f}% < 75%)"
        )
    return _score_entry(1, f"Statement {stmt_pct:.1f}% < 85%")


def _score_non_functional(
    totals: dict[str, Any], markers: dict[str, Any]
) -> dict[str, Any]:
    n_files = totals["files"]
    benchmark_count = markers.get("benchmark", 0)
    if n_files < 2:
        return _score_entry(0, "Too few test files for non-functional signal")
    if benchmark_count > 0:
        return _score_entry(2, f"{benchmark_count} benchmark markers detected")
    return _score_entry(1, "No benchmark markers detected")


def score_rubric(
    summary: dict[str, Any],
    config: dict[str, Any],
    cov_json_path: str = "",
) -> dict[str, Any]:
    """Produce heuristic rubric scores (0-3) for each of the 8 quality dimensions.

    Returns a dict with one key per dimension (each mapping to
    ``{"score": int, "max": 3, "rationale": str}``) plus ``total`` and
    ``max_total`` summary keys.
    """
    totals = summary["totals"]
    ratios = summary["ratios"]
    classes = summary["classification_counts"]
    markers = summary.get("markers", {})

    scores: dict[str, dict[str, Any]] = {}

    scores["Contract Coverage"] = _score_contract_coverage(totals)
    priv_pub_ratio = ratios["private_to_public_call_ratio"]
    scores["Behavior-First Focus"] = _score_behavior_first(totals, ratios)
    scores["White-Box Justification"] = _score_white_box(
        totals, classes, priv_pub_ratio
    )
    scores["Determinism/Isolation"] = _score_determinism(totals)
    scores["Assertion Quality"] = _score_assertion_quality(totals, ratios)
    scores["Pyramid/Scope"] = _score_pyramid_scope(totals, classes)
    scores["Coverage/Mutation"] = _score_coverage_mutation(cov_json_path)
    scores["Non-Functional"] = _score_non_functional(totals, markers)

    total = sum(d["score"] for d in scores.values())
    return {
        **scores,
        "total": total,
        "max_total": 24,
    }


def _count_delta(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    delta: dict[str, Any] = {}
    all_keys = sorted(set(current) | set(baseline))
    for key in all_keys:
        cur_val = current.get(key, 0)
        base_val = baseline.get(key, 0)
        if cur_val != base_val:
            delta[key] = {
                "before": base_val,
                "after": cur_val,
                "change": cur_val - base_val,
            }
    return delta


def _totals_delta(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    cur_totals = current.get("summary", {}).get("totals", {})
    base_totals = baseline.get("summary", {}).get("totals", {})
    return _count_delta(cur_totals, base_totals)


def _ratios_delta(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    cur_ratios = current.get("summary", {}).get("ratios", {})
    base_ratios = baseline.get("summary", {}).get("ratios", {})
    delta: dict[str, Any] = {}
    for key in cur_ratios:
        cur_val = cur_ratios.get(key, 0)
        base_val = base_ratios.get(key, 0)
        if cur_val != base_val:
            delta[key] = {"before": base_val, "after": cur_val}
    return delta


def _classification_delta(
    current: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, Any]:
    cur_classes = current.get("summary", {}).get("classification_counts", {})
    base_classes = baseline.get("summary", {}).get("classification_counts", {})
    return _count_delta(cur_classes, base_classes)


def _rubric_delta(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    cur_rubric = current.get("rubric_scores", {})
    base_rubric = baseline.get("rubric_scores", {})
    delta: dict[str, Any] = {}
    for key in cur_rubric:
        if key in ("total", "max_total"):
            cur_v = cur_rubric.get(key)
            base_v = base_rubric.get(key)
            if cur_v != base_v:
                delta[key] = {
                    "before": base_v if base_v is not None else "N/A",
                    "after": cur_v,
                }
            continue
        cur_score = cur_rubric.get(key, {}).get("score")
        base_score = base_rubric.get(key, {}).get("score")
        if cur_score is not None and base_score is not None and cur_score != base_score:
            delta[key] = {
                "before": base_score,
                "after": cur_score,
                "change": cur_score - base_score,
            }
    return delta


def compute_delta(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Compare current report against a baseline and produce delta information."""
    delta: dict[str, Any] = {}
    delta["totals"] = _totals_delta(current, baseline)
    delta["ratios"] = _ratios_delta(current, baseline)
    delta["classification_counts"] = _classification_delta(current, baseline)
    delta["rubric_scores"] = _rubric_delta(current, baseline)

    return delta


def _render_summary_sections(report: dict[str, Any]) -> list[str]:
    config = report["config"]
    totals = report["summary"]["totals"]
    ratios = report["summary"]["ratios"]
    classes = report["summary"]["classification_counts"]
    return [
        "# Test Quality Inventory",
        "",
        "## Config",
        f"- Root: {report['root']}",
        f"- Test dirs: {', '.join(config['test_dirs'])}",
        f"- Test globs: {', '.join(config['test_globs'])}",
        f"- Internal import patterns: {len(config['internal_import_patterns'])}",
        f"- Public call hints: {len(config['public_hints'])}",
        f"- Auto-inferred public hints: {config['auto_inferred_public_hints']}",
        f"- Exact-eq assert pattern: `{config['exact_eq_pattern']}`",
        "",
        "## Totals",
        f"- Files: {totals['files']}",
        f"- Test functions: {totals['test_functions']}",
        f"- Private method calls: {totals['private_method_calls']}",
        f"- Public call hints: {totals['public_call_hints']}",
        f"- Internal implementation imports: {totals['internal_imports']}",
        f"- `pytest.raises` calls: {totals['raises_total']}",
        f"- `pytest.raises(..., match=...)`: {totals['raises_with_match']}",
        f"- Broad exception tuples: {totals['raises_broad_tuple']}",
        f"- `@given` calls (Hypothesis signal): {totals['hypothesis_given_calls']}",
        f"- `expected = (...)` literals: {totals['expected_literal_count']}",
        f"- Exact expected-equality asserts: {totals['exact_eq_assert_count']}",
        "",
        "## Ratios",
        "- Private/Public call ratio: "
        + (
            str(ratios["private_to_public_call_ratio"])
            if config["public_hints"]
            else "N/A (no public hints)"
        ),
        f"- Raises with match ratio: {ratios['raises_with_match_ratio']}",
        f"- Broad tuple raises ratio: {ratios['broad_tuple_raises_ratio']}",
        "",
        "## Classification Counts",
        f"- White-box candidates: {classes.get('white_box_candidate', 0)}",
        f"- Black-box candidates: {classes.get('black_box_candidate', 0)}",
        f"- Change-indicator candidates: "
        f"{classes.get('change_indicator_candidate', 0)}",
        "",
        "## Marker Breakdown",
    ]


def _render_marker_breakdown(markers: dict[str, int]) -> list[str]:
    lines: list[str] = []
    custom = {k: v for k, v in markers.items() if k not in PYTEST_BUILTIN_MARKERS}
    builtin = {k: v for k, v in markers.items() if k in PYTEST_BUILTIN_MARKERS}
    if custom:
        for marker, count in sorted(custom.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- `{marker}`: {count}")
    else:
        lines.append("- No custom markers detected.")
    if builtin:
        summary = ", ".join(
            f"`{m}` ({c})"
            for m, c in sorted(builtin.items(), key=lambda kv: (-kv[1], kv[0]))
        )
        lines.append(f"- Structural (filtered from signal): {summary}")
    return lines


def _render_flags(report: dict[str, Any]) -> list[str]:
    config = report["config"]
    totals = report["summary"]["totals"]
    ratios = report["summary"]["ratios"]
    classes = report["summary"]["classification_counts"]
    lines = [
        "",
        "## Flags",
    ]
    flags: list[str] = []
    if not config["public_hints"]:
        flags.append(
            "- Public call hints list is empty; black-box classification "
            "is disabled for this run."
        )
    if config["public_hints"] and ratios["private_to_public_call_ratio"] > 1.0:
        flags.append("- High private API coupling signal (private/public ratio > 1).")
    if totals["raises_total"] > 0 and ratios["raises_with_match_ratio"] < 0.5:
        flags.append(
            "- Low exception precision signal "
            "(fewer than half of raises use message matching)."
        )
    if totals["raises_total"] > 0 and ratios["broad_tuple_raises_ratio"] > 0.25:
        flags.append("- Broad exception tuple usage may hide contract precision.")
    if classes.get("change_indicator_candidate", 0) > 0:
        flags.append("- Change-indicator tests detected; verify intentional labeling.")
    if flags:
        lines.extend(flags)
    else:
        lines.append("- No high-level heuristic flags triggered by this static pass.")
    return lines


def _render_rubric_scores(rubric: dict[str, Any] | None) -> list[str]:
    if not rubric:
        return []
    lines = [
        "",
        "## Rubric Scores",
        "",
        "| Dimension | Score | Max | Rationale |",
        "|-----------|-------|-----|-----------|",
    ]
    dimension_order = [
        "Contract Coverage",
        "Behavior-First Focus",
        "White-Box Justification",
        "Determinism/Isolation",
        "Assertion Quality",
        "Pyramid/Scope",
        "Coverage/Mutation",
        "Non-Functional",
    ]
    for dim in dimension_order:
        entry = rubric.get(dim, {})
        if isinstance(entry, dict) and "score" in entry:
            lines.append(
                f"| {dim} | {entry['score']} | {entry['max']} | "
                f"{entry['rationale']} |"
            )
    lines.append(
        f"| **Total** | **{rubric.get('total', '?')}** | "
        f"**{rubric.get('max_total', 24)}** | |"
    )
    return lines


def _render_count_delta_section(title: str, values: dict[str, Any]) -> list[str]:
    if not values:
        return []
    lines = [title]
    for key, info in sorted(values.items()):
        change = info["change"]
        sign = "+" if change > 0 else ""
        lines.append(
            f"- {key}: {info['before']} \u2192 {info['after']} ({sign}{change})"
        )
    lines.append("")
    return lines


def _render_ratio_delta_section(values: dict[str, Any]) -> list[str]:
    if not values:
        return []
    lines = ["### Ratios"]
    for key, info in sorted(values.items()):
        lines.append(f"- {key}: {info['before']} \u2192 {info['after']}")
    lines.append("")
    return lines


def _render_rubric_delta_section(values: dict[str, Any]) -> list[str]:
    if not values:
        return []
    lines = ["### Rubric Score Changes"]
    for key, info in sorted(values.items()):
        if key in ("total", "max_total"):
            lines.append(f"- {key}: {info['before']} \u2192 {info['after']}")
        else:
            change = info.get("change", "")
            sign = "+" if isinstance(change, int) and change > 0 else ""
            lines.append(
                f"- {key}: {info['before']} \u2192 "
                f"{info['after']} ({sign}{change})"
            )
    lines.append("")
    return lines


def _render_delta_report(delta: dict[str, Any] | None) -> list[str]:
    if not delta:
        return []
    lines = [
        "",
        "## Delta Report",
        "",
    ]
    lines.extend(_render_count_delta_section("### Totals", delta.get("totals", {})))
    lines.extend(_render_ratio_delta_section(delta.get("ratios", {})))
    lines.extend(
        _render_count_delta_section(
            "### Classifications", delta.get("classification_counts", {})
        )
    )
    lines.extend(_render_rubric_delta_section(delta.get("rubric_scores", {})))
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    markers = report["summary"]["markers"]
    lines = _render_summary_sections(report)
    lines.extend(_render_marker_breakdown(markers))
    lines.extend(_render_flags(report))
    lines.extend(_render_rubric_scores(report.get("rubric_scores")))
    lines.extend(_render_delta_report(report.get("delta")))

    return "\n".join(lines) + "\n"


def _add_input_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root", default=".", help="Repository root path (default: current directory)."
    )
    parser.add_argument(
        "--tests-dir",
        action="append",
        default=None,
        help="Test directory relative to root. Repeat or comma-separate for multiple.",
    )
    parser.add_argument(
        "--test-glob",
        action="append",
        default=None,
        help="Glob pattern under each test dir. Repeat or comma-separate for multiple.",
    )


def _add_detection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--internal-import-pattern",
        action="append",
        default=[],
        help="Regex identifying implementation-coupled imports. "
        "Repeat or comma-separate.",
    )
    parser.add_argument(
        "--public-hint",
        action="append",
        default=[],
        help="Public API call hint substring (e.g., compute(). "
        "Repeat or comma-separate.",
    )
    parser.add_argument(
        "--no-auto-public-hints",
        action="store_true",
        help="Disable automatic public hint inference "
        "from package __init__.py exports.",
    )
    parser.add_argument(
        "--exact-eq-pattern",
        default="",
        help=(
            "Override the regex used to detect exact-equality "
            "change-indicator asserts. "
            "Defaults to the built-in EXACT_EQ_ASSERT_RE pattern."
        ),
    )


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json-out", default="", help="Optional JSON report output path."
    )
    parser.add_argument(
        "--md-out", default="", help="Optional markdown summary output path."
    )
    parser.add_argument(
        "--cov-json",
        default="",
        help="Path to a coverage.json file (from `coverage json`). "
        "Used to score the Coverage/Mutation rubric dimension.",
    )
    parser.add_argument(
        "--baseline-json",
        default="",
        help="Path to a previous JSON report. "
        "When provided, a delta report is included showing changes.",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Static test quality inventory.")
    _add_input_args(parser)
    _add_detection_args(parser)
    _add_output_args(parser)
    return parser.parse_args()


def _compile_internal_patterns(
    patterns: list[str],
) -> list[re.Pattern[str]] | None:
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            print(
                f"error: invalid --internal-import-pattern regex {pattern!r}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            return None
    return compiled


def _resolve_public_hints(
    root: Path, args: argparse.Namespace
) -> tuple[list[str], bool]:
    public_hints = _split_csv_values(args.public_hint)
    if args.no_auto_public_hints:
        return public_hints, False
    inferred_hints = infer_public_hints(root)
    if not inferred_hints:
        return public_hints, False
    return sorted(set(public_hints + inferred_hints)), True


def _compile_exact_eq_pattern(pattern: str) -> re.Pattern[str] | None:
    try:
        return re.compile(pattern, re.MULTILINE)
    except re.error as exc:
        print(
            f"error: invalid --exact-eq-pattern regex {pattern!r}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return None


@dataclass(frozen=True)
class _ReportBuildInput:
    root: Path
    test_dirs: list[str]
    test_globs: list[str]
    internal_patterns: list[str]
    internal_import_res: list[re.Pattern[str]]
    public_hints: list[str]
    auto_inferred: bool
    exact_eq_pattern: str
    exact_eq_re: re.Pattern[str]


def _build_report(inputs: _ReportBuildInput) -> dict[str, Any]:
    files = collect_test_files(inputs.root, inputs.test_dirs, inputs.test_globs)
    metrics = [
        analyze_file(
            path,
            inputs.internal_import_res,
            inputs.public_hints,
            inputs.exact_eq_re,
        )
        for path in files
    ]
    return {
        "root": str(inputs.root),
        "config": {
            "test_dirs": inputs.test_dirs,
            "test_globs": inputs.test_globs,
            "internal_import_patterns": inputs.internal_patterns,
            "public_hints": inputs.public_hints,
            "auto_inferred_public_hints": inputs.auto_inferred,
            "exact_eq_pattern": inputs.exact_eq_pattern,
        },
        "summary": summarize(metrics),
        "files": [m.to_dict() for m in metrics],
    }


def _add_rubric_scores(report: dict[str, Any], cov_json_path: str) -> None:
    report["rubric_scores"] = score_rubric(
        report["summary"],
        report["config"],
        cov_json_path=cov_json_path,
    )


def _add_delta_report(report: dict[str, Any], baseline_json: str) -> None:
    if not baseline_json:
        return
    try:
        baseline_data = json.loads(Path(baseline_json).read_text(encoding="utf-8"))
        report["delta"] = compute_delta(report, baseline_data)
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        print(
            f"warning: could not load baseline JSON {baseline_json}: {exc}",
            file=sys.stderr,
            flush=True,
        )


def _write_report_outputs(report: dict[str, Any], args: argparse.Namespace) -> None:
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    md = render_markdown(report)
    if args.md_out:
        out = Path(args.md_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
    else:
        print(md)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    test_dirs = _split_csv_values(args.tests_dir) or ["tests"]
    test_globs = _split_csv_values(args.test_glob) or list(DEFAULT_TEST_GLOBS)
    internal_patterns = _split_csv_values(args.internal_import_pattern)
    if not internal_patterns:
        internal_patterns = list(DEFAULT_INTERNAL_IMPORT_PATTERNS)
    internal_import_res = _compile_internal_patterns(internal_patterns)
    if internal_import_res is None:
        return 1
    public_hints, auto_inferred = _resolve_public_hints(root, args)
    exact_eq_pattern = args.exact_eq_pattern or EXACT_EQ_ASSERT_RE.pattern
    exact_eq_re = _compile_exact_eq_pattern(exact_eq_pattern)
    if exact_eq_re is None:
        return 1
    report = _build_report(
        _ReportBuildInput(
            root=root,
            test_dirs=test_dirs,
            test_globs=test_globs,
            internal_patterns=internal_patterns,
            internal_import_res=internal_import_res,
            public_hints=public_hints,
            auto_inferred=auto_inferred,
            exact_eq_pattern=exact_eq_pattern,
            exact_eq_re=exact_eq_re,
        )
    )
    _add_rubric_scores(report, args.cov_json)
    _add_delta_report(report, args.baseline_json)
    _write_report_outputs(report, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
