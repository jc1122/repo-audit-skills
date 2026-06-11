"""Shared constants, types, and the health_common import for the hotspot-audit leaf."""

from __future__ import annotations

import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health_common as hc  # noqa: E402, F401

LEAF = "hotspot"
DECLARED_COUPLING = "declared_coupling"
SINGLE_MAINTAINER = "single_maintainer"

DEFAULT_THRESHOLDS = {
    "min_churn_commits": 5,
    "min_churn_complexity_product": 1000,
    "min_coupling_ratio": 0.7,
    "min_coupling_changes": 5,
    "max_commit_files": 50,
    "min_author_share": 0.9,
    "min_author_commits": 10,
    "coupling_allow_pairs": [],
    "single_maintainer": False,
}


class ToolError(RuntimeError):
    pass


def default_suppression_counts() -> dict[str, int]:
    """Return counted suppression defaults for config-driven policies."""
    return {DECLARED_COUPLING: 0, SINGLE_MAINTAINER: 0}


_EvidenceCtx = namedtuple(
    "_EvidenceCtx", ["num_commits_read", "max_commits", "short_sha"]
)
