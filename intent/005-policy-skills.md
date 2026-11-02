# Intent: policy skills for security, compliance and CLI UX

Status: accepted (requested by the owner after the SDLC rehearsal flagged "policy skills: none exist")

## Problem
The playbook's design stage wants security, compliance and UX policy encoded as skills that constrain the spec and the build. None existed, so those rules lived only in people's heads and scattered tests.

## Outcome
Three skills (`policy-security`, `policy-compliance`, `policy-cli-ux`), each with rules, an "Ask first" list and an "Enforced by" section, plus `tests/test_policy.py` as the hook behind the rules that must always hold.

## Users and systems
Build agents and reviewers; `.claude/skills/`, `CLAUDE.md`, `tests/`.

## Constraints
- Skills are advisory; anything that must always hold needs a test or hook (the "Enforced by" section says which).
- `.claude/` is protected, so the skills enter through the installer's re-install commit.

## Open questions
- Brand policy does not apply (no UI). Revisit if the kit grows a front end.
- Rules 2 (compliance) and the UX style rules have no mechanical check yet.
