# Intent: local rehearsal of the full AI-native SDLC

Status: accepted (requested by the owner: test the whole harness locally, greenfield and brownfield, against the playbook)

## Problem
The harness was only proven on this repo, after the fact. We could not say whether a new project or an existing one gets the same guards, or whether each playbook stage has a gate that fires.

## Outcome
`tools/sdlc_rehearsal.py` builds a greenfield and a brownfield repo in a temp dir, installs build mode, and checks each stage's artifact and gate with the real hooks, including the full six-gate Stop hook.

## Users and systems
The developer; `tools/`, the factory installer, `.claude/hooks`.

## Constraints
- Offline: no CI, no network, no model.
- Proves the guards stop a non-compliant agent, not that a model follows the process.

## Open questions
- A live-model pass (an agent doing intent to merge in the temp repos) costs money and needs a decision.
- Policy skills, branch protection and rollback stay SKIP until they exist.
