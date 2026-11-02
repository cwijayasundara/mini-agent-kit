---
name: policy-security
description: Security rules for mini-agent-kit. Read before touching fireworks.py, tool code, traces, hooks or anything that handles credentials, network access or model output. Escalate anything in the "Ask first" list to the owner instead of deciding alone.
---

# Security policy

## Rules (must always hold)
1. Credentials come from the environment only (`FIREWORKS_API_KEY`), are read in `fireworks.py` only, and are never written into code, logs, traces, errors or test fixtures. The only place the key is formatted into text is the `Authorization` header.
2. Only `fireworks.py` touches the network. Tests never call it.
3. The runtime never runs dynamic code: no `eval`, `exec`, `compile`, `__import__`; no `subprocess`, `pickle`, `marshal`, `shelve`, `ctypes`.
4. Tools do only what their arguments say. A tool never reads files, environment variables or the network on its own; a tool error is returned as `ToolError`, never raised and never containing internals.
5. Model output is untrusted input: tool arguments are validated against the schema before a tool runs, and a bad call becomes a `ToolError`.
6. Traces may contain prompts and tool results. Treat a saved trace as sensitive; `traces/` stays gitignored.

## Ask first (stop and record in BLOCKED.md or ask the owner)
- Any new module that opens a socket, reads files outside the project, or starts a process.
- Any change to `.claude/`, hooks, deny rules or gates.
- Adding a dependency of any kind.

## Enforced by
- Rule 1: `.claude/hooks/secret-guard.mjs` (edits), gitleaks (history), `tests/test_policy.py::test_api_key_is_only_read_in_fireworks_and_never_formatted_into_text`.
- Rule 2: `tests/test_architecture.py` (network modules).
- Rule 3: `tests/test_policy.py` (forbidden calls and imports) and semgrep in CI.
- Rule 4 and 5: `tests/test_registry_call.py` and the failure-path evals in `evals/`.
- Rule 6: `.gitignore`.
- "Ask first": protect-paths hook and the Stop hook's protected-diff check.
