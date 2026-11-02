# Intent: branch protection and AI PR review

Status: accepted (requested by the owner; closes pending item 3)

## Problem
Everything went straight to `main`: no review gate, no separation between the agent that writes and the owner who approves, and REVIEW.md was only read when someone remembered.

## Outcome
- `main` requires a pull request, one code-owner approval, passing `verify` and `security` checks and resolved conversations; force pushes and deletions are blocked.
- Every same-repo PR gets one AI review comment against REVIEW.md. The review never approves or blocks.

## Users and systems
The owner, build agents, reviewers; `.github/`, GitHub branch protection.

## Constraints
- The reviewer runs on Sonnet, read-only plus one PR comment, pinned action, no `pull_request_target`.
- The API key is a repository secret the owner sets; it is never typed into a session or committed.
- Admin bypass stays on (solo owner cannot approve their own PR). An agent using the owner's token can therefore still push to main; real separation needs a separate agent identity.

## Open questions
- CI is locked by billing, so the required checks will not report until the lock is lifted; the owner merges by bypass meanwhile.
- A second human or a dedicated bot account would make separation of duties real.
