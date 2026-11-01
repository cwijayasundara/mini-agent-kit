"""Run results and the steps they record."""

from dataclasses import dataclass
from typing import Literal

from mini_agent_kit.types import Message, ModelReply

StopReason = Literal["final", "max_steps", "error"]


@dataclass(frozen=True)
class ToolResult:
    name: str
    arguments: dict[str, object]
    result: str


@dataclass(frozen=True)
class Step:
    messages: tuple[Message, ...]
    reply: ModelReply | None
    tool_results: tuple[ToolResult, ...]
    duration_ms: float
    error: str | None = None


@dataclass(frozen=True)
class RunResult:
    answer: str | None
    steps: tuple[Step, ...]
    stop_reason: StopReason
