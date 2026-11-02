"""The drift detector picks a response tier from recent versus baseline failure rates."""

import importlib.util
import json
import sys
from pathlib import Path

from mini_agent_kit.agent import run
from mini_agent_kit.registry import Registry
from mini_agent_kit.scripted import ScriptedModel

_tools = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(_tools))
_spec = importlib.util.spec_from_file_location("drift", _tools / "drift.py")
assert _spec and _spec.loader
drift = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(drift)

CONFIG = json.loads((_tools / "drift.json").read_text())


def _traces(directory: Path, pattern: str) -> None:
    """One trace per character: 'g' is a clean run, 'b' a model error."""
    directory.mkdir(exist_ok=True)
    for i, kind in enumerate(pattern):
        turns = [{"final": "ok"}] if kind == "g" else []
        result = run("q", ScriptedModel({"turns": turns}), Registry())
        (directory / f"{i:03d}.json").write_text(result.to_json())


def test_pick_tier_uses_rate_or_delta() -> None:
    tiers = CONFIG["tiers"]
    assert drift.pick_tier(0.0, 0.0, tiers) == 0
    assert drift.pick_tier(0.2, 0.2, tiers) == 1  # rate alone
    assert drift.pick_tier(0.15, 0.0, tiers) == 1  # delta alone
    assert drift.pick_tier(0.4, 0.4, tiers) == 2
    assert drift.pick_tier(0.6, 0.6, tiers) == 3
    assert drift.pick_tier(0.5, 0.0, tiers) == 3  # delta 0.5 >= 0.4


def test_too_few_traces_does_nothing(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    _traces(tmp_path / "t", "ggg")
    assert drift.check(tmp_path / "t", CONFIG, tmp_path / "i") == 0
    assert "not enough traces" in capsys.readouterr().out


def test_healthy_traces_stay_within_bands(tmp_path: Path) -> None:
    _traces(tmp_path / "t", "gggggggggg")
    assert drift.check(tmp_path / "t", CONFIG, tmp_path / "i") == 0


def test_diagnose_tier_is_read_only(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    _traces(tmp_path / "t", "bbgggggbbg")
    assert drift.check(tmp_path / "t", CONFIG, tmp_path / "i") == 2
    assert "model error" in capsys.readouterr().out
    assert not (tmp_path / "i").exists()


def test_propose_tier_writes_intents(tmp_path: Path) -> None:
    _traces(tmp_path / "t", "ggggggbbbb")
    assert drift.check(tmp_path / "t", CONFIG, tmp_path / "i") == 3
    assert len(list((tmp_path / "i").glob("*.md"))) == 4


def test_main_returns_the_tier(tmp_path: Path) -> None:
    _traces(tmp_path / "t", "ggggggbbbb")
    assert (
        drift.main(
            [str(tmp_path / "t"), str(_tools / "drift.json"), str(tmp_path / "i")]
        )
        == 3
    )
