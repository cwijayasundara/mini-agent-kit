import json
from pathlib import Path

import pytest

from mini_agent_kit.scripted import ScriptedModel, ScriptExhausted, ScriptMismatch
from mini_agent_kit.types import Message, ToolCall

CALL = {"id": "c1", "name": "t", "arguments": {"x": 1}}


def test_returns_turns_in_order_then_exhausts() -> None:
    model = ScriptedModel({"turns": [{"tool_calls": [CALL]}, {"final": "done"}]})
    first = model.complete([], [])
    assert first.tool_calls == (ToolCall("c1", "t", {"x": 1}),)
    assert model.complete([], []).final == "done"
    with pytest.raises(ScriptExhausted):
        model.complete([], [])


def test_from_file(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"turns": [{"final": "hi"}]}))
    assert ScriptedModel.from_file(path).complete([], []).final == "hi"
    assert ScriptedModel.from_file(str(path)).complete([], []).final == "hi"


def test_expect_passes_when_text_matches() -> None:
    model = ScriptedModel({"turns": [{"final": "ok", "expect": {"c1": "391"}}]})
    assert model.complete([Message("tool", "391", tool_call_id="c1")], []).final == "ok"


def test_expect_mismatch_names_id_expected_actual() -> None:
    model = ScriptedModel({"turns": [{"final": "ok", "expect": {"c1": "391"}}]})
    with pytest.raises(ScriptMismatch) as info:
        model.complete([Message("tool", "7", tool_call_id="c1")], [])
    text = str(info.value)
    assert "c1" in text and "391" in text and "7" in text


def test_expect_missing_message_is_mismatch() -> None:
    model = ScriptedModel({"turns": [{"final": "ok", "expect": {"c1": "391"}}]})
    with pytest.raises(ScriptMismatch):
        model.complete([Message("user", "q")], [])


@pytest.mark.parametrize(
    ("data", "index"),
    [
        ({"turns": [{"final": "a"}, {"final": "b", "tool_calls": [CALL]}]}, "turn 1"),
        ({"turns": [{"final": "a"}, {}]}, "turn 1"),
        ({"turns": [{"tool_calls": [{"id": "a", "name": "t"}]}]}, "turn 0"),
        (
            {"turns": [{"tool_calls": [{"name": "t", "arguments": {}, "id": 5}]}]},
            "turn 0",
        ),
        ({"turns": [{"tool_calls": []}]}, "turn 0"),
        ({"turns": [{"tool_calls": "x"}]}, "turn 0"),
        ({"turns": [{"tool_calls": ["x"]}]}, "turn 0"),
        ({"turns": [{"final": 3}]}, "turn 0"),
        ({"turns": ["x"]}, "turn 0"),
        ({"turns": [{"final": "a", "expect": {"c": 1}}]}, "turn 0"),
        ({"turns": [{"final": "a", "expect": "no"}]}, "turn 0"),
    ],
)
def test_malformed_script_names_turn(data: object, index: str) -> None:
    with pytest.raises(ValueError, match=index):
        ScriptedModel(data)


@pytest.mark.parametrize("data", [[], {}, {"turns": "x"}])
def test_malformed_top_level(data: object) -> None:
    with pytest.raises(ValueError, match="turns"):
        ScriptedModel(data)
