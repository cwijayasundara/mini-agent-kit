---
name: policy-cli-ux
description: Command-line experience rules for mini-agent-kit. Read before changing cli.py output, error messages, exit codes, the demo script, or README examples.
---

# CLI and error-message UX policy

## Rules (must always hold)
1. `mini-agent demo` prints the four spec lines exactly, offline, and exits 0. Its shape is `question:`, one `step N:` line per tool call, then `answer:`.
2. Output goes to stdout in a stable, greppable shape; a human reads it top to bottom without a legend. No color, no spinners, no timestamps in default output.
3. Every error message names what was wrong and what to change (`set FIREWORKS_API_KEY to use the live model`, not `auth failed`).
4. Exit codes: 0 success, nonzero when the run ends in `stop_reason="error"` or the arguments are invalid. Never exit 0 on a failure.
5. A tool error reaches the model as `error: <what and why>` text, so the model can recover; it is never a stack trace.
6. README examples are runnable as written. If a command or output changes, the README changes in the same commit.

## Ask first
- Renaming a command or flag, or changing the demo's output (SPEC.md is protected; the owner approves).
- Adding interactive prompts: the kit is non-interactive by design.

## Enforced by
- Rule 1: `tests/test_policy.py::test_demo_output_is_the_four_spec_lines`, `tests/test_cli.py`, and the demo gate in `.factory/build.json`.
- Rule 3 and 5: failure-path evals in `evals/` assert the exact error text.
- Rule 4: `tests/test_cli.py`.
- Rules 2 and 6 have no mechanical check; they rely on review (REVIEW.md pass 3).
