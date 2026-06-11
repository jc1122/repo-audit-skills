"""Out-of-root path token hardening for docs-consistency-audit.

Verifies that absolute path tokens pointing to files outside --root are
skipped without crashing.  (SP8 G2-1)
"""

from helpers import load_module, read_findings


def test_out_of_root_token_is_skipped_no_crash(tmp_path):
    """Absolute .py path token outside --root → skipped, never a finding."""
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    # Create an out-of-root script that passes the argparse guard
    # (so the old code would reach _rel and crash with ValueError).
    x_py = outside / "x.py"
    x_py.write_text(
        "import argparse\n"
        "def build_parser():\n"
        "    return argparse.ArgumentParser(description='outside')\n"
    )

    abs_x = str(x_py.resolve())
    readme = root / "README.md"
    readme.write_text(
        f"# test\n\n"
        f"```bash\n"
        f"python3 {abs_x} --foo\n"
        f"```\n"
    )

    mod = load_module()
    out = tmp_path / "out"
    rc = mod.main(["--root", str(root), "--out-dir", str(out)])

    # Must not crash; exit 0 or 1.
    assert rc in {0, 1}, f"unexpected exit code {rc}"

    data = read_findings(out)

    # The out-of-root token must be absent from findings.
    for f in data:
        path = f.get("path", "")
        symbol = f.get("location", {}).get("symbol", "")
        assert abs_x not in (path, symbol), (
            f"out-of-root token leaked into findings: path={path!r} symbol={symbol!r}"
        )
