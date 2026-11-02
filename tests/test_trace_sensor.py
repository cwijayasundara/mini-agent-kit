"""The trace sensor flags loops, tool errors and abnormal stops."""

import importlib.util
from pathlib import Path

from mini_agent_kit.agent import run
from mini_agent_kit.registry import Registry
from mini_agent_kit.scripted import ScriptedModel

_spec = importlib.util.spec_from_file_location(
    "trace_sensor", Path(__file__).resolve().parent.parent / "tools" / "trace_sensor.py"
)
assert _spec and _spec.loader
sensor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sensor)


def _registry() -> Registry:
    registry = Registry()

    @registry.tool
    def ping(n: int) -> str:
        """Echo n."""
        return str(n)

    return registry


def _call(i: int, n: int = 1) -> dict[str, object]:
    return {"tool_calls": [{"id": f"c{i}", "name": "ping", "arguments": {"n": n}}]}


def test_clean_run_has_no_findings() -> None:
    model = ScriptedModel({"turns": [_call(1), {"final": "ok"}]})
    assert sensor.findings(run("q", model, _registry())) == []


def test_repeated_identical_calls_are_a_loop() -> None:
    model = ScriptedModel({"turns": [_call(1), _call(2), _call(3), {"final": "ok"}]})
    found = sensor.findings(run("q", model, _registry()))
    assert len(found) == 1 and "ping was called 3 times" in found[0]


def test_different_arguments_are_not_a_loop() -> None:
    turns = [_call(1, 1), _call(2, 2), _call(3, 3), {"final": "ok"}]
    assert sensor.findings(run("q", ScriptedModel({"turns": turns}), _registry())) == []


def test_max_steps_is_reported() -> None:
    model = ScriptedModel({"turns": [_call(1, 1), _call(2, 2)]})
    found = sensor.findings(run("q", model, _registry(), max_steps=2))
    assert len(found) == 1 and "hit max_steps after 2 steps" in found[0]


def test_model_error_is_reported() -> None:
    found = sensor.findings(run("q", ScriptedModel({"turns": []}), _registry()))
    assert len(found) == 1 and "model error" in found[0]


def test_tool_error_is_reported() -> None:
    bad = {"tool_calls": [{"id": "c1", "name": "nope", "arguments": {}}]}
    model = ScriptedModel({"turns": [bad, {"final": "ok"}]})
    found = sensor.findings(run("q", model, _registry()))
    assert len(found) == 1 and "error: unknown tool: nope" in found[0]


def test_main_exit_code_follows_findings(tmp_path: Path) -> None:
    clean = run("q", ScriptedModel({"turns": [{"final": "ok"}]}), _registry())
    stuck = run("q", ScriptedModel({"turns": []}), _registry())
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(clean.to_json())
    b.write_text(stuck.to_json())
    assert sensor.main([str(a)]) == 0
    assert sensor.main([str(a), str(b)]) == 1
