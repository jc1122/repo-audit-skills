#!/usr/bin/env python3
"""Assert each leaf's vendored health_common.py matches the shared source of truth."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "shared" / "health_common.py"
SKILLS = ROOT / "skills"


def main() -> int:
    if not SOURCE.exists():
        print(
            json.dumps(
                {"status": "fail", "defects": ["shared/health_common.py missing"]},
                indent=2,
            )
        )
        return 1
    source_bytes = SOURCE.read_bytes()
    defects: list[str] = []
    copies = (
        sorted(SKILLS.glob("*/scripts/health_common.py")) if SKILLS.exists() else []
    )
    for copy in copies:
        if copy.read_bytes() != source_bytes:
            defects.append(f"vendored copy drifted: {copy.relative_to(ROOT)}")
    if defects:
        print(json.dumps({"status": "fail", "defects": defects}, indent=2))
        return 1
    print(
        json.dumps(
            {"status": "pass", "checked": [str(c.relative_to(ROOT)) for c in copies]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
