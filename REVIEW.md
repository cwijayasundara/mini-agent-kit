# Review guide

Used by humans and AI reviewers on any diff to this repo. Three passes, in order.

1. **Bugs.** Wrong behaviour against SPEC.md; unhandled errors that should become `ToolError` or `stop_reason="error"`; tests that would still pass if the code returned nothing.
2. **Security.** Credentials in code, logs or traces; network access outside `fireworks.py`; `eval`/`exec`; tool code reaching beyond its arguments.
3. **Spec and plan.** Does the diff match SPEC.md and the relevant PLAN.md task? Is every spec-silent choice logged in DECISIONS.md? Does the layering in CLAUDE.md still hold?

Severity: **blocker** (wrong behaviour, leak, weakened test), **should-fix** (missing test, unclear error text), **nit** (style; report at most 3).
Do not comment on formatting or anything ruff, mypy or the gates already enforce.
