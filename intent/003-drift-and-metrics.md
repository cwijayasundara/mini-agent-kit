# Intent: scheduled drift job and DORA-style metrics

Status: accepted (built in the pending-items pass, tasks 16-18)

## Problem
`drift.py` needed a trace set and a schedule; `metrics.py` lacked plan-to-diff drift and delivery rates.

## Outcome
- `tools/eval_traces.py` regenerates a trace set from the offline evals; the weekly CI `drift` job runs it, runs `drift.py`, uploads the traces. Tier 2+ fails the job.
- `metrics.py` reports `plan_drift`, `deploys_per_week`, `fix_lag_hours`; lead time stays n/a until PRs exist.

- Item 9 follow-up: evals for model-failure stops (script exhausted, expectation mismatch, empty script) and bool passed as a string argument.

## Users and systems
The developer; `tools/`, `.github/workflows/ci.yml`.

## Constraints
- Offline and key-free; live traces still come from `tools/traced_run.py` into gitignored `traces/`.

## Open questions
- Real-model traces in CI need `FIREWORKS_API_KEY` and billing.
