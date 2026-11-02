"""Drift detector: compare recent trace failure rate with the earlier baseline and pick a response tier.

Usage: uv run python tools/drift.py <traces-dir> [config.json] [intent-dir]
Traces are ordered by file name (traced_run.py names them by timestamp). The `window` newest traces
are "recent"; everything older is the baseline. Thresholds live in tools/drift.json, version-controlled.
Tiers escalate: log -> diagnose (read-only) -> propose (writes intent files). Exit code is the tier index
(0 = none, 1 = log, 2 = diagnose, 3 = propose).
"""

import json
import sys
from pathlib import Path

from maintain import maintain
from trace_sensor import findings

from mini_agent_kit.trace import RunResult

DEFAULT_CONFIG = Path(__file__).resolve().parent / "drift.json"


def _failures(paths: list[Path]) -> list[list[str]]:
    return [findings(RunResult.from_json(p.read_text())) for p in paths]


def _rate(results: list[list[str]]) -> float:
    return sum(1 for r in results if r) / len(results) if results else 0.0


def pick_tier(recent: float, baseline: float, tiers: list[dict[str, object]]) -> int:
    """Index (1-based) of the highest tier whose rate or delta threshold is met; 0 if none."""
    chosen = 0
    for index, tier in enumerate(tiers, start=1):
        if recent >= float(str(tier["rate"])) or recent - baseline >= float(
            str(tier["delta"])
        ):
            chosen = index
    return chosen


def check(traces: Path, config: dict[str, object], intent_dir: Path) -> int:
    """Run the detector; print what it did and return the tier index."""
    paths = sorted(traces.glob("*.json"))
    window = int(str(config["window"]))
    if len(paths) < window + int(str(config["min_baseline"])):
        print(
            f"not enough traces ({len(paths)}); need {window} recent + {config['min_baseline']} baseline"
        )
        return 0
    recent, older = _failures(paths[-window:]), _failures(paths[:-window])
    recent_rate, baseline_rate = _rate(recent), _rate(older)
    tiers = list(config["tiers"])  # type: ignore[call-overload]
    tier = pick_tier(recent_rate, baseline_rate, tiers)
    print(f"recent failure rate {recent_rate:.2f}, baseline {baseline_rate:.2f}")
    if tier == 0:
        print("within bands")
        return 0
    print(f"tier {tier}: {tiers[tier - 1]['name']}")
    if tier >= 2:
        for path, problems in zip(paths[-window:], recent, strict=True):
            for problem in problems:
                print(f"  {path.name}: {problem}")
    if tier >= 3:
        for written in maintain(traces, intent_dir):
            print(f"wrote {written}")
    return tier


def main(argv: list[str]) -> int:
    config = json.loads(Path(argv[1] if len(argv) > 1 else DEFAULT_CONFIG).read_text())
    intent_dir = Path(argv[2]) if len(argv) > 2 else Path("intent")
    return check(Path(argv[0]), config, intent_dir)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main(sys.argv[1:]))
