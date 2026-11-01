import re
from datetime import UTC, datetime

import pytest

from mini_agent_kit.toys import calculator, make_clock, toy_registry, word_count
from mini_agent_kit.types import ToolError


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("17 * 23", "391"),
        ("1 + 2 * 3", "7"),
        ("(1 + 2) * 3", "9"),
        ("10 - 4 - 3", "3"),
        ("100 / 5 / 2", "10"),
        ("10 / 4", "2.5"),
        ("1.5 + 1.5", "3"),
        ("0.1 + 0.2", "0.3"),
        ("1 / 3", "0.3333333333333333333333333333"),
        ("-3 + 5", "2"),
        ("2 * -3", "-6"),
        ("--4", "4"),
        (".5 * 4", "2"),
        ("  7  ", "7"),
        ("2 * (3 + (4 - 1))", "12"),
        ("0 * 5", "0"),
        ("7 - 7.5", "-0.5"),
    ],
)
def test_calculator_values(expression: str, expected: str) -> None:
    assert calculator(expression) == expected


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("1 / 0", "division by zero"),
        ("1 / (2 - 2)", "division by zero"),
        ("", "unexpected end"),
        ("1 +", "unexpected end"),
        ("(1 + 2", "missing closing"),
        ("1 2", "unexpected '2'"),
        ("1 + a", "unexpected 'a'"),
        ("__import__('os')", "unexpected"),
        (")", "unexpected ')'"),
        ("2 ** 3", "unexpected '*'"),
        ("1 +* 2", "unexpected '*'"),
    ],
)
def test_calculator_errors(expression: str, message: str) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        calculator(expression)


def test_word_count() -> None:
    assert word_count("the quick  brown\nfox") == 4
    assert word_count("   ") == 0


def test_clock_default_utc_and_zone() -> None:
    clock = make_clock(lambda: datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC))
    assert clock() == "2026-01-02T03:04:05+00:00"
    assert clock("Asia/Tokyo") == "2026-01-02T12:04:05+09:00"


@pytest.mark.parametrize("name", ["Mars/Base", "../etc", ""])
def test_clock_unknown_zone(name: str) -> None:
    clock = make_clock(lambda: datetime(2026, 1, 2, tzinfo=UTC))
    with pytest.raises(ValueError, match="unknown timezone"):
        clock(name)


def test_toy_registry_through_call() -> None:
    reg = toy_registry()
    assert [s["name"] for s in reg.schemas()] == ["calculator", "clock", "word_count"]
    assert reg.call("calculator", {"expression": "17 * 23"}) == "391"
    assert reg.call("word_count", {"text": "a b"}) == 2
    failure = reg.call("calculator", {"expression": "1/0"})
    assert failure == ToolError("calculator failed: division by zero")
    assert isinstance(reg.call("clock", {}), str)
