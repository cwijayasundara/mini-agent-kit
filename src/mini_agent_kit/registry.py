"""Tool registry: register plain functions, derive schemas, call safely."""

import inspect
import typing
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, TypeVar, get_args, get_origin

from mini_agent_kit.types import ToolError, ToolSchema

F = TypeVar("F", bound=Callable[..., Any])

_SCALARS: dict[type, str] = {
    str: "string",
    bool: "boolean",
    int: "integer",
    float: "number",
}


@dataclass(frozen=True)
class _Param:
    name: str
    schema: dict[str, object]
    required: bool


@dataclass(frozen=True)
class _Tool:
    name: str
    description: str
    fn: Callable[..., Any]
    params: tuple[_Param, ...]


def _scalar_schema(annotation: object) -> dict[str, object] | None:
    if isinstance(annotation, type) and annotation in _SCALARS:
        return {"type": _SCALARS[annotation]}
    return None


def _literal_schema(annotation: object) -> dict[str, object] | None:
    if get_origin(annotation) is not Literal:
        return None
    values = get_args(annotation)
    if not values or not all(type(v) in (str, int) for v in values):
        return None
    return {"enum": list(values)}


def _list_schema(annotation: object) -> dict[str, object] | None:
    if get_origin(annotation) is not list:
        return None
    args = get_args(annotation)
    items = _scalar_schema(args[0]) if len(args) == 1 else None
    return None if items is None else {"type": "array", "items": items}


def schema_for(annotation: object) -> dict[str, object] | None:
    """JSON Schema for a supported annotation, or None."""
    return (
        _scalar_schema(annotation)
        or _literal_schema(annotation)
        or _list_schema(annotation)
    )


def _description(fn: Callable[..., Any]) -> str:
    doc = inspect.getdoc(fn)
    if not doc or not doc.strip():
        raise ValueError(f"tool {fn.__name__} needs a docstring")
    return " ".join(doc.strip().split("\n\n")[0].split())


def _params(fn: Callable[..., Any]) -> tuple[_Param, ...]:
    hints = typing.get_type_hints(fn)
    params = []
    for p in inspect.signature(fn).parameters.values():
        schema = schema_for(hints[p.name]) if p.name in hints else None
        if schema is None or p.kind not in (
            p.POSITIONAL_OR_KEYWORD,
            p.KEYWORD_ONLY,
        ):
            raise TypeError(f"{p.name}: unsupported parameter type")
        params.append(_Param(p.name, schema, p.default is p.empty))
    return tuple(params)


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _matches_scalar(kind: object, value: object) -> bool:
    if kind == "string":
        return isinstance(value, str)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return _is_number(value)


def describe(schema: dict[str, object]) -> str:
    """Human name of a schema's type, used in error messages."""
    if "enum" in schema:
        return "one of " + ", ".join(
            repr(v) for v in typing.cast(list[object], schema["enum"])
        )
    if schema["type"] == "array":
        items = typing.cast(dict[str, object], schema["items"])
        return f"array of {items['type']}"
    return str(schema["type"])


def matches(schema: dict[str, object], value: object) -> bool:
    """Whether value satisfies a schema produced by schema_for."""
    if "enum" in schema:
        return any(
            type(value) is type(v) and value == v
            for v in typing.cast(list[object], schema["enum"])
        )
    if schema["type"] == "array":
        items = typing.cast(dict[str, object], schema["items"])
        return isinstance(value, list) and all(matches(items, v) for v in value)
    return _matches_scalar(schema["type"], value)


def _check(tool: _Tool, arguments: dict[str, object]) -> str | None:
    """The first validation error message, or None when arguments are fine."""
    known = {p.name for p in tool.params}
    for p in tool.params:
        if p.required and p.name not in arguments:
            return f"missing argument: {p.name}"
    for key in arguments:
        if key not in known:
            return f"unexpected argument: {key}"
    for p in tool.params:
        if p.name in arguments and not matches(p.schema, arguments[p.name]):
            return f"{p.name}: expected {describe(p.schema)}"
    return None


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, _Tool] = {}

    def register(self, fn: F) -> F:
        """Register fn as a tool and return it unchanged."""
        name = fn.__name__
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = _Tool(name, _description(fn), fn, _params(fn))
        return fn

    def tool(self, fn: F) -> F:
        """Decorator form of register."""
        return self.register(fn)

    def schemas(self) -> list[ToolSchema]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": {
                    "type": "object",
                    "properties": {p.name: p.schema for p in t.params},
                    "required": [p.name for p in t.params if p.required],
                    "additionalProperties": False,
                },
            }
            for _, t in sorted(self._tools.items())
        ]

    def call(self, name: str, arguments: dict[str, object]) -> object | ToolError:
        """Validate and run a tool. Never raises."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolError(f"unknown tool: {name}")
        problem = _check(tool, arguments)
        if problem is not None:
            return ToolError(problem)
        try:
            result: object = tool.fn(**arguments)
        except Exception as exc:  # noqa: BLE001 - tool failures must not escape
            return ToolError(f"{name} failed: {exc}")
        return result
