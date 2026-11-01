import pytest

from mini_agent_kit.types import Message, ModelReply, ToolCall


def test_reply_final_only() -> None:
    assert ModelReply(final="hi").final == "hi"


def test_reply_tool_calls_only() -> None:
    call = ToolCall("1", "t", {})
    assert ModelReply(tool_calls=(call,)).tool_calls == (call,)


def test_reply_rejects_both() -> None:
    with pytest.raises(ValueError):
        ModelReply(final="x", tool_calls=(ToolCall("1", "t", {}),))


def test_reply_rejects_neither() -> None:
    with pytest.raises(ValueError):
        ModelReply()


def test_reply_allows_empty_final_text() -> None:
    assert ModelReply(final="").final == ""


def test_message_defaults() -> None:
    m = Message("user", "q")
    assert m.tool_calls == () and m.tool_call_id is None
