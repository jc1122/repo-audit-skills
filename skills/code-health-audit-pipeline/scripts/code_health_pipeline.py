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
