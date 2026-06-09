"""Shared helpers for code-health leaf skills.

SOURCE OF TRUTH. This file is vendored (copied byte-for-byte) into each leaf at
``skills/<leaf>/scripts/health_common.py`` so every leaf is self-contained and
independently installable. ``scripts/check_vendored_common.py`` enforces that the
copies stay identical to this file.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

SIGNALS = frozenset(
    {"SIMPLIFY", "DECOMPOSE", "EXTRACT", "MERGE", "DELETE", "RESTRUCTURE", "LINT", "FORMAT", "TYPE"}
)
SEVERITIES = ("info", "low", "medium", "high")
CONFIDENCES = ("low", "medium", "high")

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2


@dataclasses.dataclass(frozen=True)
class Finding:
    leaf: str
    signal: str
    severity: str
    path: str
    line_start: int
    line_end: int
    symbol: str
    metric_name: str
    metric_value: float
    metric_threshold: float
    evidence_tool: str
    evidence_raw: str
    confidence: str
    suggested_action: str

    def stable_id(self) -> str:
        key = f"{self.leaf}|{self.path}|{self.symbol}|{self.metric_name}"
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.stable_id(),
            "leaf": self.leaf,
            "signal": self.signal,
            "severity": self.severity,
            "path": self.path,
            "location": {"line_start": self.line_start, "line_end": self.line_end, "symbol": self.symbol},
            "metric": {"name": self.metric_name, "value": self.metric_value, "threshold": self.metric_threshold},
            "evidence": {"tool": self.evidence_tool, "raw": self.evidence_raw},
            "confidence": self.confidence,
            "suggested_action": self.suggested_action,
        }


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (f.path, f.line_start, f.signal, f.metric_name, f.symbol))


def write_findings(findings: Iterable[Finding], out_dir: str | Path, leaf: str) -> list[dict[str, Any]]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = [f.to_dict() for f in sort_findings(findings)]
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    (out / f"{leaf}_findings.json").write_text(text, encoding="utf-8")
    return data
