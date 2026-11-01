"""A scripted fake model: deterministic replies from a JSON script."""

import json
from dataclasses import dataclass
from pathlib import Path

from mini_agent_kit.types import Message, ModelReply, ToolCall, ToolSchema


class ScriptMismatch(Exception):
    """A tool message did not match the script's expectation."""


class ScriptExhausted(Exception):
    """The model was asked for more turns than the script holds."""


@dataclass(frozen=True)
class Turn:
    reply: ModelReply
    expect: dict[str, str]


def _invalid(message: str) -> ValueError:
    return ValueError(message)


def _parse_call(index: int, raw: object) -> ToolCall:
    if not isinstance(raw, dict):
        raise _invalid(f"turn {index}: tool call must be an object")
    for key in ("id", "name", "arguments"):
        if key not in raw:
            raise _invalid(f"turn {index}: tool call missing {key}")
    if not (
        isinstance(raw["id"], str)
        and isinstance(raw["name"], str)
        and isinstance(raw["arguments"], dict)
    ):
        raise _invalid(f"turn {index}: tool call has wrong field types")
    return ToolCall(raw["id"], raw["name"], raw["arguments"])


def _parse_expect(index: int, raw: object) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in raw.items()
    ):
        raise _invalid(f"turn {index}: expect must map ids to text")
    return dict(raw)


def _parse_reply(index: int, raw: dict[str, object]) -> ModelReply:
    if ("final" in raw) == ("tool_calls" in raw):
        raise _invalid(f"turn {index}: needs exactly one of final or tool_calls")
    if "final" in raw:
        if not isinstance(raw["final"], str):
            raise _invalid(f"turn {index}: final must be text")
        return ModelReply(final=raw["final"])
    calls = raw["tool_calls"]
    if not isinstance(calls, list) or not calls:
        raise _invalid(f"turn {index}: tool_calls must be a non-empty list")
    return ModelReply(tool_calls=tuple(_parse_call(index, c) for c in calls))


def parse_turns(data: object) -> list[Turn]:
    """Validate script data and turn it into Turns."""
    if not isinstance(data, dict) or not isinstance(data.get("turns"), list):
        raise _invalid("script must be an object with a turns list")
    turns = []
    for index, raw in enumerate(data["turns"]):
        if not isinstance(raw, dict):
            raise _invalid(f"turn {index}: must be an object")
        turns.append(
            Turn(_parse_reply(index, raw), _parse_expect(index, raw.get("expect")))
        )
    return turns


def _tool_texts(messages: list[Message]) -> dict[str, str]:
    return {m.tool_call_id: m.content for m in messages if m.tool_call_id is not None}


class ScriptedModel:
    def __init__(self, data: object) -> None:
        self._turns = parse_turns(data)
        self._next = 0

    @classmethod
    def from_file(cls, path: str | Path) -> "ScriptedModel":
        return cls(json.loads(Path(path).read_text()))

    def complete(self, messages: list[Message], tools: list[ToolSchema]) -> ModelReply:
        if self._next >= len(self._turns):
            raise ScriptExhausted(f"script has only {len(self._turns)} turns")
        turn = self._turns[self._next]
        self._next += 1
        seen = _tool_texts(messages)
        for call_id, expected in turn.expect.items():
            actual = seen.get(call_id)
            if actual != expected:
                raise ScriptMismatch(
                    f"{call_id}: expected {expected!r}, got {actual!r}"
                )
        return turn.reply
