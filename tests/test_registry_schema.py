from typing import Any, Literal

import pytest

from mini_agent_kit.registry import Registry


def schema_of(fn: Any) -> dict[str, Any]:
    reg = Registry()
    reg.register(fn)
    return dict(reg.schemas()[0]["input_schema"])


def test_all_supported_types_and_optional() -> None:
    def f(
        s: str,
        i: int,
        x: float,
        b: bool,
        xs: list[int],
        lit: Literal["a", "b"],
        n: Literal[1, 2],
        opt: str = "d",
    ) -> str:
        """F."""
        return s

    assert schema_of(f) == {
        "type": "object",
        "properties": {
            "s": {"type": "string"},
            "i": {"type": "integer"},
            "x": {"type": "number"},
            "b": {"type": "boolean"},
            "xs": {"type": "array", "items": {"type": "integer"}},
            "lit": {"enum": ["a", "b"]},
            "n": {"enum": [1, 2]},
            "opt": {"type": "string"},
        },
        "required": ["s", "i", "x", "b", "xs", "lit", "n"],
        "additionalProperties": False,
    }


def test_schemas_sorted_by_name() -> None:
    reg = Registry()

    def zed() -> int:
        """Z."""
        return 1

    def alpha() -> int:
        """A."""
        return 1

    reg.register(zed)
    reg.register(alpha)
    assert [s["name"] for s in reg.schemas()] == ["alpha", "zed"]


@pytest.mark.parametrize(
    "annotation",
    [dict[str, int], list[list[int]], list[dict[str, int]], Literal[1.5], bytes, Any],
)
def test_unsupported_annotation_names_parameter(annotation: Any) -> None:
    def f(weird: Any) -> int:
        """F."""
        return 1

    f.__annotations__["weird"] = annotation
    with pytest.raises(TypeError, match="weird"):
        Registry().register(f)


def test_missing_annotation_rejected() -> None:
    def f(plain) -> int:  # type: ignore[no-untyped-def]
        """F."""
        return 1

    with pytest.raises(TypeError, match="plain"):
        Registry().register(f)


def test_var_args_rejected() -> None:
    def f(*rest: int) -> int:
        """F."""
        return 1

    with pytest.raises(TypeError, match="rest"):
        Registry().register(f)
