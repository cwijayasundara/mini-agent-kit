import json

import pytest

from mini_agent_kit.fireworks import (
    FireworksError,
    FireworksModel,
    encode_message,
    parse_reply,
)
from mini_agent_kit.types import Message, ToolCall


def body(message: dict[str, object]) -> dict[str, object]:
    return {"choices": [{"message": message}]}


def test_parse_final() -> None:
    assert parse_reply(body({"content": "hi"})).final == "hi"


def test_parse_tool_calls() -> None:
    call = {
        "id": "a",
        "function": {"name": "calculator", "arguments": '{"expression": "1+1"}'},
    }
    reply = parse_reply(body({"content": None, "tool_calls": [call]}))
    assert reply.tool_calls == (ToolCall("a", "calculator", {"expression": "1+1"}),)


def test_parse_garbage_raises() -> None:
    with pytest.raises(FireworksError):
        parse_reply({"nope": 1})


def test_encode_assistant_and_tool() -> None:
    m = Message("assistant", tool_calls=(ToolCall("a", "t", {"x": 1}),))
    enc = encode_message(m)
    assert enc["tool_calls"][0]["function"]["arguments"] == json.dumps({"x": 1})  # type: ignore[index]
    assert encode_message(Message("tool", "4", tool_call_id="a"))["tool_call_id"] == "a"


def test_complete_sends_model_and_tools() -> None:
    sent: list[dict[str, object]] = []

    def transport(payload: dict[str, object]) -> dict[str, object]:
        sent.append(payload)
        return body({"content": "ok"})

    model = FireworksModel(transport=transport)
    reply = model.complete(
        [Message("user", "q")],
        [{"name": "t", "description": "d", "input_schema": {"type": "object"}}],
    )
    assert reply.final == "ok"
    assert sent[0]["model"] == "accounts/fireworks/models/glm-5p3-flash"
    assert sent[0]["temperature"] == 0


def test_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    with pytest.raises(FireworksError):
        FireworksModel()


def test_explicit_key_needs_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    assert FireworksModel(api_key="k") is not None


def test_env_key_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIREWORKS_API_KEY", "k")
    assert FireworksModel() is not None
