"""Run evals/live/*.json against the real Fireworks model (opt-in; needs FIREWORKS_API_KEY).

Each case is {"question", "contains", optional "allow_tool_errors"}: the run must finish with a final answer containing
`contains`, and the trace sensor must report nothing. Traces are saved to traces/.
Usage: uv run python tools/live_evals.py
Exit 0 when every case passes.
"""

import sys
from pathlib import Path

from mini_agent_kit.agent import run
from mini_agent_kit.fireworks import FireworksModel
from mini_agent_kit.toys import toy_registry

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trace_sensor import findings


def check(case: dict[str, object], model: FireworksModel, out: Path) -> list[str]:
    """Run one case; return what went wrong (empty list means pass)."""
    result = run(str(case["question"]), model, toy_registry())
    out.write_text(result.to_json())
    problems = findings(result)
    if case.get("allow_tool_errors"):
        problems = [p for p in problems if "returned 'error: " not in p]
    if result.answer is None or str(case["contains"]) not in result.answer:
        problems.append(f"answer {result.answer!r} lacks {case['contains']!r}")
    return problems


def main() -> int:
    import json

    model = FireworksModel()
    Path("traces").mkdir(exist_ok=True)
    failed = 0
    for path in sorted(Path("evals/live").glob("*.json")):
        problems = check(
            json.loads(path.read_text()), model, Path("traces") / path.name
        )
        print(f"{'FAIL' if problems else 'PASS'} {path.stem}")
        for p in problems:
            print(f"  - {p}")
        failed += bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
