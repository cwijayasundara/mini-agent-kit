# SDLC gap analysis

Compares mini-agent-kit's harness (as of install commit `92f4e74`) with the stages of the [AI-native SDLC playbook](https://claude.com/resources/articles/the-ai-native-sdlc-playbook). Related references: Martin Fowler's [harness engineering](https://martinfowler.com/articles/harness-engineering.html) and [sensors for coding agents](https://martinfowler.com/articles/sensors-for-coding-agents.html).

## Verification state

- All six gates and the demo pass against `.factory/build.json`: tests (142), lint, types, crap, dry, mutate (every mutant killed).
- The build-mode Stop hook run from a fresh clone of GitHub exits 0 with `decision: allow` and a `COMPLETE` header.
- Hooks (secret guard, post-edit ruff, fix-mode guard, protect-paths) fired in a live session.
- Live-model evals (4 cases, Fireworks) pass.
- Not tested: the CI workflow on GitHub (account billing lock), the `shape` skill, and the weakening check.
- `BUILD-REPORT.md` is stale (it says 109 tests). The Stop hook regenerates it on a real stop, and flips `.factory/phase` to `maintain` after `COMPLETE`.

## Stage by stage

| Stage | Playbook asks for | Now | Gap |
|---|---|---|---|
| **1. Plan** | `intent.md` committed, owner accepts or rejects | `intent/` folder; `tools/maintain.py` writes intents from traces | The one real intent is retroactive. Nothing records an accept or reject. |
| **2. Design** | `spec.md` from the intent, constrained by policy skills; concerns flagged to owners | SPEC.md is precise; the factory's `shape` skill exists for specs, glossary and acceptance examples | No policy skills for security, compliance or UX. `shape` is unused, so there is no `acceptance/` suite. Spec versions are not logged. |
| **3. Build** | Plan mode with a committed plan, CLAUDE.md, skills, hooks, worktrees and subagents | CLAUDE.md, PLAN.md, `build-discipline` skill, four hooks, protected paths | Only the original build has a plan; the Fireworks and harness work did not go through PLAN.md. No worktrees or subagents. Auto-mode readiness not assessed. |
| **4. Test** | One verify command, failing-test-first, 20–50 evals in CI that rerun when config changes | Six gates including mutation; `.fix-mode` guard; 5 offline and 4 live evals | 9 evals, not 20–50. Evals do not rerun when CLAUDE.md, skills or hooks change. Live evals are not in CI. `.fix-mode` is toggled by hand. Incident-to-eval is a convention in LESSONS.md, not enforced. |
| **5. Deploy** | AI PR review, separation of duties, approval gates, sandboxed credentials, managed settings, rehearsed rollback | REVIEW.md, CI workflow, secret guard | CI has never run. Everything goes straight to `main`: no PR flow or branch protection. Nothing uses REVIEW.md automatically. Deny rules cover only `curl`, `wget` and force-push. No sandbox or egress rules. No rollback plan (a library has little to roll back). |
| **6. Maintain** | Deterministic drift detection with tiered response, post-mortems, scheduled security scans | `tools/traced_run.py`, `trace_sensor.py`, `maintain.py`; weekly CI cron | Manual and unscheduled. No rolling baseline or response tiers. The weekly cron only reruns the demo. No SAST or gitleaks scan, only a regex test. |
| **Metrics** | First-pass merge rate, rework cycles, DORA | `tools/metrics.py`: fix share, test-touch share, plan completion | No first-pass CI rate, rework cycles, plan-to-diff drift or time-to-merge. |
| **Cross-cutting** | Every stage commits an artifact the next stage reads, with human gates | Chain partly exists: intent → SPEC → PLAN → code → LESSONS | Links are by convention; nothing checks that a change has an intent or a plan task. Human approval points are not defined. |

## Priorities

1. **CI.** Lift the billing lock, then confirm the workflow is green.
2. **Evals in CI.** Grow the evals and run them on every change to CLAUDE.md, skills or hooks.
3. **PR flow.** Branch protection with an AI review using REVIEW.md.
4. **Security scans.** Add gitleaks and semgrep to CI.
5. **Maintain loop.** Save real traces and add a baseline with response tiers.
6. **Remaining metrics.** First-pass CI rate and rework cycles.
7. **Policy skills and a `shape` pass** for the next feature.
