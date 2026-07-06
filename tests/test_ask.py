import pytest

from crashlens import ask


def test_guard_allows_select():
    assert ask._guard_sql("SELECT * FROM crashes;") == "SELECT * FROM crashes"


def test_guard_allows_cte():
    sql = "WITH t AS (SELECT 1) SELECT * FROM t"
    assert ask._guard_sql(sql) == sql


@pytest.mark.parametrize(
    "bad",
    [
        "DROP TABLE crashes",
        "DELETE FROM crashes",
        "UPDATE crashes SET borough = 'X'",
        "INSERT INTO crashes VALUES (1)",
    ],
)
def test_guard_rejects_mutations(bad):
    with pytest.raises(ValueError):
        ask._guard_sql(bad)


def test_is_available_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ask.is_available() is False
