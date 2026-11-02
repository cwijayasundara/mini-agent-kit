# SDLC gap analysis

Compares mini-agent-kit's harness (as of install commit `92f4e74`) with the stages of the [AI-native SDLC playbook](https://claude.com/resources/articles/the-ai-native-sdlc-playbook). Related references: Martin Fowler's [harness engineering](https://martinfowler.com/articles/harness-engineering.html) and [sensors for coding agents](https://martinfowler.com/articles/sensors-for-coding-agents.html).

## Verification state

- All six gates and the demo pass against `.factory/build.json`: tests (142), lint, types, crap, dry, mutate (every mutant killed).
- The build-mode Stop hook run from a fresh clone of GitHub exits 0 with `decision: allow` and a `COMPLETE` header.
- Hooks (secret guard, post-edit ruff, fix-mode guard, protect-paths) fired in a live session.
- Live-model evals (4 cases, Fireworks) pass.
- Since then: 22 offline evals, gitleaks and semgrep (clean locally, jobs added to CI), `tools/drift.py` with response tiers, and rework and CI-pass metrics.
- Not tested: the CI workflow on GitHub (account billing lock), the `shape` skill, and the weakening check.
- `BUILD-REPORT.md` is stale (it says 109 tests). The Stop hook regenerates it on a real stop, and flips `.factory/phase` to `maintain` after `COMPLETE`.

## Stage by stage

| Stage | Playbook asks for | Now | Gap |
|---|---|---|---|
| **1. Plan** | `intent.md` committed, owner accepts or rejects | `intent/` folder; `tools/maintain.py` writes intents from traces | The one real intent is retroactive. Nothing records an accept or reject. |
| **2. Design** | `spec.md` from the intent, constrained by policy skills; concerns flagged to owners | SPEC.md is precise; the factory's `shape` skill exists for specs, glossary and acceptance examples | No policy skills for security, compliance or UX. `shape` is unused, so there is no `acceptance/` suite. Spec versions are not logged. |
| **3. Build** | Plan mode with a committed plan, CLAUDE.md, skills, hooks, worktrees and subagents | CLAUDE.md, PLAN.md, `build-discipline` skill, four hooks, protected paths | Only the original build has a plan; the Fireworks and harness work did not go through PLAN.md. No worktrees or subagents. Auto-mode readiness not assessed. |
| **4. Test** | One verify command, failing-test-first, 20–50 evals in CI that rerun when config changes | Six gates including mutation; `.fix-mode` guard; 5 offline and 4 live evals | 22 offline evals plus 4 live; the offline ones run on every CI push, which covers config changes. The target of 20–50 is met at the low end. Live evals are not in CI. `.fix-mode` is toggled by hand. Incident-to-eval is a convention in LESSONS.md, not enforced. |
| **5. Deploy** | AI PR review, separation of duties, approval gates, sandboxed credentials, managed settings, rehearsed rollback | REVIEW.md, CI workflow, secret guard | CI has never run. Everything goes straight to `main`: no PR flow or branch protection. Nothing uses REVIEW.md automatically. Deny rules cover only `curl`, `wget` and force-push. No sandbox or egress rules. No rollback plan (a library has little to roll back). gitleaks and semgrep now run locally and in CI (untested on GitHub). |
| **6. Maintain** | Deterministic drift detection with tiered response, post-mortems, scheduled security scans | `tools/traced_run.py`, `trace_sensor.py`, `maintain.py`; weekly CI cron | `tools/drift.py` gives a baseline and three response tiers, but it is not scheduled and no real traces are saved yet. The weekly cron only reruns the demo. |
| **Metrics** | First-pass merge rate, rework cycles, DORA | `tools/metrics.py`: fix share, test-touch share, plan completion | Rework share and CI pass rate added (CI pass rate reads 0.00 while the billing lock holds). No plan-to-diff drift, time-to-merge or DORA. |
| **Cross-cutting** | Every stage commits an artifact the next stage reads, with human gates | Chain partly exists: intent → SPEC → PLAN → code → LESSONS | Links are by convention; nothing checks that a change has an intent or a plan task. Human approval points are not defined. |

## Priorities

1. **CI.** Lift the billing lock, then confirm the workflow is green.
2. ~~Evals in CI~~ Done at 22 offline evals; keep adding one per bug.
3. **PR flow.** Branch protection with an AI review using REVIEW.md.
4. ~~Security scans~~ Added to CI; confirm they pass on GitHub.
5. **Maintain loop.** Baseline and tiers exist; save real traces and schedule `drift.py`.
6. **Remaining metrics.** Plan-to-diff drift and time-to-merge.
7. **Policy skills and a `shape` pass** for the next feature.

## Local rehearsal (greenfield and brownfield)

`uv run python tools/sdlc_rehearsal.py all-gates` builds two throwaway repos, installs build mode with the factory installer and drives every guard with the JSON the harness sends. Result: 0 failed, with skips only for GitHub-dependent and policy checks.

| Stage | Greenfield | Brownfield | Notes |
|---|---|---|---|
| 1 Plan | pass | pass | intent sections, author and timestamp, accepted status |
| 2 Design | pass (policy skills SKIP) | pass (policy skills SKIP) | spec committed with acceptance examples |
| 3 Build | pass | pass | protect-paths, secret-guard, CLAUDE.md length, plan committed; Stop hook blocks on open task and on missing report |
| 4 Test | pass (evals SKIP) | pass | fix-mode guard; brownfield baseline shows the expected lint debt |
| 5 Deploy | partial | partial | REVIEW.md and deny rules checked; branch protection, AI PR review and rollback SKIP |
| 6 Maintain | pass | n/a | full Stop hook allows, phase flips to maintain, protected edit still blocked; drift tiers and maintain loop pass in the `kit` scenario |

Findings from building it:
- The factory template ships only `protect-paths` and the Stop hook. `secret-guard`, `fix-mode-guard` and `post-edit-check` are kit-local, so a new repo does not get them unless copied. Fixed: the factory template now ships all three (and git-ignores `.fix-mode`), and the rehearsal relies on the template alone.
- Brownfield install preserves existing hooks, history and `.gitignore`. Legacy lint debt fails the lint gate, so the Stop hook cannot pass until a cleanup task or a ratchet exists.
- The Stop hook demands the last plan task verify with the demo command exactly, and the mutation gate fails with "ran no mutants" on code without branching logic.
- Not proven: a model following the process end to end. That needs a live agent run in the temp repos.

## Live pass (haiku-5-5 builds, sonnet-5-5 grades; no Opus)

`uv run python tools/sdlc_live.py` seeds an accepted intent and spec for `slugify`, installs build mode, lets Haiku build under the Stop hook, runs deterministic checks, then has Sonnet grade a nine-point rubric. Two runs, about $0.11 and $0.13 each:

- Both runs: Haiku wrote a nine-task plan, the Stop hook allowed on the first stop, the phase flipped to maintain, BUILD-REPORT said COMPLETE, protected paths stayed untouched, and an independent probe confirmed the spec examples.
- Run 1: evaluator verdict fail (test-first: code landed with one test and the rest of the tests came later; commits: see below). Run 2: verdict pass (commits: tasks 1-5 lumped into one commit). The model's process varies run to run, so one pass is not a guarantee.
- Harness finding (fixed in the factory): the Stop hook committed `chore: build complete, enter maintain` and never pushed it, so every build ended one commit ahead. It now pushes when the branch has an upstream; a live rerun showed ahead=0.
- Harness finding (fixed in the factory): test-first was enforced only in fix mode. The Stop hook now blocks while a source-changing commit has no test commit at or after it (refactor/chore/docs/style are exempt; `testFirst: false` in build.json turns it off). It proves tests exist for the change, not that they were written first, and it is curable by adding a tests commit because history cannot be rewritten.
- Observation: Haiku once rewrote production code "so the mutation gate has sites to test", which is the gate shaping the code. It was harmless here but worth watching.

## Policy skills (stage 2)

`policy-security`, `policy-compliance` and `policy-cli-ux` now exist under `.claude/skills/`, each with rules, an "Ask first" list and an "Enforced by" section. `tests/test_policy.py` is the hook behind the rules that must always hold (no dynamic execution or process imports, API key read only in `fireworks.py` and never interpolated, stdlib-only runtime, demo shape). Two rules have no mechanical check and say so: copied-code licensing and CLI style. Brand policy is not applicable (no UI). The rehearsal now verifies new repos receive the skills.

## Live brownfield pass

`uv run python tools/sdlc_live.py brownfield` seeds an existing repo (history by another author, a team hook, a `slugify` bug, lint and type debt, existing tests), installs build mode and lets Haiku fix the bug under the Stop hook; Sonnet grades ten criteria. One run, $0.11, 12 deterministic checks and 10 rubric criteria all passed. The builder wrote a failing regression test first, fixed the bug with a one-line change, cleaned the debt in three separate `refactor:` commits, left `shout` and the original tests alone, and the Stop hook allowed on the first stop. The new test was shown to fail against the original buggy `slug.py`. Repo kept at `~/Documents/learning_102/sdlc-live-demos/brownfield-*/brownfield`.

Still not covered: GitHub-side stage 5 (branch protection, AI PR review, release authorization, rollback), real incidents feeding the maintain loop on these repos, plan mode, worktrees and subagents, and anything beyond a trivial codebase. One passing run is not a guarantee; the builder varies run to run.

## Branch protection and AI review (stage 5)

Configured: `main` requires a PR, one code-owner approval, the `verify` and `security` checks, resolved conversations and linear history, and blocks force pushes and deletions (read back via the API). `.github/workflows/ai-review.yml` runs Sonnet (pinned action SHA, `pull_request` not `_target`, read-only plus one PR comment) against REVIEW.md and never approves or blocks; `tests/test_policy.py` guards those properties. Not verified: neither has run, because CI is billing-locked and the `ANTHROPIC_API_KEY` secret is not set. Admin bypass is on, so protection does not bind the owner's own token.
