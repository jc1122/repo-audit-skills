import scripts.run_checks as rc


def test_budget_violation_fails_gate(tmp_path):
    budget = {"selfaudit": 0.000001}
    timings = {"selfaudit": 1.5}
    violations = rc.budget_violations(timings, budget)
    assert violations == [("selfaudit", 1.5, 0.000001)]


def test_within_budget_passes():
    assert rc.budget_violations({"selfaudit": 1.0}, {"selfaudit": 30}) == []


def test_missing_budget_entry_is_a_violation():
    # Every gate must have a budget row: silence is not allowed.
    assert rc.budget_violations({"newgate": 1.0}, {}) == [("newgate", 1.0, None)]
