"""Threshold loading for repo-hygiene-audit."""

from __future__ import annotations

import json
from pathlib import Path

from _git_utils import ToolError

DEFAULT_THRESHOLDS = {"max_tracked_file_bytes": 1048576}


def load_thresholds(config_path: str | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if not config_path:
        return thresholds
    try:
        overrides = json.loads(Path(config_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolError(f"invalid --config: {exc}") from exc
    thresholds.update(overrides)
    return thresholds
