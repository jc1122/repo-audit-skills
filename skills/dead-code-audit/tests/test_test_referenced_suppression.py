import json

from helpers import load_module, read_findings


def test_vulture_findings_referenced_by_tests_are_counted_and_suppressed(
    tmp_path, capsys
):
    root = tmp_path / "repo"
    tests = root / "tests"
    tests.mkdir(parents=True)
    (root / "helpers.py").write_text(
        "\n".join(
            [
                "def used_in_test():",
                "    return 1",
                "",
                "def truly_dead():",
                "    return 2",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (tests / "test_helpers.py").write_text(
        "\n".join(
            [
                "from helpers import used_in_test",
                "",
                "",
                "def test_used_in_test():",
                "    assert used_in_test() == 1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    mod = load_module()
    rc = mod.main(
        [
            "--root",
            str(root),
            "--source-prefix",
            "helpers.py",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    status = json.loads(capsys.readouterr().out)
    data = read_findings(tmp_path / "out")
    vulture_deletes = [
        item
        for item in data
        if item["signal"] == "DELETE" and item["evidence"]["tool"] == "vulture"
    ]

    assert rc == 1
    assert status["suppressed_test_referenced"] == 1
    assert len(vulture_deletes) == 1
    assert vulture_deletes[0]["location"]["symbol"] == "truly_dead"
    assert "used_in_test" not in {item["location"]["symbol"] for item in data}
    assert "suppressed_test_referenced: 1" in (
        tmp_path / "out" / "dead-code_report.md"
    ).read_text(encoding="utf-8")
