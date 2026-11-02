"""Trace sensor: read a `mini-agent run --trace` file and report agent misbehaviour.

Usage: uv run python tools/trace_sensor.py trace.json [more.json ...]
Exit 0 when every trace is clean, 1 when any finding is reported.
Each finding says what happened and what to change.
"""

import sys
from collections import Counter
from pathlib import Path

from mini_agent_kit.trace import RunResult

REPEAT_LIMIT = 3


def findings(result: RunResult) -> list[str]:
    """Return the problems a run's trace shows, as fix-oriented messages."""
    out: list[str] = []
    if result.stop_reason == "max_steps":
        out.append(
            f"hit max_steps after {len(result.steps)} steps without an answer: "
            "raise max_steps, or make the tool descriptions clearer"
        )
    if result.stop_reason == "error":
        last = result.steps[-1].error if result.steps else None
        out.append(f"model error ended the run ({last}): check the model and script")
    calls = Counter(
        (r.name, repr(sorted(r.arguments.items())))
        for step in result.steps
        for r in step.tool_results
    )
    for (name, _), count in calls.items():
        if count >= REPEAT_LIMIT:
            out.append(
                f"{name} was called {count} times with identical arguments: "
                "the agent is looping; check that the tool result answers the question"
            )
    errors = [
        r
        for step in result.steps
        for r in step.tool_results
        if r.result.startswith("error: ")
    ]
    for r in errors:
        out.append(
            f"{r.name} returned '{r.result}': fix the arguments or the tool schema"
        )
    return out


def main(argv: list[str]) -> int:
    bad = 0
    for name in argv:
        result = RunResult.from_json(Path(name).read_text())
        for finding in findings(result):
            print(f"{name}: {finding}")
            bad = 1
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
