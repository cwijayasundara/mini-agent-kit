# mini-agent-kit

Offline toolkit for tool-using agents. SPEC.md is the approved spec; PLAN.md the task list; DECISIONS.md records where the spec was silent.

## Verify (run before calling anything done)

```
uv run pytest -q
uv run ruff check --isolated src tests && uv run ruff format --isolated --check src tests
uv run mypy --strict --config-file .factory/gates/mypy.ini src
uv run mini-agent demo      # must print the four spec lines exactly
```

Full gate set (adds crap, dry, mutate) is in `.factory/build.json`. Healthy output: all green, demo exits 0.

## Architecture (enforced by `tests/test_architecture.py`)

`types` → `model`/`registry`/`trace`/`scripted`/`fireworks` → `toys`/`agent` → `cli`. A module imports only downward. Runtime is stdlib-only. Only `fireworks.py` touches the network, and tests never call it.

## Conventions

- Tool errors are returned as `ToolError`, never raised into the caller. Model failures end a run with `stop_reason="error"`; `run` does not raise.
- New module: add it to `ALLOWED` in `tests/test_architecture.py`.
- Spec silent? Pick the simplest reading, log it in DECISIONS.md.
- Write the failing test first. Never weaken a test to get green.
- Protected, do not edit: `.claude/`, `.factory/build.json`, `.factory/gates/`, `SPEC.md`.

## Recurring mistakes

Add a line here (and to LESSONS.md) whenever a correction repeats. Keep this file under a page.

## Other guides and sensors

- `REVIEW.md`: review passes and severity for any diff.
- `intent/`: start new work as `intent/NNN-name.md`, then SPEC → PLAN → code.
- `LESSONS.md`: log each recurring failure with the guide or sensor added.
- `tools/trace_sensor.py <trace.json>`: flags loops, tool errors and abnormal stops in a `--trace` file. Run it on traces from `mini-agent run --trace`.
- `evals/*.json`: end-to-end regression cases run by `tests/test_evals.py`. Add one for every bug or incident.
- `tools/traced_run.py` saves a trace to `traces/`; `tools/maintain.py traces` turns problem traces into `intent/` files.
