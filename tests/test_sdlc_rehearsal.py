"""The SDLC rehearsal passes on throwaway greenfield and brownfield repos (needs the factory checkout and node)."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

_tools = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(_tools))
_spec = importlib.util.spec_from_file_location(
    "sdlc_rehearsal", _tools / "sdlc_rehearsal.py"
)
assert _spec and _spec.loader
rehearsal = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rehearsal)

needs_factory = pytest.mark.skipif(
    shutil.which("node") is None or not rehearsal.FACTORY.exists(),
    reason="needs node and the lights_on_factory checkout",
)


def test_report_counts_only_failures() -> None:
    report = rehearsal.Report("x")
    report.add("1 plan", "a", True)
    report.add("1 plan", "b", None)
    report.add("1 plan", "c", False)
    assert report.failed == 1
    assert [row[2] for row in report.rows] == ["PASS", "SKIP", "FAIL"]


@needs_factory
@pytest.mark.parametrize("scenario", ["greenfield", "brownfield"])
def test_scenario_passes(scenario: str, tmp_path: Path) -> None:
    report = getattr(rehearsal, scenario)(
        tmp_path, *([False] if scenario == "greenfield" else [])
    )
    failures = [row for row in report.rows if row[2] == "FAIL"]
    assert failures == []
    assert sum(1 for row in report.rows if row[2] == "PASS") >= 20
