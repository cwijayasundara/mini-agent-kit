"""Shared data shapes: messages, tool calls, replies and tool errors."""

from dataclasses import dataclass, field
from typing import Literal, TypedDict


class ToolSchema(TypedDict):
    name: str
    description: str
    input_schema: dict[str, object]


@dataclass(frozen=True)
class ToolError:
    message: str


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class ModelReply:
    """Exactly one of a final text answer or a non-empty list of tool calls."""

    final: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()

    def __post_init__(self) -> None:
        if (self.final is None) == (not self.tool_calls):
            raise ValueError("reply needs exactly one of final or tool_calls")


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant", "tool"]
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = field(default=())
    tool_call_id: str | None = None
