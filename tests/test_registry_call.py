from typing import Literal

from mini_agent_kit.registry import Registry
from mini_agent_kit.types import ToolError


def make() -> Registry:
    reg = Registry()

    @reg.tool
    def add(a: int, b: int = 1) -> int:
        """Add."""
        return a + b

    @reg.tool
    def half(x: float) -> float:
        """Half."""
        return x / 2

    @reg.tool
    def flag(b: bool) -> bool:
        """Flag."""
        return b

    @reg.tool
    def total(xs: list[int]) -> int:
        """Total."""
        return sum(xs)

    @reg.tool
    def pick(c: Literal["a", "b"], n: Literal[1, 2] = 1) -> str:
        """Pick."""
        return f"{c}{n}"

    @reg.tool
    def boom(msg: str) -> str:
        """Boom."""
        raise RuntimeError(msg)

    return reg


def err(result: object) -> str:
    assert isinstance(result, ToolError)
    return result.message


def test_success_and_default() -> None:
    reg = make()
    assert reg.call("add", {"a": 2}) == 3
    assert reg.call("add", {"a": 2, "b": 5}) == 7


def test_unknown_tool() -> None:
    assert err(make().call("nope", {})) == "unknown tool: nope"


def test_missing_argument() -> None:
    assert err(make().call("add", {})) == "missing argument: a"


def test_unexpected_argument() -> None:
    assert err(make().call("add", {"a": 1, "z": 2})) == "unexpected argument: z"


def test_wrong_type() -> None:
    assert err(make().call("add", {"a": "1"})) == "a: expected integer"
    assert err(make().call("add", {"a": 1, "b": "x"})) == "b: expected integer"


def test_bool_not_int_or_float() -> None:
    assert err(make().call("add", {"a": True})) == "a: expected integer"
    assert err(make().call("half", {"x": False})) == "x: expected number"


def test_int_accepted_as_float_and_float_not_int() -> None:
    assert make().call("half", {"x": 3}) == 1.5
    assert err(make().call("add", {"a": 1.5})) == "a: expected integer"


def test_bool_requires_bool() -> None:
    assert make().call("flag", {"b": True}) is True
    assert err(make().call("flag", {"b": 1})) == "b: expected boolean"


def test_list_checks_items() -> None:
    assert make().call("total", {"xs": [1, 2]}) == 3
    assert (
        err(make().call("total", {"xs": [1, "2"]})) == "xs: expected array of integer"
    )
    assert err(make().call("total", {"xs": 5})) == "xs: expected array of integer"
    assert err(make().call("total", {"xs": [True]})) == "xs: expected array of integer"


def test_literal_checks_value_and_type() -> None:
    reg = make()
    assert reg.call("pick", {"c": "a", "n": 2}) == "a2"
    assert err(reg.call("pick", {"c": "z"})) == "c: expected one of 'a', 'b'"
    assert err(reg.call("pick", {"c": "a", "n": True})) == "n: expected one of 1, 2"


def test_tool_exception_becomes_error() -> None:
    assert err(make().call("boom", {"msg": "bad"})) == "boom failed: bad"
