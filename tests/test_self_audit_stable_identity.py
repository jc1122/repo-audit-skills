import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "self_audit", ROOT / "scripts" / "self_audit.py"
)
SA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SA)


def _make_root_with_file(root: Path, rel: str, lines: list[str]) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _identity_for_finding(root: Path, symbol: str, leaf: str = "duplication") -> str:
    finding = {
        "leaf": leaf,
        "path": "shared/a.py",
        "location": {"symbol": symbol},
    }
    return SA._stable_symbol(root, finding)


def test_duplication_symbol_is_stable_by_clone_content(tmp_path):
    root = tmp_path / "repo"
    _make_root_with_file(
        root,
        "scripts/alpha.py",
        [
            "banner",
            "line one",
            "line two",
            "line three",
        ],
    )

    symbol = "shared/a.py ↔ scripts/alpha.py:2-3"
    expected_hash = hashlib.sha256("line one\nline two".encode("utf-8")).hexdigest()[
        :12
    ]

    assert (
        _identity_for_finding(root, symbol)
        == f"shared/a.py ↔ scripts/alpha.py#{expected_hash}"
    )


def test_duplication_identity_stable_when_lines_shift_up(tmp_path):
    root = tmp_path / "repo"
    target = _make_root_with_file(
        root,
        "scripts/beta.py",
        [
            "header line",
            "dup one",
            "dup two",
            "tail",
        ],
    )

    symbol_before = "scripts/beta.py:2-3"
    symbol_after = "scripts/beta.py:3-4"
    before = _identity_for_finding(root, symbol_before)

    target.write_text(
        "\n".join(["inserted above", "header line", "dup one", "dup two", "tail"])
        + "\n"
    )
    shifted_before = _identity_for_finding(root, symbol_before)
    after_after = _identity_for_finding(root, symbol_after)
    assert shifted_before != before
    assert after_after == before

    target.write_text(
        "\n".join(["inserted above", "header line", "dup one", "changed", "tail"])
        + "\n"
    )
    assert _identity_for_finding(root, symbol_after) != before


def test_non_duplication_symbol_is_unmodified(tmp_path):
    root = tmp_path / "repo"
    _make_root_with_file(root, "scripts/gamma.py", ["x = 1"])

    symbol = "scripts/gamma.py:1-1"
    finding = {
        "leaf": "quality",
        "path": "scripts/gamma.py",
        "location": {"symbol": symbol},
    }
    assert SA._stable_symbol(root, finding) == symbol
