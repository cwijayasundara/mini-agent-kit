# Intent: opt-in Fireworks AI provider

Status: accepted (retroactive; records an intent that was built before this folder existed)

## Problem
The kit only runs against a scripted fake model, so nobody can see a real model drive the tools.

## Outcome
`demo --live` and `live` run the same agent loop against Fireworks AI, using `FIREWORKS_API_KEY`.

## Users and systems
Developers trying the kit; `fireworks.py`, `cli.py`.

## Constraints
- Default commands and all tests stay offline and key-free.
- Standard library only.
- Network access confined to one module (enforced by `tests/test_architecture.py`).

## Open questions
- Retry/backoff on provider errors (currently out of scope).

## Flow
intent (this file) → SPEC.md (Out of scope + provider note) → PLAN.md → code. New work starts here as `intent/NNN-name.md`.
