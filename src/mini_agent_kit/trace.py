"""Run results and the steps they record."""

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal, cast

from mini_agent_kit.types import Message, ModelReply, ToolCall

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

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, text: str) -> "RunResult":
        raw = json.loads(text)
        return cls(
            raw["answer"], tuple(_step(s) for s in raw["steps"]), raw["stop_reason"]
        )


def _calls(raw: list[dict[str, Any]]) -> tuple[ToolCall, ...]:
    return tuple(ToolCall(c["id"], c["name"], c["arguments"]) for c in raw)


def _message(raw: dict[str, Any]) -> Message:
    return Message(
        cast(Any, raw["role"]),
        raw["content"],
        _calls(raw["tool_calls"]),
        raw["tool_call_id"],
    )


def _reply(raw: dict[str, Any] | None) -> ModelReply | None:
    if raw is None:
        return None
    return ModelReply(raw["final"], _calls(raw["tool_calls"]))


def _step(raw: dict[str, Any]) -> Step:
    return Step(
        tuple(_message(m) for m in raw["messages"]),
        _reply(raw["reply"]),
        tuple(
            ToolResult(r["name"], r["arguments"], r["result"])
            for r in raw["tool_results"]
        ),
        raw["duration_ms"],
        raw["error"],
    )
