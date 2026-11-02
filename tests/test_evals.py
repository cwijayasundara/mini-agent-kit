"""Evals: real-task regression cases in evals/*.json, run end to end.

Add a case for every incident or bug: question, a script, the answer and stop_reason expected.
"""

import json
from pathlib import Path

import pytest

from mini_agent_kit.agent import run
from mini_agent_kit.scripted import ScriptedModel
from mini_agent_kit.toys import toy_registry

CASES = sorted((Path(__file__).resolve().parent.parent / "evals").glob("*.json"))


def test_there_are_evals() -> None:
    assert len(CASES) >= 20


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.stem)
def test_eval(case: Path) -> None:
    spec = json.loads(case.read_text())
    result = run(spec["question"], ScriptedModel(spec["script"]), toy_registry())
    assert (result.answer, result.stop_reason) == (spec["answer"], spec["stop_reason"])
