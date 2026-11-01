"""The agent loop."""

import time
from collections.abc import Callable

from mini_agent_kit.model import Model
from mini_agent_kit.registry import Registry
from mini_agent_kit.trace import RunResult, Step, ToolResult
from mini_agent_kit.types import Message, ToolCall, ToolError


def result_text(result: object) -> str:
    """Render a tool result as the text a tool message carries."""
    if isinstance(result, ToolError):
        return f"error: {result.message}"
    return str(result)


def _run_calls(
    calls: tuple[ToolCall, ...], registry: Registry
) -> tuple[tuple[ToolResult, ...], list[Message]]:
    """Run calls in order; return their results and the matching tool messages."""
    results = []
    messages = []
    for c in calls:
        text = result_text(registry.call(c.name, c.arguments))
        results.append(ToolResult(c.name, c.arguments, text))
        messages.append(Message("tool", text, tool_call_id=c.id))
    return tuple(results), messages


def run(
    question: str,
    model: Model,
    registry: Registry,
    max_steps: int = 8,
    clock: Callable[[], float] = time.perf_counter,
) -> RunResult:
    """Ask the model until it gives a final answer, errors, or hits max_steps."""
    messages = [Message("user", question)]
    tools = registry.schemas()
    steps: list[Step] = []
    for _ in range(max_steps):
        start = clock()
        sent = tuple(messages)
        try:
            reply = model.complete(list(messages), tools)
        except Exception as exc:  # noqa: BLE001 - any model failure ends the run
            steps.append(Step(sent, None, (), (clock() - start) * 1000, str(exc)))
            return RunResult(None, tuple(steps), "error")
        results, tool_messages = _run_calls(reply.tool_calls, registry)
        steps.append(Step(sent, reply, results, (clock() - start) * 1000))
        if reply.final is not None:
            return RunResult(reply.final, tuple(steps), "final")
        messages.append(Message("assistant", tool_calls=reply.tool_calls))
        messages.extend(tool_messages)
    return RunResult(None, tuple(steps), "max_steps")
