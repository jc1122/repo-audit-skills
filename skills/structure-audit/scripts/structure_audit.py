#!/usr/bin/env python3
"""structure-audit leaf: ast import graph + Tarjan SCC → RESTRUCTURE findings."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402

LEAF = "structure"

DEFAULT_THRESHOLDS = {
    "max_fan_out": 20,
    "max_fan_in": 20,
    "layers": [],
}


class ToolError(RuntimeError):
    pass


def _iter_python_files(root: Path, source_prefixes: list[str]) -> list[Path]:
    files = sorted(p for p in root.rglob("*.py") if p.is_file())
    if not source_prefixes:
        return files
    return [p for p in files if any(p.relative_to(root).as_posix().startswith(pre) for pre in source_prefixes)]


def _module_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_base(node: ast.ImportFrom, current_module: str, is_pkg: bool) -> str:
    if node.level == 0:
        return node.module or ""
    package = current_module if is_pkg else ".".join(current_module.split(".")[:-1])
    pkg_parts = package.split(".") if package else []
    drop = node.level - 1
    if drop:
        pkg_parts = pkg_parts[: len(pkg_parts) - drop] if drop <= len(pkg_parts) else []
    base = ".".join(pkg_parts)
    if node.module:
        base = f"{base}.{node.module}" if base else node.module
    return base


def _imported_names(path: Path, current_module: str, is_pkg: bool) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_base(node, current_module, is_pkg)
            for alias in node.names:
                if alias.name == "*":
                    if base:
                        names.append(base)
                else:
                    names.append(f"{base}.{alias.name}" if base else alias.name)
    return names


def _resolve_to_internal(name: str, module_set: set[str]) -> str | None:
    parts = name.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in module_set:
            return cand
    return None


def build_graph(root: Path, files: list[Path]):
    module_file: dict[str, str] = {}
    is_pkg: dict[str, bool] = {}
    for p in files:
        mod = _module_name(p, root)
        if mod:
            module_file[mod] = p.relative_to(root).as_posix()
            is_pkg[mod] = p.name == "__init__.py"
    module_set = set(module_file)
    edges: dict[str, set[str]] = {m: set() for m in module_set}
    for p in files:
        src = _module_name(p, root)
        if not src:
            continue
        for target in _imported_names(p, src, is_pkg.get(src, False)):
            dst = _resolve_to_internal(target, module_set)
            if dst and dst != src:
                edges[src].add(dst)
    return module_file, {m: sorted(s) for m, s in edges.items()}


def _strongly_connected_components(nodes, edges):
    index_counter = [0]
    stack: list[str] = []
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    result: list[list[str]] = []
    for root_node in nodes:
        if root_node in index:
            continue
        work = [(root_node, 0)]
        while work:
            node, pi = work[-1]
            if pi == 0:
                index[node] = index_counter[0]
                lowlink[node] = index_counter[0]
                index_counter[0] += 1
                stack.append(node)
                on_stack[node] = True
            recurse = False
            succs = edges.get(node, [])
            for i in range(pi, len(succs)):
                w = succs[i]
                if w not in index:
                    work[-1] = (node, i + 1)
                    work.append((w, 0))
                    recurse = True
                    break
                if on_stack.get(w):
                    lowlink[node] = min(lowlink[node], index[w])
            if recurse:
                continue
            if lowlink[node] == index[node]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    comp.append(w)
                    if w == node:
                        break
                result.append(sorted(comp))
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])
    return result


def _layer_of(module: str, layers: list[str]) -> int | None:
    best_idx, best_len = None, -1
    for idx, prefix in enumerate(layers):
        if (module == prefix or module.startswith(prefix + ".")) and len(prefix) > best_len:
            best_idx, best_len = idx, len(prefix)
    return best_idx


def analyze_tree(root, source_prefixes, thresholds) -> list[hc.Finding]:
    root = Path(root)
    files = _iter_python_files(root, list(source_prefixes or []))
    if not files:
        return []
    module_file, edges = build_graph(root, files)
    nodes = sorted(module_file)
    findings: list[hc.Finding] = []

    # Cycles
    for comp in _strongly_connected_components(nodes, edges):
        is_cycle = len(comp) > 1 or (len(comp) == 1 and comp[0] in edges.get(comp[0], []))
        if not is_cycle:
            continue
        members = sorted(comp)
        first = members[0]
        findings.append(hc.Finding(
            leaf=LEAF, signal="RESTRUCTURE", severity="high", path=module_file[first],
            line_start=1, line_end=1, symbol="cycle:" + "|".join(members),
            metric_name="import_cycle_size", metric_value=float(len(members)), metric_threshold=1.0,
            evidence_tool="ast", evidence_raw="import cycle: " + " -> ".join(members),
            confidence="high",
            suggested_action="Break the import cycle among: " + ", ".join(members),
        ))

    # Fan-in / fan-out
    in_degree = {m: 0 for m in nodes}
    for src in nodes:
        for dst in edges.get(src, []):
            in_degree[dst] = in_degree.get(dst, 0) + 1
    for m in nodes:
        out_deg = len(edges.get(m, []))
        if out_deg > thresholds["max_fan_out"]:
            findings.append(hc.Finding(
                leaf=LEAF, signal="RESTRUCTURE", severity="medium", path=module_file[m],
                line_start=1, line_end=1, symbol=m, metric_name="fan_out",
                metric_value=float(out_deg), metric_threshold=float(thresholds["max_fan_out"]),
                evidence_tool="ast", evidence_raw=f"{m} imports {out_deg} internal modules",
                confidence="high", suggested_action=f"Reduce coupling: {m} imports {out_deg} modules",
            ))
        if in_degree.get(m, 0) > thresholds["max_fan_in"]:
            findings.append(hc.Finding(
                leaf=LEAF, signal="RESTRUCTURE", severity="medium", path=module_file[m],
                line_start=1, line_end=1, symbol=m, metric_name="fan_in",
                metric_value=float(in_degree[m]), metric_threshold=float(thresholds["max_fan_in"]),
                evidence_tool="ast", evidence_raw=f"{m} is imported by {in_degree[m]} modules",
                confidence="high", suggested_action=f"Split god-module: {m} is imported by {in_degree[m]} modules",
            ))

    # Layering
    layers = thresholds.get("layers") or []
    if layers:
        for src in nodes:
            src_layer = _layer_of(src, layers)
            if src_layer is None:
                continue
            for dst in edges.get(src, []):
                dst_layer = _layer_of(dst, layers)
                if dst_layer is None:
                    continue
                if src_layer > dst_layer:  # lower layer importing higher layer
                    findings.append(hc.Finding(
                        leaf=LEAF, signal="RESTRUCTURE", severity="high", path=module_file[src],
                        line_start=1, line_end=1, symbol=f"{src}->{dst}", metric_name="layer_violation",
                        metric_value=float(src_layer - dst_layer), metric_threshold=0.0,
                        evidence_tool="ast", evidence_raw=f"{src} (layer {src_layer}) imports {dst} (layer {dst_layer})",
                        confidence="high",
                        suggested_action=f"Layering violation: {src} must not import {dst}",
                    ))

    return hc.sort_findings(findings)


def render_report(findings: list[hc.Finding]) -> str:
    lines = ["# structure-audit report", ""]
    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    lines.append(f"## RESTRUCTURE ({len(findings)})")
    for f in findings:
        lines.append(f"- `{f.path}` {f.symbol} — {f.metric_name}={f.metric_value:g} [{f.severity}]")
    lines.append("")
    return "\n".join(lines) + "\n"


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if config_path:
        try:
            thresholds.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError(f"invalid --config: {exc}") from exc
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic import-structure audit (advisory).")
    parser.add_argument("--root")
    parser.add_argument("--source-prefix", action="append", default=[], dest="source_prefixes",
                        help="Path prefix(es) relative to --root to include. Repeatable.")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--out-dir")
    parser.add_argument("--config", help="JSON file overriding thresholds (max_fan_out, max_fan_in, layers).")
    parser.add_argument("--format", choices=["json", "md"], default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir:
        print(json.dumps({"status": "error", "message": "--root and --out-dir are required"}))
        return hc.EXIT_ERROR
    try:
        thresholds = load_thresholds(args.config)
        findings = analyze_tree(args.root, args.source_prefixes, thresholds)
    except ToolError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return hc.EXIT_ERROR
    data = hc.write_findings(findings, args.out_dir, LEAF)
    Path(args.out_dir, "structure_report.md").write_text(render_report(findings), encoding="utf-8")
    print(json.dumps({"status": "ok", "findings": len(data), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if data else hc.EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
