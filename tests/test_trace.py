from mini_agent_kit.agent import run
from mini_agent_kit.registry import Registry
from mini_agent_kit.scripted import ScriptedModel
from mini_agent_kit.trace import RunResult


def registry() -> Registry:
    reg = Registry()

    @reg.tool
    def add(a: int, b: int) -> int:
        """Add."""
        return a + b

    return reg


def test_round_trip_with_tool_calls() -> None:
    script = {
        "turns": [
            {
                "tool_calls": [
                    {"id": "c1", "name": "add", "arguments": {"a": 1, "b": 2}}
                ]
            },
            {"final": "three"},
        ]
    }
    result = run("sum?", ScriptedModel(script), registry())
    assert RunResult.from_json(result.to_json()) == result


def test_round_trip_with_error_run() -> None:
    result = run("q", ScriptedModel({"turns": []}), registry())
    restored = RunResult.from_json(result.to_json())
    assert restored == result
    assert restored.stop_reason == "error" and restored.steps[0].reply is None


def test_round_trip_max_steps() -> None:
    loop = {"tool_calls": [{"id": "c", "name": "add", "arguments": {"a": 1, "b": 1}}]}
    result = run("q", ScriptedModel({"turns": [loop] * 3}), registry(), max_steps=2)
    assert RunResult.from_json(result.to_json()) == result


def test_durations_stay_numbers() -> None:
    result = run(
        "q",
        ScriptedModel({"turns": [{"final": "x"}]}),
        registry(),
        clock=iter([0.0, 0.5]).__next__,
    )
    assert RunResult.from_json(result.to_json()).steps[0].duration_ms == 500.0
