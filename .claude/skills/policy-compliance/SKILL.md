---
name: policy-compliance
description: Dependency, licensing, data-handling and auditability rules for mini-agent-kit. Read before adding a dependency, copying code, saving traces, changing the provider, or editing the plan, spec or decision records.
---

# Compliance policy

## Rules (must always hold)
1. The runtime is standard-library only. Dev-only tools (pytest, ruff, mypy, coverage) may be added to the `dev` group; nothing else.
2. No copied third-party code. Anything not written here needs its license recorded in DECISIONS.md and the owner's approval first.
3. User text sent to the live provider leaves the machine. `demo` and all tests stay offline; `--live` is explicit opt-in, and the README says so.
4. Saved traces are records of runs: they are never edited, and they hold no credentials (see policy-security).
5. The audit chain is intent -> SPEC.md -> PLAN.md -> commits. Every `feat` commit maps to a PLAN task (`done: <sha>`), every spec-silent choice is logged in DECISIONS.md, every recurring failure in LESSONS.md.
6. Spec, hooks and gates are changed only by the owner. An agent that needs one changed records the need and stops.

## Ask first
- Any new runtime dependency, vendored file or generated asset with unclear license.
- Sending any new kind of data to the provider (files, environment values, traces).
- Changing retention: committing traces, logs or evals that contain real model output.

## Enforced by
- Rule 1: `tests/test_policy.py::test_runtime_has_no_third_party_dependencies`.
- Rule 3: `tests/test_architecture.py` and `tests/test_cli.py` (offline default).
- Rule 5: `tools/metrics.py` `plan_drift` (feat commits missing from PLAN.md) and the Stop hook's plan lock.
- Rule 6: protect-paths hook and the Stop hook's protected-diff check.
- Rule 2 has no mechanical check; it relies on review (REVIEW.md pass 3).
