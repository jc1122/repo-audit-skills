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
SKILLS_ROOT = HERE.parents[1]  # <skills_root>/code-health-audit-pipeline/scripts -> skills root
DEFAULT_REGISTRY = HERE / "leaf_registry.json"

SEVERITY_WEIGHT = {"info": 0, "low": 1, "medium": 2, "high": 4}
CONFIDENCE_WEIGHT = {"low": 1, "medium": 2, "high": 3}
EFFORT = {
    "DELETE": 1, "LINT": 1, "FORMAT": 1,
    "TYPE": 2, "SIMPLIFY": 2, "MERGE": 2,
    "EXTRACT": 3, "DECOMPOSE": 3, "RESTRUCTURE": 4,
}

DEFAULT_GATE = {
    "gate_on_leaf_error": True,
    "gate_on_import_cycle": True,
    "max_type_errors": 1_000_000,
    "max_high_severity": 1_000_000,
}


def _dedupe_key(f: dict) -> tuple:
    return (f.get("path"), f.get("location", {}).get("line_start"), f.get("metric", {}).get("name"))


def merge_and_dedupe(findings: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for f in sorted(findings, key=_sort_key):
        seen.setdefault(_dedupe_key(f), f)
    return list(seen.values())


def _sort_key(f: dict) -> tuple:
    loc = f.get("location", {})
    return (f.get("path", ""), loc.get("line_start", 0), f.get("signal", ""), f.get("metric", {}).get("name", ""))


def score(f: dict) -> float:
    sev = SEVERITY_WEIGHT.get(f.get("severity"), 0)
    conf = CONFIDENCE_WEIGHT.get(f.get("confidence"), 1)
    effort = EFFORT.get(f.get("signal"), 2)
    return (sev * conf) / effort


def rank(findings: list[dict]) -> list[dict]:
    return sorted(findings, key=lambda f: (-score(f), _sort_key(f)))


def decide(findings: list[dict], leaf_exit: dict[str, int], gate: dict) -> tuple[str, int]:
    errored = [n for n, code in leaf_exit.items() if code == 2]
    has_cycle = any(f.get("metric", {}).get("name") == "import_cycle_size" for f in findings)
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


def _resolve_script(leaf: dict, overrides: dict[str, str]) -> Path:
    if leaf["name"] in overrides:
        return Path(overrides[leaf["name"]])
    script = leaf["script"]
    p = Path(script)
    return p if p.is_absolute() else SKILLS_ROOT / script


def _run_one(leaf: dict, root: str, source_prefixes: list[str], out_dir: Path, overrides: dict[str, str]):
    script = _resolve_script(leaf, overrides)
    leaf_out = out_dir / leaf["name"]
    cmd = [sys.executable, str(script), "--root", root, "--out-dir", str(leaf_out)]
    for pre in source_prefixes:
        cmd += ["--source-prefix", pre]
    if not script.exists():
        return leaf["name"], 2, []
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    findings_path = leaf_out / leaf["findings_file"]
    findings: list[dict] = []
    if proc.returncode != 2 and findings_path.exists():
        try:
            findings = json.loads(findings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return leaf["name"], 2, []
    return leaf["name"], proc.returncode, findings


def run_leaves(leaves: list[dict], root: str, source_prefixes: list[str], out_dir: Path,
               overrides: dict[str, str]):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    leaf_exit: dict[str, int] = {}
    all_findings: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, len(leaves))) as pool:
        results = list(pool.map(
            lambda leaf: _run_one(leaf, root, source_prefixes, out_dir, overrides), leaves
        ))
    for name, code, findings in results:
        leaf_exit[name] = code
        all_findings.extend(findings)
    return all_findings, leaf_exit
