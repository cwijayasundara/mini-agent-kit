"""Maintain loop: turn trace-sensor findings into intent files.

Usage: uv run python tools/maintain.py <traces-dir> [intent-dir]
Scans every *.json trace, and for each trace with findings writes
`intent/NNN-trace-<name>.md` (once; existing intents are left alone) so the
problem enters the normal intent -> spec -> plan flow. Exit 1 if new intents were written.
"""

import re
import sys
from pathlib import Path

from mini_agent_kit.trace import RunResult

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trace_sensor import findings


def _next_number(intent_dir: Path) -> int:
    numbers = [
        int(m.group(1))
        for p in intent_dir.glob("*.md")
        if (m := re.match(r"(\d+)-", p.name))
    ]
    return max(numbers, default=0) + 1


def _intent_text(trace: Path, problems: list[str]) -> str:
    listed = "\n".join(f"- {p}" for p in problems)
    return (
        f"# Intent: fix agent behaviour seen in {trace.name}\n\n"
        "Status: proposed (written by tools/maintain.py)\n\n"
        f"## Problem\nThe trace sensor reported:\n{listed}\n\n"
        "## Outcome\nA run like this finishes with a final answer and no tool errors.\n\n"
        "## Open questions\n- Is the cause the tool description, the schema, or the model?\n"
    )


def maintain(traces: Path, intent_dir: Path) -> list[Path]:
    """Write one intent per problem trace not already recorded; return the new files."""
    intent_dir.mkdir(exist_ok=True)
    written = []
    for trace in sorted(traces.glob("*.json")):
        problems = findings(RunResult.from_json(trace.read_text()))
        if not problems or any(intent_dir.glob(f"*-trace-{trace.stem}.md")):
            continue
        path = intent_dir / f"{_next_number(intent_dir):03d}-trace-{trace.stem}.md"
        path.write_text(_intent_text(trace, problems))
        written.append(path)
    return written


def main(argv: list[str]) -> int:
    intent_dir = Path(argv[1]) if len(argv) > 1 else Path("intent")
    new = maintain(Path(argv[0]), intent_dir)
    for path in new:
        print(f"wrote {path}")
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
