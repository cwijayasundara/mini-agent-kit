# Intent: harness guides, sensors and the maintain loop

Status: accepted (retroactive; built in 45ba6e7, ae33ef1, 5b8b3af, da88328, 9e2c12b before this folder was used for it)

## Problem
Gates prove the code is right today. Nothing told us when agent behaviour regresses, when a failure repeats, or whether the build process itself is healthy.

## Outcome
- Guides: CLAUDE.md, REVIEW.md, LESSONS.md, `intent/`.
- Sensors: `tools/trace_sensor.py` (one trace), `tools/drift.py` (trace set over time), `tools/metrics.py` (git/plan health), evals (offline `evals/`, opt-in `evals/live/`).
- Loop: `tools/maintain.py` turns problem traces into `intent/` files; CI runs it weekly.

## Users and systems
The developer and the build agent; `tools/`, `evals/`, `.github/workflows/ci.yml`, hooks under `.claude/`.

## Constraints
- Tools are stdlib plus the kit itself; no runtime dependency added.
- Existing tests and evals are frozen during a bug fix (`.fix-mode` hook).
- Nothing here changes `src/` behaviour.

## Open questions
- Should the kit also become a harness for other agents (tool risk levels, approval hooks)?
- Drift on scripted evals only detects regressions in the loop, not model drift; real drift needs saved live traces.

## Flow
intent (this file) → PLAN.md tasks 13-15 → code.
