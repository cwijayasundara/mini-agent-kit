import json
from pathlib import Path

import pytest

from mini_agent_kit.cli import main
from mini_agent_kit.trace import RunResult

DEMO_OUTPUT = """\
question: What is 17 * 23, and how many words are in 'the quick brown fox'?
step 1: calculator({"expression": "17 * 23"}) -> 391
step 2: word_count({"text": "the quick brown fox"}) -> 4
answer: 391; 4 words
"""


def test_demo_prints_exact_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demo"]) == 0
    assert capsys.readouterr().out == DEMO_OUTPUT


def write(tmp_path: Path, turns: list[object]) -> Path:
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"turns": turns}))
    return path


def test_run_final_writes_trace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    script = write(tmp_path, [{"final": "hello"}])
    trace = tmp_path / "t.json"
    code = main(["run", "--script", str(script), "--trace", str(trace), "hi"])
    assert code == 0
    assert capsys.readouterr().out == "question: hi\nanswer: hello\n"
    assert RunResult.from_json(trace.read_text()).answer == "hello"


def test_run_max_steps_exit_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    call = {"id": "c", "name": "word_count", "arguments": {"text": "a b"}}
    script = write(tmp_path, [{"tool_calls": [call]}] * 9)
    assert main(["run", "--script", str(script), "q"]) == 1
    out = capsys.readouterr().out
    assert "step 8: word_count" in out and "step 9" not in out
    assert out.endswith("stopped: max_steps reached without an answer\n")


def test_run_error_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script = write(tmp_path, [])
    assert main(["run", "--script", str(script), "q"]) == 2
    assert capsys.readouterr().out.startswith("question: q\nerror: ")


def test_run_without_trace_writes_nothing(tmp_path: Path) -> None:
    script = write(tmp_path, [{"final": "x"}])
    main(["run", "--script", str(script), "q"])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["s.json"]


def test_run_requires_script() -> None:
    with pytest.raises(SystemExit) as info:
        main(["run", "q"])
    assert info.value.code == 2


def test_error_after_tool_call_reports_last_step_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    call = {"id": "c", "name": "word_count", "arguments": {"text": "a b"}}
    script = write(tmp_path, [{"tool_calls": [call]}])
    assert main(["run", "--script", str(script), "q"]) == 2
    assert "error: script has only 1 turns" in capsys.readouterr().out


def test_command_is_required() -> None:
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code == 2
