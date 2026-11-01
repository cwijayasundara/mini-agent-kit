"""The mini-agent command line."""

import argparse
import json
from collections.abc import Sequence
from importlib import resources
from pathlib import Path

from mini_agent_kit.agent import run
from mini_agent_kit.scripted import ScriptedModel
from mini_agent_kit.toys import toy_registry
from mini_agent_kit.trace import RunResult

DEMO_QUESTION = "What is 17 * 23, and how many words are in 'the quick brown fox'?"
EXIT_CODES = {"final": 0, "max_steps": 1, "error": 2}


def render(question: str, result: RunResult) -> str:
    """The printed transcript of a run."""
    lines = [f"question: {question}"]
    for number, step in enumerate(result.steps, start=1):
        lines.extend(
            f"step {number}: {r.name}({json.dumps(r.arguments)}) -> {r.result}"
            for r in step.tool_results
        )
    if result.stop_reason == "final":
        lines.append(f"answer: {result.answer}")
    elif result.stop_reason == "error":
        lines.append(f"error: {result.steps[-1].error}")
    else:
        lines.append("stopped: max_steps reached without an answer")
    return "\n".join(lines)


def _execute(script: Path, question: str, trace: str | None) -> int:
    result = run(question, ScriptedModel.from_file(script), toy_registry())
    print(render(question, result))
    if trace is not None:
        Path(trace).write_text(result.to_json())
    return EXIT_CODES[result.stop_reason]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mini-agent")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="run the bundled demo script")
    run_cmd = commands.add_parser("run", help="run a script with the toy tools")
    run_cmd.add_argument("--script", required=True, type=Path)
    run_cmd.add_argument("--trace", help="write the run trace JSON here")
    run_cmd.add_argument("question")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "demo":
        demo = resources.files("mini_agent_kit") / "scripts" / "demo.json"
        with resources.as_file(demo) as path:
            return _execute(path, DEMO_QUESTION, None)
    return _execute(args.script, args.question, args.trace)
