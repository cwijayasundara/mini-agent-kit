"""eval_traces.py turns the offline evals into a trace directory that drift.py can read."""

import importlib.util
import sys
from pathlib import Path

_tools = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(_tools))
_spec = importlib.util.spec_from_file_location("eval_traces", _tools / "eval_traces.py")
assert _spec and _spec.loader
eval_traces = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eval_traces)

EVALS = _tools.parent / "evals"


def test_writes_one_trace_per_eval_in_sorted_name_order(tmp_path: Path) -> None:
    written = eval_traces.write_traces(EVALS, tmp_path)
    names = sorted(p.name for p in tmp_path.glob("*.json"))
    assert len(written) == len(list(EVALS.glob("*.json"))) == len(names)
    assert names == sorted(p.name for p in written)


def test_main_returns_zero_and_reports_count(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    assert eval_traces.main([str(EVALS), str(tmp_path)]) == 0
    assert "wrote" in capsys.readouterr().out
