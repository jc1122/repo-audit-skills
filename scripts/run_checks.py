#!/usr/bin/env python3
"""Timed gate runner core — runs all check scripts, tracks timings, and enforces budget.

Phase 1: cheap gates run concurrently via ThreadPoolExecutor.
Phase 2: heavy gates run sequentially (already internally parallel).

Writes per-gate elapsed seconds to ``scripts/check_timings.json``.
Reads per-gate second budgets from ``scripts/check_budget.json`` (optional).

Stdlib only — no third-party dependencies.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

# ------------------------------------------------------------------ gate definitions

CHEAP: list[tuple[str, str]] = [
    ("vendored", "scripts/check_vendored_common.py"),
    ("fixtures", "scripts/check_skill_fixtures.py"),
    ("growth", "scripts/check_growth.py"),
    ("release", "scripts/check_release.py"),
    ("selfaudit", "scripts/check_self_audit.py"),
    ("security", "scripts/check_security_audit.py"),
    ("hygiene", "scripts/check_repo_hygiene.py"),
    ("docs", "scripts/check_docs_consistency.py"),
    ("dependency", "scripts/check_dependency_audit.py"),
    ("instrlint", "scripts/check_instruction_lint.py"),
]

HEAVY: list[tuple[str, str]] = [
    ("coverage", "scripts/check_coverage_gap.py"),
    # full-pytest is opt-in only (npm run check:pytest); coverage already gates green.
]

# ------------------------------------------------------------------ budget helpers


def budget_violations(
    timings: dict[str, float], budget: dict[str, float]
) -> list[tuple[str, float, float | None]]:
    """Return ``(gate, elapsed, budget)`` for every gate whose elapsed time
    exceeds its budget entry, or whose gate name is missing from *budget*
    entirely (``budget`` is ``None`` in that case)."""
    violations: list[tuple[str, float, float | None]] = []
    for gate_name, elapsed in timings.items():
        budget_val = budget.get(gate_name)
        if budget_val is None:
            violations.append((gate_name, elapsed, None))
        elif elapsed > budget_val:
            violations.append((gate_name, elapsed, budget_val))
    return violations


def _load_budget() -> dict[str, float]:
    """Load the gate budget from *scripts/check_budget.json*, returning an
    empty dict when the file does not exist."""
    budget_path = SCRIPTS_DIR / "check_budget.json"
    if budget_path.is_file():
        with budget_path.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {}


# ------------------------------------------------------------------ gate execution


def _run_one(gate_name: str, script_rel: str) -> tuple[str, int, float, str]:
    """Run a single check script and return ``(name, exit_code, elapsed, tail)``.

    *tail* combines the last 2000 chars of stdout + stderr for human-readable
    failure reporting in ``main()``.
    """
    script = ROOT / script_rel
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(ROOT),
            check=False,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        return (gate_name, 1, elapsed, "TIMEOUT after 600 s")
    elapsed = time.perf_counter() - start
    combined = (proc.stdout + proc.stderr).strip()
    tail = combined[-2000:] if len(combined) > 2000 else combined
    return (gate_name, proc.returncode, elapsed, tail)


def _run_all_gates(
    timings: dict[str, float], results: dict[str, tuple[int, str]]
) -> None:
    """Populate *timings* and *results* by executing every gate.

    Cheap gates run concurrently; heavy gates run sequentially.
    """
    with ThreadPoolExecutor(max_workers=len(CHEAP)) as executor:
        future_to_name = {
            executor.submit(_run_one, name, path): name for name, path in CHEAP
        }
        for future in as_completed(future_to_name):
            name, code, elapsed, tail = future.result()
            timings[name] = elapsed
            results[name] = (code, tail)

    for name, path in HEAVY:
        name, code, elapsed, tail = _run_one(name, path)
        timings[name] = elapsed
        results[name] = (code, tail)


def _write_timings(timings: dict[str, float]) -> None:
    """Persist per-gate elapsed seconds to ``scripts/check_timings.json``."""
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    timings_path = SCRIPTS_DIR / "check_timings.json"
    timings_path.write_text(json.dumps(timings, indent=2) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ reporting


def _print_failed_gates(
    results: dict[str, tuple[int, str]], timings: dict[str, float]
) -> None:
    """Print the tail output of every gate that returned a non-zero exit code."""
    print("--- FAILED GATES ---")
    for name in sorted(results):
        code, tail = results[name]
        if code != 0:
            print(f"\nFAIL  {name}  (exit {code}, {timings[name]:.2f}s)")
            if tail:
                print(tail)


def _print_over_budget(
    violations: list[tuple[str, float, float | None]],
) -> None:
    """Print one line per budget violation."""
    print("\n--- OVER BUDGET ---")
    for name, elapsed, budget_val in violations:
        if budget_val is not None:
            print(f"OVER-BUDGET  {name}  {elapsed:.3f}s > {budget_val:.3f}s")
        else:
            print(f"OVER-BUDGET  {name}  {elapsed:.3f}s (no budget entry)")


def _print_summary(
    results: dict[str, tuple[int, str]],
    violations: list[tuple[str, float, float | None]],
) -> None:
    """Print the one-line ``gates:`` summary."""
    cheap_passed = sum(
        1 for name, _ in CHEAP if results.get(name, (1, ""))[0] == 0
    )
    heavy_passed = sum(
        1 for name, _ in HEAVY if results.get(name, (1, ""))[0] == 0
    )
    n_failed = sum(1 for code, _ in results.values() if code != 0)
    print(
        f"\ngates: {cheap_passed}/{len(CHEAP)} cheap, "
        f"{heavy_passed}/{len(HEAVY)} heavy, "
        f"{len(violations)} over-budget, "
        f"{n_failed} failed"
    )


# ------------------------------------------------------------------ main


def main() -> int:
    """Run every gate, write timings, and report failures / budget violations.

    Returns 0 when every gate passes and stays within budget; nonzero
    otherwise.
    """
    timings: dict[str, float] = {}
    results: dict[str, tuple[int, str]] = {}

    _run_all_gates(timings, results)
    _write_timings(timings)

    budget = _load_budget()
    violations = budget_violations(timings, budget)

    any_failure = any(code != 0 for code, _ in results.values())
    exit_code = 1 if (any_failure or violations) else 0

    if any_failure:
        _print_failed_gates(results, timings)
    if violations:
        _print_over_budget(violations)
    _print_summary(results, violations)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
