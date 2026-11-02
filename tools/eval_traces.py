"""Run every offline eval and save its trace, giving drift.py a trace set CI can produce without a model.

Usage: uv run python tools/eval_traces.py [evals-dir] [out-dir]   (defaults: evals, traces-ci)
"""

import json
import sys
from pathlib import Path

from mini_agent_kit.agent import run
from mini_agent_kit.scripted import ScriptedModel
from mini_agent_kit.toys import toy_registry


def write_traces(evals: Path, out: Path) -> list[Path]:
    """Run each evals/*.json case and write its trace to out/<name>.json; return the paths."""
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for case in sorted(evals.glob("*.json")):
        spec = json.loads(case.read_text())
        result = run(spec["question"], ScriptedModel(spec["script"]), toy_registry())
        path = out / case.name
        path.write_text(result.to_json())
        written.append(path)
    return written


def main(argv: list[str]) -> int:
    evals = Path(argv[0]) if argv else Path("evals")
    out = Path(argv[1]) if len(argv) > 1 else Path("traces-ci")
    print(f"wrote {len(write_traces(evals, out))} traces to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
