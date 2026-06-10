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
PYTEST_BUILTIN_MARKERS = frozenset({
    "parametrize", "skip", "skipif", "xfail", "usefixtures", "filterwarnings", "timeout",
})
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
    init_files = sorted(root.glob("src/**/__init__.py")) + sorted(root.glob("*/__init__.py"))
    for init_file in init_files:
        if ".venv" in init_file.parts:
            continue
        try:
            tree = ast.parse(init_file.read_text(encoding="utf-8"), filename=str(init_file))
        except Exception:
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
    elif isinstance(node, ast.Attribute):
        if (
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
        if not any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets):
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
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                count += 1
    return count


def _count_given_usage(tree: ast.AST) -> int:
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "given":
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
            if node.args and isinstance(node.args[0], ast.Tuple):
                if len(node.args[0].elts) > 1:
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
        print(f"warning: skipping unparseable file {path}: {exc}", file=sys.stderr, flush=True)
        return FileMetrics(path=str(path))
    markers = Counter(MARKER_RE.findall(text))
    markers.update(_collect_pytestmark_names(tree))
    raises_total, raises_with_match, raises_broad_tuple = _count_pytest_raises(tree)
    public_call_hints = sum(text.count(hint) for hint in public_hints)
    internal_imports = sum(len(pattern.findall(text)) for pattern in internal_import_res)
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


def collect_test_files(root: Path, test_dirs: list[str], test_globs: list[str]) -> list[Path]:
    files: set[Path] = set()
    for test_dir in test_dirs:
        base = root / test_dir
        if not base.exists():
            print(f"warning: test dir not found, skipping: {base}", file=sys.stderr, flush=True)
            continue
        for glob_pattern in test_globs:
            for path in base.rglob(glob_pattern):
                if path.is_file():
                    files.add(path)
    return sorted(files)


def summarize(file_metrics: list[FileMetrics]) -> dict[str, Any]:
    marker_totals: Counter[str] = Counter()
    classifications = Counter()

    for m in file_metrics:
        marker_totals.update(m.markers or {})
        c = classify_file(m)
        for key, value in c.items():
            if value:
                classifications[key] += 1

    total_private = sum(m.private_method_calls for m in file_metrics)
    total_public = sum(m.public_call_hints for m in file_metrics)
    total_raises = sum(m.raises_total for m in file_metrics)
    raises_match = sum(m.raises_with_match for m in file_metrics)
    broad_tuple_raises = sum(m.raises_broad_tuple for m in file_metrics)

    return {
        "totals": {
            "files": len(file_metrics),
            "test_functions": sum(m.test_functions for m in file_metrics),
            "private_method_calls": total_private,
            "public_call_hints": total_public,
            "internal_imports": sum(m.internal_imports for m in file_metrics),
            "raises_total": total_raises,
            "raises_with_match": raises_match,
            "raises_broad_tuple": broad_tuple_raises,
            "hypothesis_given_calls": sum(m.given_count for m in file_metrics),
            "expected_literal_count": sum(m.expected_literal_count for m in file_metrics),
            "exact_eq_assert_count": sum(m.exact_eq_assert_count for m in file_metrics),
        },
        "ratios": {
            "private_to_public_call_ratio": round(total_private / max(total_public, 1), 3),
            "raises_with_match_ratio": round(raises_match / max(total_raises, 1), 3),
            "broad_tuple_raises_ratio": round(broad_tuple_raises / max(total_raises, 1), 3),
        },
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
                result["branch_pct"] = round(100.0 * totals["covered_branches"] / num, 2)
        return result
    except (json.JSONDecodeError, FileNotFoundError, KeyError, TypeError) as exc:
        print(f"warning: could not parse coverage JSON {cov_json_path}: {exc}", file=sys.stderr, flush=True)
        return {}


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

    # 1. Contract Coverage
    if totals["public_call_hints"] > 0 and totals["raises_with_match"] > 0:
        cc_score, cc_rationale = 3, "Public call hints and precise raises detected"
    elif totals["public_call_hints"] > 0:
        cc_score, cc_rationale = 2, "Public call hints detected but no precise raises"
    elif totals["test_functions"] > 0:
        cc_score, cc_rationale = 1, "Tests exist but no public call hints"
    else:
        cc_score, cc_rationale = 0, "No test functions detected"
    scores["Contract Coverage"] = {"score": cc_score, "max": 3, "rationale": cc_rationale}

    # 2. Behavior-First Focus
    priv_pub_ratio = ratios["private_to_public_call_ratio"]
    if priv_pub_ratio < 0.3 and totals["public_call_hints"] > 0:
        bf_score, bf_rationale = 3, f"Low private/public ratio ({priv_pub_ratio}) with public hints"
    elif priv_pub_ratio < 0.5:
        bf_score, bf_rationale = 2, f"Moderate private/public ratio ({priv_pub_ratio})"
    elif priv_pub_ratio < 1.0:
        bf_score, bf_rationale = 1, f"High private/public ratio ({priv_pub_ratio})"
    else:
        bf_score, bf_rationale = 0, f"Very high private/public ratio ({priv_pub_ratio})"
    scores["Behavior-First Focus"] = {"score": bf_score, "max": 3, "rationale": bf_rationale}

    # 3. White-Box Justification
    has_white_box = classes.get("white_box_candidate", 0) > 0
    has_internals = totals["internal_imports"] > 0 or totals["private_method_calls"] > 0
    if has_white_box and has_internals and priv_pub_ratio < 0.5:
        wb_score, wb_rationale = 3, "White-box tests present with controlled internal coupling"
    elif priv_pub_ratio < 1.0:
        wb_score, wb_rationale = 2, "Private/public ratio under control"
    elif has_white_box:
        wb_score, wb_rationale = 1, "White-box tests present but high internal coupling"
    else:
        wb_score, wb_rationale = 0, "No white-box classification signal"
    scores["White-Box Justification"] = {"score": wb_score, "max": 3, "rationale": wb_rationale}

    # 4. Determinism/Isolation
    if totals["hypothesis_given_calls"] > 0:
        di_score, di_rationale = 3, "Hypothesis property tests detected (seed discipline)"
    else:
        di_score, di_rationale = 2, "Default (static analysis cannot fully assess)"
    scores["Determinism/Isolation"] = {"score": di_score, "max": 3, "rationale": di_rationale}

    # 5. Assertion Quality
    match_ratio = ratios["raises_with_match_ratio"]
    if match_ratio == 1.0 and totals["exact_eq_assert_count"] > 0 and totals["raises_total"] > 0:
        aq_score, aq_rationale = 3, "All raises use match and exact-equality asserts present"
    elif match_ratio >= 0.5:
        aq_score, aq_rationale = 2, f"Raises match ratio {match_ratio} >= 0.5"
    elif totals["raises_total"] > 0:
        aq_score, aq_rationale = 1, f"Raises present but low match ratio ({match_ratio})"
    else:
        aq_score, aq_rationale = 0, "No pytest.raises calls detected"
    scores["Assertion Quality"] = {"score": aq_score, "max": 3, "rationale": aq_rationale}

    # 6. Pyramid/Scope
    n_files = totals["files"]
    has_both = classes.get("white_box_candidate", 0) > 0 and classes.get("black_box_candidate", 0) > 0
    if n_files >= 4 and has_both:
        ps_score, ps_rationale = 3, f"{n_files} files with both white-box and black-box candidates"
    elif n_files >= 3:
        ps_score, ps_rationale = 2, f"{n_files} files (layering signal)"
    elif n_files >= 2:
        ps_score, ps_rationale = 1, f"{n_files} files (minimal layering)"
    else:
        ps_score, ps_rationale = 0, f"Only {n_files} file(s)"
    scores["Pyramid/Scope"] = {"score": ps_score, "max": 3, "rationale": ps_rationale}

    # 7. Coverage/Mutation
    cm_score = 1
    cm_rationale = "unknown (no coverage data provided)"
    if cov_json_path:
        cov_data = parse_coverage_json(cov_json_path)
        stmt_pct = cov_data.get("statement_pct", 0.0)
        branch_pct = cov_data.get("branch_pct", 0.0)
        if stmt_pct >= 85 and branch_pct >= 75:
            cm_score = 3
            cm_rationale = f"Statement {stmt_pct:.1f}% >= 85% and branch {branch_pct:.1f}% >= 75%"
        elif stmt_pct >= 85:
            cm_score = 2
            cm_rationale = f"Statement {stmt_pct:.1f}% >= 85% (branch {branch_pct:.1f}% < 75%)"
        else:
            cm_rationale = f"Statement {stmt_pct:.1f}% < 85%"
    scores["Coverage/Mutation"] = {"score": cm_score, "max": 3, "rationale": cm_rationale}

    # 8. Non-Functional
    benchmark_count = markers.get("benchmark", 0)
    if n_files < 2:
        nf_score, nf_rationale = 0, "Too few test files for non-functional signal"
    elif benchmark_count > 0:
        nf_score, nf_rationale = 2, f"{benchmark_count} benchmark markers detected"
    else:
        nf_score, nf_rationale = 1, "No benchmark markers detected"
    scores["Non-Functional"] = {"score": nf_score, "max": 3, "rationale": nf_rationale}

    total = sum(d["score"] for d in scores.values())
    return {
        **scores,
        "total": total,
        "max_total": 24,
    }


def compute_delta(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Compare current report against a baseline and produce delta information."""
    delta: dict[str, Any] = {}

    # Compare totals
    cur_totals = current.get("summary", {}).get("totals", {})
    base_totals = baseline.get("summary", {}).get("totals", {})
    totals_delta: dict[str, Any] = {}
    for key in cur_totals:
        cur_val = cur_totals.get(key, 0)
        base_val = base_totals.get(key, 0)
        if cur_val != base_val:
            totals_delta[key] = {"before": base_val, "after": cur_val, "change": cur_val - base_val}
    delta["totals"] = totals_delta

    # Compare ratios
    cur_ratios = current.get("summary", {}).get("ratios", {})
    base_ratios = baseline.get("summary", {}).get("ratios", {})
    ratios_delta: dict[str, Any] = {}
    for key in cur_ratios:
        cur_val = cur_ratios.get(key, 0)
        base_val = base_ratios.get(key, 0)
        if cur_val != base_val:
            ratios_delta[key] = {"before": base_val, "after": cur_val}
    delta["ratios"] = ratios_delta

    # Compare classification counts
    cur_classes = current.get("summary", {}).get("classification_counts", {})
    base_classes = baseline.get("summary", {}).get("classification_counts", {})
    class_delta: dict[str, Any] = {}
    all_keys = sorted(set(cur_classes) | set(base_classes))
    for key in all_keys:
        cur_val = cur_classes.get(key, 0)
        base_val = base_classes.get(key, 0)
        if cur_val != base_val:
            class_delta[key] = {"before": base_val, "after": cur_val, "change": cur_val - base_val}
    delta["classification_counts"] = class_delta

    # Compare rubric scores if both have them
    cur_rubric = current.get("rubric_scores", {})
    base_rubric = baseline.get("rubric_scores", {})
    rubric_delta: dict[str, Any] = {}
    for key in cur_rubric:
        if key in ("total", "max_total"):
            cur_v = cur_rubric.get(key)
            base_v = base_rubric.get(key)
            if cur_v != base_v:
                rubric_delta[key] = {"before": base_v if base_v is not None else "N/A", "after": cur_v}
            continue
        cur_score = cur_rubric.get(key, {}).get("score")
        base_score = base_rubric.get(key, {}).get("score")
        if cur_score is not None and base_score is not None and cur_score != base_score:
            rubric_delta[key] = {"before": base_score, "after": cur_score, "change": cur_score - base_score}
    delta["rubric_scores"] = rubric_delta

    return delta


def render_markdown(report: dict[str, Any]) -> str:
    config = report["config"]
    totals = report["summary"]["totals"]
    ratios = report["summary"]["ratios"]
    classes = report["summary"]["classification_counts"]
    markers = report["summary"]["markers"]

    lines = [
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
        + (str(ratios["private_to_public_call_ratio"]) if config["public_hints"] else "N/A (no public hints)"),
        f"- Raises with match ratio: {ratios['raises_with_match_ratio']}",
        f"- Broad tuple raises ratio: {ratios['broad_tuple_raises_ratio']}",
        "",
        "## Classification Counts",
        f"- White-box candidates: {classes.get('white_box_candidate', 0)}",
        f"- Black-box candidates: {classes.get('black_box_candidate', 0)}",
        f"- Change-indicator candidates: {classes.get('change_indicator_candidate', 0)}",
        "",
        "## Marker Breakdown",
    ]

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

    lines.extend([
        "",
        "## Flags",
    ])

    flags: list[str] = []
    if not config["public_hints"]:
        flags.append("- Public call hints list is empty; black-box classification is disabled for this run.")
    if config["public_hints"] and ratios["private_to_public_call_ratio"] > 1.0:
        flags.append("- High private API coupling signal (private/public ratio > 1).")
    if totals["raises_total"] > 0 and ratios["raises_with_match_ratio"] < 0.5:
        flags.append("- Low exception precision signal (fewer than half of raises use message matching).")
    if totals["raises_total"] > 0 and ratios["broad_tuple_raises_ratio"] > 0.25:
        flags.append("- Broad exception tuple usage may hide contract precision.")
    if classes.get("change_indicator_candidate", 0) > 0:
        flags.append("- Change-indicator tests detected; verify intentional labeling.")
    if flags:
        lines.extend(flags)
    else:
        lines.append("- No high-level heuristic flags triggered by this static pass.")

    # Rubric Scores section
    rubric = report.get("rubric_scores")
    if rubric:
        lines.extend([
            "",
            "## Rubric Scores",
            "",
            "| Dimension | Score | Max | Rationale |",
            "|-----------|-------|-----|-----------|",
        ])
        dimension_order = [
            "Contract Coverage", "Behavior-First Focus", "White-Box Justification",
            "Determinism/Isolation", "Assertion Quality", "Pyramid/Scope",
            "Coverage/Mutation", "Non-Functional",
        ]
        for dim in dimension_order:
            entry = rubric.get(dim, {})
            if isinstance(entry, dict) and "score" in entry:
                lines.append(
                    f"| {dim} | {entry['score']} | {entry['max']} | {entry['rationale']} |"
                )
        lines.append(f"| **Total** | **{rubric.get('total', '?')}** | **{rubric.get('max_total', 24)}** | |")

    # Delta Report section
    delta = report.get("delta")
    if delta:
        lines.extend([
            "",
            "## Delta Report",
            "",
        ])
        # Totals changes
        totals_d = delta.get("totals", {})
        if totals_d:
            lines.append("### Totals")
            for key, info in sorted(totals_d.items()):
                change = info["change"]
                sign = "+" if change > 0 else ""
                lines.append(f"- {key}: {info['before']} \u2192 {info['after']} ({sign}{change})")
            lines.append("")
        # Ratio changes
        ratios_d = delta.get("ratios", {})
        if ratios_d:
            lines.append("### Ratios")
            for key, info in sorted(ratios_d.items()):
                lines.append(f"- {key}: {info['before']} \u2192 {info['after']}")
            lines.append("")
        # Classification changes
        class_d = delta.get("classification_counts", {})
        if class_d:
            lines.append("### Classifications")
            for key, info in sorted(class_d.items()):
                change = info["change"]
                sign = "+" if change > 0 else ""
                lines.append(f"- {key}: {info['before']} \u2192 {info['after']} ({sign}{change})")
            lines.append("")
        # Rubric score changes
        rubric_d = delta.get("rubric_scores", {})
        if rubric_d:
            lines.append("### Rubric Score Changes")
            for key, info in sorted(rubric_d.items()):
                if key in ("total", "max_total"):
                    lines.append(f"- {key}: {info['before']} \u2192 {info['after']}")
                else:
                    change = info.get("change", "")
                    sign = "+" if isinstance(change, int) and change > 0 else ""
                    lines.append(f"- {key}: {info['before']} \u2192 {info['after']} ({sign}{change})")
            lines.append("")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Static test quality inventory.")
    parser.add_argument("--root", default=".", help="Repository root path (default: current directory).")
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
    parser.add_argument(
        "--internal-import-pattern",
        action="append",
        default=[],
        help="Regex identifying implementation-coupled imports. Repeat or comma-separate.",
    )
    parser.add_argument(
        "--public-hint",
        action="append",
        default=[],
        help="Public API call hint substring (e.g., compute(). Repeat or comma-separate.",
    )
    parser.add_argument(
        "--no-auto-public-hints",
        action="store_true",
        help="Disable automatic public hint inference from package __init__.py exports.",
    )
    parser.add_argument(
        "--exact-eq-pattern",
        default="",
        help=(
            "Override the regex used to detect exact-equality change-indicator asserts. "
            "Defaults to the built-in EXACT_EQ_ASSERT_RE pattern."
        ),
    )
    parser.add_argument("--json-out", default="", help="Optional JSON report output path.")
    parser.add_argument("--md-out", default="", help="Optional markdown summary output path.")
    parser.add_argument(
        "--cov-json",
        default="",
        help="Path to a coverage.json file (from `coverage json`). Used to score the Coverage/Mutation rubric dimension.",
    )
    parser.add_argument(
        "--baseline-json",
        default="",
        help="Path to a previous JSON report. When provided, a delta report is included showing changes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()

    test_dirs = _split_csv_values(args.tests_dir) or ["tests"]
    test_globs = _split_csv_values(args.test_glob) or list(DEFAULT_TEST_GLOBS)

    internal_patterns = _split_csv_values(args.internal_import_pattern)
    if not internal_patterns:
        internal_patterns = list(DEFAULT_INTERNAL_IMPORT_PATTERNS)
    internal_import_res: list[re.Pattern[str]] = []
    for pattern in internal_patterns:
        try:
            internal_import_res.append(re.compile(pattern))
        except re.error as exc:
            print(f"error: invalid --internal-import-pattern regex {pattern!r}: {exc}", file=sys.stderr, flush=True)
            return 1

    public_hints = _split_csv_values(args.public_hint)
    auto_inferred = False
    if not args.no_auto_public_hints:
        inferred_hints = infer_public_hints(root)
        if inferred_hints:
            auto_inferred = True
            public_hints = sorted(set(public_hints + inferred_hints))

    exact_eq_pattern = args.exact_eq_pattern or EXACT_EQ_ASSERT_RE.pattern
    try:
        exact_eq_re = re.compile(exact_eq_pattern, re.MULTILINE)
    except re.error as exc:
        print(f"error: invalid --exact-eq-pattern regex {exact_eq_pattern!r}: {exc}", file=sys.stderr, flush=True)
        return 1

    files = collect_test_files(root, test_dirs, test_globs)
    metrics = [analyze_file(path, internal_import_res, public_hints, exact_eq_re) for path in files]
    report = {
        "root": str(root),
        "config": {
            "test_dirs": test_dirs,
            "test_globs": test_globs,
            "internal_import_patterns": internal_patterns,
            "public_hints": public_hints,
            "auto_inferred_public_hints": auto_inferred,
            "exact_eq_pattern": exact_eq_pattern,
        },
        "summary": summarize(metrics),
        "files": [m.to_dict() for m in metrics],
    }

    # Rubric scoring
    report["rubric_scores"] = score_rubric(
        report["summary"],
        report["config"],
        cov_json_path=args.cov_json,
    )

    # Delta reporting
    if args.baseline_json:
        try:
            baseline_data = json.loads(
                Path(args.baseline_json).read_text(encoding="utf-8")
            )
            report["delta"] = compute_delta(report, baseline_data)
        except (json.JSONDecodeError, FileNotFoundError) as exc:
            print(
                f"warning: could not load baseline JSON {args.baseline_json}: {exc}",
                file=sys.stderr,
                flush=True,
            )

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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
