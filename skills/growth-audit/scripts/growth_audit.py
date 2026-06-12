#!/usr/bin/env python3
"""growth-audit leaf: git-based surface growth detection between revisions.

Metrics are language-blind and computed from ``git diff`` between
``--baseline-rev`` and ``HEAD`` (or ``--rev``).  Positive growth beyond
configured allowances emits GROWTH findings.

Metrics
-------
* **tracked_files_growth** — new tracked files
* **net_loc_growth**       — net lines-of-code change (additions – deletions)
* **docs_loc_growth**      — net documentation lines change
* **dependency_growth**    — new dependency declarations across common manifests
* **cli_flag_growth**      — new CLI flag / option declarations

Config
------
An optional JSON file passed via ``--config`` may contain an ``allow_growth``
array.  Each entry has ``metric``, ``max_delta``, and ``reason``.  Growth
within ``max_delta`` is suppressed (counted in the summary).  Growth beyond
``max_delta`` emits a FINDING.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Fallback to the repo shared helper until a vendored copy is placed.
_SHARED = Path(__file__).resolve().parents[3] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import health_common as hc  # noqa: E402

LEAF = "growth-audit"
SIGNAL_GROWTH = "RESTRUCTURE"

TOOL_TIMEOUT = 120

_DOC_GLOBS = (
    ".md", ".rst", ".txt", ".adoc",
    "docs/", "doc/", "README", "CHANGELOG", "CONTRIBUTING",
)

_DEP_FILES = (
    "requirements.txt", "requirements.in",
    "pyproject.toml", "setup.py", "setup.cfg",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "Pipfile",
)

# Per-file-type patterns that denote a new dependency declaration line.
_DEP_PATTERNS: dict[str, list[str]] = {
    ".txt": [r"^[A-Za-z0-9_\-\[\].><=!~;,@#\s]"],
    ".in": [r"^[A-Za-z0-9_\-\[\].><=!~;,@#\s]"],
    ".toml": [r'^"?[A-Za-z0-9_\-]+"?\s*='],
    ".py": [r"^\s*['\"]?[A-Za-z0-9_\-]+['\"]?\s*[,:)#]"],
    ".json": [r'"[A-Za-z0-9@_\-/]+"\s*:'],
    ".mod": [r"^[A-Za-z0-9_\-/.]+ v"],
    "Gemfile": [r'^\s*gem\s+["\']'],
    "Pipfile": [r'^\s*[A-Za-z0-9_\-]+\s*='],
}

# CLI flag patterns (heuristic, language-blind-ish).
_CLI_FLAG_PATTERNS: list[str] = [
    r"\.add_argument\(",
    r"@click\.(option|argument)\(",
    r"@(typer|cli)\.(option|argument)\(",
    r"@(cli|app|group)\.(option|argument)\(",
    r"parser\.add_argument\(",
    r"@(arg|flag|opt)",
    r"\.option\(",
    r"clap\(",
    r"derive\(.*Args",
]


# ---------------------------------------------------------------------------
# git helpers
# ---------------------------------------------------------------------------


class ToolError(RuntimeError):
    """Non-recoverable error (git missing, bad repo, etc.)."""


def _git(root: Path, *args: str, timeout: int = TOOL_TIMEOUT) -> str:
    """Run a git command in *root* and return stdout."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolError("git is not installed") from exc
    if proc.returncode != 0:
        raise ToolError(f"git {args[0]} failed: {proc.stderr.strip()}")
    return proc.stdout


def _validate_git_root(root: Path) -> None:
    """Raise ToolError if *root* is not inside a git working tree."""
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ToolError(f"not a git repository: {root}")


def _resolve_rev(root: Path, rev: str) -> str:
    """Resolve *rev* to a full commit SHA."""
    out = _git(root, "rev-parse", "--verify", f"{rev}^{{commit}}")
    return out.strip()


def _checkout_file_at_rev(
    root: Path, rev: str, rel_path: str, dest: Path
) -> bool:
    """Copy a single file from *rev* to *dest*.  Returns True on success."""
    try:
        _git(root, "show", f"{rev}:{rel_path}", timeout=30)
    except ToolError:
        return False
    content = _git(root, "show", f"{rev}:{rel_path}", timeout=30)
    dest.write_text(content, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# metric collectors
# ---------------------------------------------------------------------------


def _new_files(root: Path, base: str, head: str) -> list[str]:
    """Return list of newly added file paths (relative)."""
    out = _git(
        root, "diff", "--name-only", "--diff-filter=A", f"{base}..{head}"
    )
    return [l for l in out.splitlines() if l.strip()]


def _numstat_delta(
    root: Path, base: str, head: str, path_globs: tuple[str, ...] | None = None
) -> int:
    """Return net (additions – deletions) from ``git diff --numstat``.

    When *path_globs* is given, only matching files are counted.
    """
    args = ["diff", "--numstat", f"{base}..{head}"]
    out = _git(root, *args)
    total = 0
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        fpath = parts[2]
        if path_globs:
            if not any(
                fpath.endswith(g) or g.endswith("/") and fpath.startswith(g)
                for g in path_globs
            ):
                continue
        adds = int(parts[0]) if parts[0] != "-" else 0
        dels = int(parts[1]) if parts[1] != "-" else 0
        total += adds - dels
    return total


def _dependency_delta(root: Path, base: str, head: str) -> int:
    """Count new dependency declarations across known manifest files."""
    changed_dep_files = _git(
        root,
        "diff",
        "--name-only",
        f"{base}..{head}",
        "--",
        *_DEP_FILES,
    )
    total_new = 0
    for rel_path in changed_dep_files.splitlines():
        if not rel_path.strip():
            continue
        try:
            base_content = _git(root, "show", f"{base}:{rel_path}")
        except ToolError:
            base_content = ""
        try:
            head_content = _git(root, "show", f"{head}:{rel_path}")
        except ToolError:
            head_content = ""
        base_lines = set(_dep_entries(base_content, rel_path))
        head_lines = set(_dep_entries(head_content, rel_path))
        total_new += len(head_lines - base_lines)
    return total_new


def _dep_entries(content: str, path: str) -> list[str]:
    """Extract dependency-like lines from a manifest file's content."""
    entries: list[str] = []
    ext = Path(path).suffix
    name = Path(path).name
    patterns: list[str] = _DEP_PATTERNS.get(name, [])
    patterns.extend(_DEP_PATTERNS.get(ext, []))
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "/*")):
            continue
        for pat in patterns:
            if re.match(pat, stripped):
                entries.append(stripped)
                break
    return entries


def _cli_flag_delta(root: Path, base: str, head: str) -> int:
    """Count new CLI flag / option declarations in changed source files."""
    changed = _git(root, "diff", "--name-only", f"{base}..{head}")
    total_new = 0
    for rel_path in changed.splitlines():
        if not rel_path.strip():
            continue
        # Get the diff for this file
        try:
            diff_text = _git(root, "diff", f"{base}..{head}", "--", rel_path)
        except ToolError:
            continue
        for line in diff_text.splitlines():
            if not line.startswith("+"):
                continue
            if line.startswith("+++"):
                continue
            text = line[1:]
            for pat in _CLI_FLAG_PATTERNS:
                if re.search(pat, text):
                    total_new += 1
                    break
    return total_new


# ---------------------------------------------------------------------------
# config loading
# ---------------------------------------------------------------------------


DEFAULT_CONFIG: dict[str, Any] = {
    "allow_growth": [],
}


def _load_config(config_path: str | None) -> dict[str, Any]:
    """Load JSON config and merge with defaults."""
    cfg = dict(DEFAULT_CONFIG)
    if config_path is None:
        return cfg
    cfg_file = Path(config_path)
    try:
        raw = cfg_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise ToolError(f"cannot read config file: {exc}") from exc
    try:
        overrides = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ToolError(f"invalid JSON in config: {exc}") from exc
    if not isinstance(overrides, dict):
        raise ToolError("config root must be a JSON object")
    cfg.update(overrides)
    return cfg


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------


def _collect_metrics(
    root: Path, base: str, head: str
) -> dict[str, int]:
    """Return raw metric deltas collected from git."""
    new = _new_files(root, base, head)
    return {
        "tracked_files_growth": len(new),
        "net_loc_growth": _numstat_delta(root, base, head),
        "docs_loc_growth": _numstat_delta(root, base, head, _DOC_GLOBS),
        "dependency_growth": _dependency_delta(root, base, head),
        "cli_flag_growth": _cli_flag_delta(root, base, head),
    }


def _apply_allowances(
    metrics: dict[str, int],
    allow_growth: list[dict[str, Any]],
) -> tuple[list[hc.Finding], list[dict[str, Any]], list[dict[str, Any]]]:
    """Compare metrics against allowances; return (findings, suppressions, overflows)."""
    findings: list[hc.Finding] = []
    suppressions: list[dict[str, Any]] = []
    overflows: list[dict[str, Any]] = []

    for rule in allow_growth:
        metric_name = rule.get("metric", "")
        max_delta = rule.get("max_delta", 0)
        reason = rule.get("reason", "")

        if metric_name not in metrics:
            continue

        delta = metrics[metric_name]
        if delta <= 0:
            continue  # no positive growth to flag

        if delta <= max_delta:
            suppressions.append({
                "metric": metric_name,
                "delta": delta,
                "max_delta": max_delta,
                "reason": reason,
            })
        else:
            overflow = delta - max_delta
            overflows.append({
                "metric": metric_name,
                "delta": delta,
                "max_delta": max_delta,
                "overflow": overflow,
                "reason": reason,
            })
            findings.append(
                hc.Finding(
                    leaf=LEAF,
                    signal=SIGNAL_GROWTH,
                    severity=_severity_for_delta(metric_name, overflow),
                    path="<repo>",
                    line_start=0,
                    line_end=0,
                    symbol=f"{metric_name}",
                    metric_name=metric_name,
                    metric_value=float(delta),
                    metric_threshold=float(max_delta),
                    evidence_tool="git",
                    evidence_raw=json.dumps({
                        "base": "baseline-rev",
                        "head": "HEAD",
                        "delta": delta,
                        "allowance": max_delta,
                        "overflow": overflow,
                    }),
                    confidence="high",
                    suggested_action=(
                        f"Review {metric_name} growth of +{delta} "
                        f"(allowance: {max_delta}, overflow: {overflow})"
                    ),
                )
            )

    # Unsuppressed metrics not in any allowance rule: always emit if positive
    suppressed_metrics = {s["metric"] for s in suppressions}
    overflow_metrics = {o["metric"] for o in overflows}
    for name, delta in sorted(metrics.items()):
        if delta <= 0 or name in suppressed_metrics or name in overflow_metrics:
            continue
        findings.append(
            hc.Finding(
                leaf=LEAF,
                signal=SIGNAL_GROWTH,
                severity=_severity_for_delta(name, delta),
                path="<repo>",
                line_start=0,
                line_end=0,
                symbol=name,
                metric_name=name,
                metric_value=float(delta),
                metric_threshold=0.0,
                evidence_tool="git",
                evidence_raw=json.dumps({"delta": delta}),
                confidence="medium",
                suggested_action=f"Consider adding an allowance for {name} growth of +{delta}",
            )
        )

    return findings, suppressions, overflows


def _severity_for_delta(metric: str, delta: int) -> str:
    """Map a metric name and delta to a severity label."""
    if metric in ("tracked_files_growth", "dependency_growth"):
        if delta > 20:
            return "high"
        if delta > 10:
            return "medium"
        return "low"
    if metric in ("net_loc_growth", "docs_loc_growth"):
        if delta > 2000:
            return "high"
        if delta > 500:
            return "medium"
        return "low"
    if metric == "cli_flag_growth":
        if delta > 15:
            return "high"
        if delta > 5:
            return "medium"
        return "low"
    return "low"


def analyze_tree(
    root: str | Path,
    baseline_rev: str,
    config: dict[str, Any] | None = None,
) -> tuple[list[hc.Finding], dict[str, Any]]:
    """Core analysis — returns (findings, summary_dict)."""
    _root = Path(root)
    _validate_git_root(_root)

    try:
        base_sha = _resolve_rev(_root, baseline_rev)
    except ToolError as exc:
        raise ToolError(
            f"cannot resolve --baseline-rev {baseline_rev}: {exc}"
        ) from exc

    head_sha = _resolve_rev(_root, "HEAD")

    cfg = config or DEFAULT_CONFIG
    allow_growth: list[dict[str, Any]] = cfg.get("allow_growth", [])

    metrics = _collect_metrics(_root, base_sha, head_sha)
    findings, suppressions, overflows = _apply_allowances(metrics, allow_growth)

    summary: dict[str, Any] = {
        "leaf": LEAF,
        "baseline": baseline_rev,
        "baseline_sha": base_sha,
        "head_sha": head_sha,
        "metrics": metrics,
        "suppressions": suppressions,
        "suppression_count": len(suppressions),
        "overflow_count": len(overflows),
        "finding_count": len(findings),
    }

    return hc.sort_findings(findings), summary


# ---------------------------------------------------------------------------
# report rendering
# ---------------------------------------------------------------------------


def render_md(
    findings: list[hc.Finding], summary: dict[str, Any]
) -> str:
    """Produce a Markdown report."""
    lines = [
        "# growth-audit report",
        "",
        f"Baseline: `{summary.get('baseline', '?')}`",
        f"Baseline SHA: `{summary.get('baseline_sha', '?')[:12]}`",
        f"HEAD SHA: `{summary.get('head_sha', '?')[:12]}`",
        "",
        "## Metrics",
        "",
    ]
    metrics = summary.get("metrics", {})
    for name in sorted(metrics):
        lines.append(f"- **{name}**: {metrics[name]:+d}")
    lines.append("")

    suppressions = summary.get("suppressions", [])
    if suppressions:
        lines.append("## Suppressions")
        lines.append("")
        for s in suppressions:
            lines.append(
                f"- `{s['metric']}` delta={s['delta']:+d} "
                f"(max_delta={s['max_delta']}, reason={s['reason']})"
            )
        lines.append("")

    if not findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"

    by_signal: dict[str, list[hc.Finding]] = {}
    for f in findings:
        by_signal.setdefault(f.signal, []).append(f)

    for signal in sorted(by_signal):
        lines.append(f"## {signal} ({len(by_signal[signal])})")
        for f_item in by_signal[signal]:
            lines.append(
                f"- `{f_item.path}` **{f_item.symbol}** "
                f"value={f_item.metric_value:g} threshold={f_item.metric_threshold:g} "
                f"[{f_item.severity}]"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build arg parser for growth-audit."""
    p = argparse.ArgumentParser(
        description="Deterministic surface growth audit between git revisions.",
    )
    p.add_argument("--root", required=True, help="Repository root directory")
    p.add_argument("--out-dir", required=True, help="Output directory")
    p.add_argument(
        "--baseline-rev",
        required=True,
        help="Baseline git revision to compare against",
    )
    p.add_argument("--rev", default="HEAD", help="Target revision (default: HEAD)")
    p.add_argument(
        "--format", choices=["json", "md"], default="json", help="Report format"
    )
    p.add_argument("--config", help="Optional JSON config file with allowances")
    return p


def _emit_error(message: str) -> None:
    """Print error status JSON to stdout."""
    print(json.dumps({"status": "error", "message": message}))


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Returns exit code (0/1/2)."""
    ns = build_parser().parse_args(argv)

    root = Path(ns.root).resolve()
    out_dir = Path(ns.out_dir)

    try:
        cfg = _load_config(ns.config)
    except ToolError as exc:
        _emit_error(str(exc))
        return hc.EXIT_ERROR

    try:
        findings, summary = analyze_tree(root, ns.baseline_rev, cfg)
    except ToolError as exc:
        _emit_error(str(exc))
        return hc.EXIT_ERROR

    # Always write findings JSON
    hc.write_findings(findings, str(out_dir), LEAF)

    # Write summary JSON
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{LEAF}_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Write markdown report if requested
    if ns.format == "md":
        (out_dir / f"{LEAF}_report.md").write_text(
            render_md(findings, summary),
            encoding="utf-8",
        )

    print(json.dumps({"status": "ok", "findings": len(findings), "leaf": LEAF}))
    return hc.EXIT_FINDINGS if findings else hc.EXIT_CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
