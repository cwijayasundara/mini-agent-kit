"""The maintain loop turns problem traces into intent files, once each."""

import importlib.util
import sys
from pathlib import Path

from mini_agent_kit.agent import run
from mini_agent_kit.registry import Registry
from mini_agent_kit.scripted import ScriptedModel

_tools = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(_tools))
_spec = importlib.util.spec_from_file_location("maintain", _tools / "maintain.py")
assert _spec and _spec.loader
maintain = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(maintain)


def _write(path: Path, turns: list[dict[str, object]]) -> None:
    path.write_text(run("q", ScriptedModel({"turns": turns}), Registry()).to_json())


def test_problem_trace_becomes_one_numbered_intent(tmp_path: Path) -> None:
    traces, intent = tmp_path / "t", tmp_path / "i"
    traces.mkdir()
    intent.mkdir()
    (intent / "007-old.md").write_text("x")
    _write(traces / "bad.json", [])
    _write(traces / "good.json", [{"final": "ok"}])
    written = maintain.maintain(traces, intent)
    assert [p.name for p in written] == ["008-trace-bad.md"]
    assert "model error" in written[0].read_text()
    assert maintain.maintain(traces, intent) == []


def test_main_exit_code_and_default_intent_dir(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    traces = tmp_path / "t"
    traces.mkdir()
    _write(traces / "good.json", [{"final": "ok"}])
    assert maintain.main([str(traces)]) == 0
    _write(traces / "bad.json", [])
    assert maintain.main([str(traces)]) == 1
    assert (tmp_path / "intent" / "001-trace-bad.md").exists()
