"""Fresh-clone guard: scanned markdown must not reference gitignored snapshots by path.

The docs-consistency leaf scans *.md under scripts/ (self-audit production scope)
and docs/self-audit/ (check:docs living-docs scope). A literal
`scripts/<class>_snapshot.json` token resolves on dev machines, where the
gitignored file persists between gate runs, but not in a fresh clone — so CI
fails while every local gate stays green (SP9 ship, run 27351678384).
Reference snapshots by basename ("`foo_snapshot.json` under `scripts/`") or
with placeholder markers (`<class>`) instead.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT_TOKEN = re.compile(r"scripts/[A-Za-z_]+_snapshot\.json")
SCANNED_DOC_ROOTS = ("scripts", "docs/self-audit")


def test_no_gitignored_snapshot_tokens_in_scanned_docs():
    offenders = []
    for root in SCANNED_DOC_ROOTS:
        for md in sorted((REPO / root).glob("*.md")):
            for lineno, line in enumerate(
                md.read_text(encoding="utf-8").splitlines(), 1
            ):
                if SNAPSHOT_TOKEN.search(line):
                    offenders.append(f"{md.relative_to(REPO)}:{lineno}")
    assert not offenders, (
        "gitignored snapshot paths referenced as literal tokens "
        "(these break fresh-clone CI): " + ", ".join(offenders)
    )
