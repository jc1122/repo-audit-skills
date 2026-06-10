#!/usr/bin/env python3
"""code-health-audit-pipeline: discover leaves, run in parallel, merge/rank/decide."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS_ROOT = HERE.parents[
    1
]  # <skills_root>/code-health-audit-pipeline/scripts -> skills root
DEFAULT_REGISTRY = HERE / "leaf_registry.json"

SEVERITY_WEIGHT = {"info": 0, "low": 1, "medium": 2, "high": 4}
CONFIDENCE_WEIGHT = {"low": 1, "medium": 2, "high": 3}
EFFORT = {
    "DELETE": 1,
    "LINT": 1,
    "FORMAT": 1,
    "TYPE": 2,
    "TEST": 3,
    "SIMPLIFY": 2,
    "MERGE": 2,
    "EXTRACT": 3,
    "DECOMPOSE": 3,
    "RESTRUCTURE": 4,
}

DEFAULT_GATE = {
    "gate_on_leaf_error": True,
    "gate_on_import_cycle": True,
    "max_type_errors": 1_000_000,
    "max_high_severity": 1_000_000,
}

TOOL_TIMEOUT = 120


def _dedupe_key(f: dict) -> tuple:
    return (
        f.get("path"),
        f.get("location", {}).get("line_start"),
        f.get("metric", {}).get("name"),
    )


def merge_and_dedupe(findings: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for f in sorted(findings, key=_sort_key):
        seen.setdefault(_dedupe_key(f), f)
    return list(seen.values())


def _sort_key(f: dict) -> tuple:
    loc = f.get("location", {})
    return (
        f.get("path", ""),
        loc.get("line_start", 0),
        f.get("signal", ""),
        f.get("metric", {}).get("name", ""),
    )


def score(f: dict) -> float:
    sev = SEVERITY_WEIGHT.get(f.get("severity"), 0)
    conf = CONFIDENCE_WEIGHT.get(f.get("confidence"), 1)
    effort = EFFORT.get(f.get("signal"), 2)
    return (sev * conf) / effort


def rank(findings: list[dict]) -> list[dict]:
    return sorted(findings, key=lambda f: (-score(f), _sort_key(f)))


def decide(
    findings: list[dict], leaf_exit: dict[str, int], gate: dict
) -> tuple[str, int]:
    errored = [n for n, code in leaf_exit.items() if code == 2]
    has_cycle = any(
        f.get("metric", {}).get("name") == "import_cycle_size" for f in findings
    )
    type_errors = sum(1 for f in findings if f.get("signal") == "TYPE")
    high = sum(1 for f in findings if f.get("severity") == "high")
    gated = (
        (gate["gate_on_leaf_error"] and errored)
        or (gate["gate_on_import_cycle"] and has_cycle)
        or type_errors > gate["max_type_errors"]
        or high > gate["max_high_severity"]
    )
    if gated:
        return "GATE", 2
    if findings:
        return "ADVISE", 1
    return "PASS", 0


def load_registry(registry_path: Path) -> list[dict]:
    data = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    return data.get("leaves", [])


def select_leaves(leaves: list[dict], languages: list[str]) -> list[dict]:
    wanted = set(languages)
    return [leaf for leaf in leaves if wanted & set(leaf.get("languages", []))]


def _partition_leaves(
    leaves: list[dict], coverage_json: str | None
) -> tuple[list[dict], list[dict]]:
    """Split leaves into (runnable, skipped) based on requires.

    A leaf without ``requires`` is always runnable.  For leaves with
    ``requires``, each key is checked: ``coverage_json`` is satisfied when
    *coverage_json* is not None; any other key is treated as NOT satisfied
    (fail-safe).  Skipped records are sorted by leaf name.
    """
    runnable: list[dict] = []
    skipped: list[dict] = []
    for leaf in leaves:
        requires = leaf.get("requires", {})
        if not requires:
            runnable.append(leaf)
            continue
        skip_reason = None
        for key, required in requires.items():
            if not required:
                continue
            if key == "coverage_json":
                if not coverage_json:
                    skip_reason = "requires coverage_json artifact"
                    break
            else:
                # Unknown requirement key — fail safe
                skip_reason = f"requires {key} artifact"
                break
        if skip_reason:
            skipped.append({"leaf": leaf["name"], "reason": skip_reason})
        else:
            runnable.append(leaf)
    skipped.sort(key=lambda s: s["leaf"])
    return runnable, skipped


def _resolve_script(leaf: dict, overrides: dict[str, str]) -> Path:
    if leaf["name"] in overrides:
        return Path(overrides[leaf["name"]])
    script = leaf["script"]
    p = Path(script)
    return p if p.is_absolute() else SKILLS_ROOT / script


def _run_one(
    leaf: dict,
    root: str,
    source_prefixes: list[str],
    out_dir: Path,
    overrides: dict[str, str],
    coverage_json: str | None = None,
):
    script = _resolve_script(leaf, overrides)
    leaf_out = out_dir / leaf["name"]
    cmd = [sys.executable, str(script), "--root", root, "--out-dir", str(leaf_out)]
    for pre in source_prefixes:
        cmd += ["--source-prefix", pre]
    if coverage_json and leaf.get("requires", {}).get("coverage_json"):
        cmd += ["--coverage-json", coverage_json]
    if not script.exists():
        return leaf["name"], 2, []
    try:
        proc = subprocess.run(
            cmd, text=True, capture_output=True, check=False, timeout=TOOL_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return leaf["name"], 2, []
    findings_path = leaf_out / leaf["findings_file"]
    findings: list[dict] = []
    if proc.returncode != 2 and findings_path.exists():
        try:
            findings = json.loads(findings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return leaf["name"], 2, []
    return leaf["name"], proc.returncode, findings


def run_leaves(
    leaves: list[dict],
    root: str,
    source_prefixes: list[str],
    out_dir: Path,
    overrides: dict[str, str],
    coverage_json: str | None = None,
):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    leaf_exit: dict[str, int] = {}
    all_findings: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, len(leaves))) as pool:
        results = list(
            pool.map(
                lambda leaf: _run_one(
                    leaf, root, source_prefixes, out_dir, overrides, coverage_json
                ),
                leaves,
            )
        )
    for name, code, findings in results:
        leaf_exit[name] = code
        all_findings.extend(findings)
    return all_findings, leaf_exit


def build_summary(
    ranked: list[dict], leaf_exit: dict[str, int], decision: str, code: int
) -> dict:
    by_signal: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for f in ranked:
        by_signal[f["signal"]] = by_signal.get(f["signal"], 0) + 1
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
    status = {0: "clean", 1: "findings", 2: "errored"}
    leaves = {}
    for name, exit_code in sorted(leaf_exit.items()):
        count = sum(1 for f in ranked if f.get("leaf") == name)
        leaves[name] = {
            "exit": exit_code,
            "status": status.get(exit_code, "unknown"),
            "count": count,
        }
    return {
        "supervisor": decision,
        "exit_code": code,
        "leaves": leaves,
        "totals": {
            "count": len(ranked),
            "by_signal": by_signal,
            "by_severity": by_severity,
        },
        "findings": ranked,
    }


def render_report(ranked: list[dict], decision: str) -> str:
    lines = [f"# code-health-audit-pipeline report — {decision}", ""]
    if not ranked:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"
    by_signal: dict[str, list[dict]] = {}
    for f in ranked:
        by_signal.setdefault(f["signal"], []).append(f)
    for signal in sorted(by_signal):
        lines.append(f"## {signal} ({len(by_signal[signal])})")
        for f in by_signal[signal]:
            loc = f["location"]
            lines.append(
                f"- `{f['path']}:{loc['line_start']}` {loc['symbol']} "
                f"[{f['severity']}/{f['leaf']}] — {f['suggested_action']}"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def load_gate(config_path: str | None) -> dict:
    gate = dict(DEFAULT_GATE)
    if config_path:
        try:
            gate.update(json.loads(Path(config_path).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"invalid --config: {exc}") from exc
    return gate


def _parse_overrides(values: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise SystemExit(f"--leaf-script must be name=PATH, got {item!r}")
        name, path = item.split("=", 1)
        overrides[name] = path
    return overrides


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run code-health leaves, merge/rank, decide."
    )
    parser.add_argument("--root")
    parser.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        dest="source_prefixes",
        help="Path prefix(es) relative to --root. Repeatable.",
    )
    parser.add_argument("--out-dir")
    parser.add_argument(
        "--languages",
        default="python",
        help="Comma-separated languages to select leaves.",
    )
    parser.add_argument(
        "--registry", default=str(DEFAULT_REGISTRY), help="Leaf registry JSON."
    )
    parser.add_argument(
        "--leaf-script",
        action="append",
        default=[],
        help="Override: name=PATH. Repeatable.",
    )
    parser.add_argument("--config", help="JSON gate overrides.")
    parser.add_argument(
        "--coverage-json",
        default=None,
        help="Path to coverage JSON for artifact-gated leaves.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root or not args.out_dir:
        print(
            json.dumps(
                {"status": "error", "message": "--root and --out-dir are required"}
            )
        )
        return 2
    gate = load_gate(args.config)
    overrides = _parse_overrides(args.leaf_script)
    leaves = select_leaves(
        load_registry(Path(args.registry)), args.languages.split(",")
    )
    coverage_json = args.coverage_json
    runnable_leaves, skipped = _partition_leaves(leaves, coverage_json)
    out_dir = Path(args.out_dir)
    findings, leaf_exit = run_leaves(
        runnable_leaves,
        args.root,
        args.source_prefixes,
        out_dir,
        overrides,
        coverage_json,
    )
    ranked = rank(merge_and_dedupe(findings))
    decision, code = decide(ranked, leaf_exit, gate)
    summary = build_summary(ranked, leaf_exit, decision, code)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "code_health_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "code_health_report.md").write_text(
        render_report(ranked, decision), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "supervisor": decision,
                "findings": len(ranked),
                "skipped": skipped,
            }
        )
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
