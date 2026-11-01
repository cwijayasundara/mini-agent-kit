from mini_agent_kit.agent import run
from mini_agent_kit.registry import Registry
from mini_agent_kit.scripted import ScriptedModel
from mini_agent_kit.types import Message, ModelReply, ToolSchema


def registry() -> Registry:
    reg = Registry()

    @reg.tool
    def add(a: int, b: int) -> int:
        """Add."""
        return a + b

    return reg


def call(cid: str, name: str, **arguments: object) -> dict[str, object]:
    return {"id": cid, "name": name, "arguments": arguments}


def test_final_answer_directly() -> None:
    result = run("hi", ScriptedModel({"turns": [{"final": "yo"}]}), registry())
    assert (result.answer, result.stop_reason, len(result.steps)) == ("yo", "final", 1)
    assert result.steps[0].messages == (Message("user", "hi"),)
    assert result.steps[0].duration_ms >= 0


def test_tool_call_then_final_with_expectation() -> None:
    script = {
        "turns": [
            {"tool_calls": [call("c1", "add", a=2, b=3), call("c2", "add", a=1, b=1)]},
            {"final": "five", "expect": {"c1": "5", "c2": "2"}},
        ]
    }
    result = run("sum", ScriptedModel(script), registry())
    assert result.answer == "five" and result.stop_reason == "final"
    first = result.steps[0]
    assert [(r.name, r.arguments, r.result) for r in first.tool_results] == [
        ("add", {"a": 2, "b": 3}, "5"),
        ("add", {"a": 1, "b": 1}, "2"),
    ]
    second = result.steps[1].messages
    assert [m.role for m in second] == ["user", "assistant", "tool", "tool"]
    assert second[1].tool_calls == first.reply.tool_calls  # type: ignore[union-attr]
    assert [m.tool_call_id for m in second[2:]] == ["c1", "c2"]


def test_tool_error_becomes_error_text() -> None:
    script = {
        "turns": [
            {"tool_calls": [call("c1", "nope")]},
            {"final": "ok", "expect": {"c1": "error: unknown tool: nope"}},
        ]
    }
    assert run("q", ScriptedModel(script), registry()).stop_reason == "final"


def test_max_steps_counts_model_calls() -> None:
    loop = {"tool_calls": [call("c", "add", a=1, b=1)]}
    result = run("q", ScriptedModel({"turns": [loop] * 5}), registry(), max_steps=3)
    assert (result.answer, result.stop_reason, len(result.steps)) == (
        None,
        "max_steps",
        3,
    )


def test_final_on_last_allowed_step_succeeds() -> None:
    loop = {"tool_calls": [call("c", "add", a=1, b=1)]}
    result = run(
        "q", ScriptedModel({"turns": [loop, {"final": "x"}]}), registry(), max_steps=2
    )
    assert result.stop_reason == "final"


def test_zero_max_steps() -> None:
    result = run(
        "q", ScriptedModel({"turns": [{"final": "x"}]}), registry(), max_steps=0
    )
    assert (result.stop_reason, result.steps) == ("max_steps", ())


def test_script_mismatch_ends_run_with_error() -> None:
    script = {
        "turns": [
            {"tool_calls": [call("c1", "add", a=1, b=1)]},
            {"final": "x", "expect": {"c1": "99"}},
        ]
    }
    result = run("q", ScriptedModel(script), registry())
    assert (result.answer, result.stop_reason) == (None, "error")
    assert result.steps[-1].error is not None and "99" in result.steps[-1].error
    assert result.steps[-1].reply is None


def test_script_exhausted_ends_run_with_error() -> None:
    loop = {"tool_calls": [call("c", "add", a=1, b=1)]}
    result = run("q", ScriptedModel({"turns": [loop]}), registry())
    assert result.stop_reason == "error" and result.steps[-1].error


def test_model_sees_tool_schemas() -> None:
    seen: list[list[ToolSchema]] = []

    class Spy:
        def complete(
            self, messages: list[Message], tools: list[ToolSchema]
        ) -> ModelReply:
            seen.append(tools)
            return ModelReply(final="x")

    run("q", Spy(), registry())
    assert [t["name"] for t in seen[0]] == ["add"]


def test_duration_is_clock_difference_in_milliseconds() -> None:
    ticks = iter([1.0, 1.25])
    result = run(
        "q",
        ScriptedModel({"turns": [{"final": "x"}]}),
        registry(),
        clock=lambda: next(ticks),
    )
    assert result.steps[0].duration_ms == 250.0


def test_error_step_has_duration() -> None:
    ticks = iter([2.0, 2.5])
    result = run(
        "q", ScriptedModel({"turns": []}), registry(), clock=lambda: next(ticks)
    )
    assert result.steps[0].duration_ms == 500.0
