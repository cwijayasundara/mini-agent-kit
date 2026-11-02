# Pending items (handoff)

State as of `9e2c12b` on `main`: all six gates and the demo pass, 167 tests, gitleaks clean. Build mode is installed (`92f4e74`). See `docs/sdlc-gap-analysis.md` for the full stage-by-stage comparison.

## Blocked on something outside the repo

1. **CI has never run.** The GitHub account has a billing lock ("account is locked due to a billing issue"). After lifting it: `gh run rerun` the latest run, or push any commit, and confirm both the `verify` and `security` jobs are green. A clean-clone run of every `verify` step passed locally.
2. **gitleaks and semgrep in CI are untested on GitHub.** Semgrep runs locally only through `uvx semgrep`; the Homebrew/pip install is broken by an opentelemetry conflict.

## Needs a decision before doing

3. **Branch protection and AI PR review.** Everything goes straight to `main`. A PR flow needs: branch protection via `gh api` (admin rights), a review workflow using `REVIEW.md` (needs `ANTHROPIC_API_KEY` secret and billing). With one developer there is no second human for separation of duties.
4. **Policy skills (security, compliance, UX).** They belong in `.claude/skills/`, which build mode protects. Add them, then re-run the installer: `cd ~/Documents/learning_102/lights_on_factory_v2.0 && node scripts/install-build-mode.ts <this repo> --demo "uv run mini-agent demo"` (needs a clean tree; it makes a `chore: install build mode` commit; push it afterwards or the Stop hook blocks on "commit and push").
5. **Use the `shape` skill** (new in the installer) for the next feature: spec, glossary, decision records, acceptance examples. No `acceptance/` suite exists yet.

## Buildable now (items 6-9 done in 03415a0; see intent/003)

6. **Save real traces and schedule `tools/drift.py`.** Use `tools/traced_run.py` to write to `traces/` (gitignored). `drift.py` needs 5 recent plus 5 baseline traces before it acts. Decide where traces live in CI (artifact upload) and add a scheduled job.
7. **Metrics still missing:** plan-to-diff drift, time-to-merge (only meaningful with PRs), DORA measures.
8. **Intent and plan discipline:** new work should start as `intent/NNN-name.md` and get PLAN.md tasks. The Fireworks and harness work did neither.
9. **Add an eval for every bug** (`evals/*.json`, offline; `evals/live/*.json`, real model, opt-in via `tools/live_evals.py`).

## Things to know

- `BUILD-REPORT.md` shows as modified after every session: the Stop hook rewrites it (it says 109 tests; stale). Discard with `git checkout BUILD-REPORT.md`, or let a real stop regenerate it.
- The Stop hook flips `.factory/phase` to `maintain` after `COMPLETE`.
- Protected paths (do not edit): `.claude/`, `.factory/build.json`, `.factory/gates/`, `SPEC.md`. Editing them without re-running the installer makes the Stop hook block.
- Bug-fix flow: `touch .fix-mode`, add a new failing test, fix the code, `rm .fix-mode`.
- Open question never answered: should the kit become a harness for other agents (tool risk levels, approval hooks), or only be well harnessed itself?

## Added after the local rehearsal
- `tools/sdlc_rehearsal.py` (intent/004) passes on greenfield, brownfield and kit scenarios. Kit-local hooks are now in the factory template. Still open: policy skills, branch protection and rollback (items 3 and 4).
- Live pass done (`tools/sdlc_live.py`, intent/004). Open harness gaps from it: the Stop hook's own commit is never pushed; test-first for new features is not enforced.
