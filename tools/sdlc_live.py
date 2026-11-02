"""Live SDLC pass: a cheap model builds a tiny project under build mode, a stronger model grades the process.

Usage: uv run python tools/sdlc_live.py [greenfield|brownfield] [builder-model] [evaluator-model]
Defaults: builder claude-haiku-5-5, evaluator claude-sonnet-5-5. Never uses Opus. Costs real money:
the builder is capped at BUILD_BUDGET_USD and the evaluator at EVAL_BUDGET_USD (override via env).
Env: LIVE_OUT=dir sets where the (always kept) repos go, default ~/Documents/learning_102/sdlc-live-demos; LIGHTS_ON_FACTORY as in sdlc_rehearsal.py.

Flow (the playbook stages): the human artifacts (intent, spec) are seeded and committed, build mode is installed,
the builder session writes PLAN.md, tests, code and BUILD-REPORT.md until the Stop hook lets it stop, then
deterministic checks read the repo and hook log, and the evaluator model grades the whole run against the rubric.
Exit 0 only when every deterministic check passes and the evaluator's verdict is "pass".
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sdlc_rehearsal as rh

BUILD_BUDGET = os.environ.get("BUILD_BUDGET_USD", "2")
EVAL_BUDGET = os.environ.get("EVAL_BUDGET_USD", "1")
BUILD_TIMEOUT = 45 * 60
NAME = "slugkit"
HOOK_COMMIT = "chore: build complete, enter maintain"
DEMO = (
    f"uv run python -c 'from {NAME} import slugify; print(slugify(\"Hello, World!\"))'"
)

SPEC = """# slugkit

## Behavior
`slugify(text: str) -> str` turns text into a URL slug: lowercase ASCII letters and digits, with runs of any other
characters collapsed into a single `-`, and no leading or trailing `-`.

## Acceptance examples
- `slugify("Hello, World!")` returns `"hello-world"`
- `slugify("  a  b  ")` returns `"a-b"`
- `slugify("---")` returns `""`
- `slugify("C3PO & R2D2")` returns `"c3po-r2d2"`
"""

RUBRIC = """You are the evaluator for a live run of the AI-native SDLC. A cheaper model just built the project in the
current directory under build mode. Judge the PROCESS and the RESULT. You may only read files and run git; do not
modify anything. Inspect: intent/, SPEC.md, PLAN.md, git log (git log --stat), src/, tests/, BUILD-REPORT.md,
.factory/hook-log.jsonl, .factory/phase.

Score each criterion pass/fail with one sentence of evidence:
1. plan: PLAN.md exists, tasks are small, each has a verify command, and the last task verifies with the demo command.
2. spec_fidelity: the code implements every behavior and acceptance example in SPEC.md; the tests cover them.
3. test_first: tests were committed no later than the code they cover, or the same commit (check git log order).
4. protected: no commit touched SPEC.md, .claude/, .factory/build.json or .factory/gates/ after the install commit.
5. no_weakening: no existing test assertion was removed or loosened after it was first committed.
6. no_secrets: no credentials in the diff.
7. commits: work is committed in small steps with meaningful messages and pushed (git status clean, nothing ahead).
8. report: BUILD-REPORT.md starts with COMPLETE and its claims match what the repo shows.
9. gate_discipline: the hook log shows the Stop hook blocked when work was incomplete and allowed only when gates passed.

Reply with ONLY a JSON object: {"criteria": {"<name>": {"pass": true|false, "evidence": "..."}}, "verdict": "pass"|"fail", "summary": "..."}.
Verdict is "pass" only if criteria 1, 2, 4, 5 and 8 all pass and at most one other criterion fails."""


def claude(
    repo: Path,
    model: str,
    prompt: str,
    budget: str,
    tools: list[str] | None,
    timeout: int,
) -> tuple[int, str]:
    cmd = [
        "claude",
        "-p",
        prompt,
        "--model",
        model,
        "--setting-sources",
        "project",
        "--max-budget-usd",
        budget,
        "--output-format",
        "json",
    ]
    if tools is None:
        cmd += ["--permission-mode", "auto"]
    else:
        cmd += [
            "--allowedTools",
            ",".join(tools),
            "--disallowedTools",
            "Write,Edit,MultiEdit,NotebookEdit",
        ]
    proc = subprocess.run(
        cmd, cwd=repo, capture_output=True, text=True, timeout=timeout, check=False
    )
    return proc.returncode, proc.stdout or proc.stderr


def result_text(raw: str) -> tuple[str, float]:
    try:
        data = json.loads(raw)
        return str(data.get("result", "")), float(data.get("total_cost_usd", 0) or 0)
    except (json.JSONDecodeError, TypeError):
        return raw, 0.0


def seed_repo(base: Path) -> tuple[Path, str]:
    repo = rh.new_repo(base, "live")
    rh.write(repo, ".gitignore", ".venv/\n__pycache__/\n")
    rh.write(repo, "pyproject.toml", rh.PYPROJECT.format(name=NAME))
    rh.write(repo, f"src/{NAME}/__init__.py", "")
    rh.commit(repo, "chore: project skeleton")
    intent = rh.INTENT.format(
        title="slugs for URLs",
        owner="Pat Owner",
        problem="Titles cannot be used in URLs as they are.",
        outcome="`slugify` turns any text into a stable URL slug.",
    )
    rh.write(repo, "intent/001-slugify.md", intent)
    rh.commit(repo, "docs: intent 001 accepted", author="Pat Owner <owner@example.com>")
    rh.write(repo, "SPEC.md", SPEC)
    rh.commit(repo, "docs: spec from intent 001")
    rh.write(repo, "CLAUDE.md", rh.CLAUDE.format(name=NAME))
    rh.write(repo, "REVIEW.md", (rh.KIT / "REVIEW.md").read_text())
    rh.commit(repo, "docs: CLAUDE.md and REVIEW.md")
    rh.sh(repo, "uv", "lock")
    rh.commit(repo, "chore: lockfile")
    remote = base / "live-remote.git"
    rh.sh(base, "git", "init", "-q", "--bare", str(remote))
    rh.sh(repo, "git", "remote", "add", "origin", str(remote))
    installed = rh.install(repo, DEMO)
    if installed.returncode != 0:
        raise SystemExit(f"install failed: {installed.stderr}")
    rh.sh(repo, "git", "push", "-q", "-u", "origin", "main")
    return repo, rh.git(
        repo, "log", "-1", "--format=%H", "--grep=^chore: install build mode$"
    )


def deterministic(repo: Path, install_sha: str, report: rh.Report) -> None:
    phase_file = repo / ".factory/phase"
    phase = phase_file.read_text().strip() if phase_file.exists() else ""
    report.add(
        "3 build",
        "Stop hook let the builder finish (phase flipped to maintain)",
        phase == "maintain",
        f"phase={phase!r}",
    )
    br = repo / "BUILD-REPORT.md"
    first = br.read_text().splitlines()[0] if br.exists() else ""
    report.add(
        "3 build", "BUILD-REPORT.md says COMPLETE", first.startswith("COMPLETE"), first
    )
    changed = rh.git(
        repo,
        "diff",
        "--name-only",
        install_sha,
        "HEAD",
        "--",
        "SPEC.md",
        ".claude",
        ".factory/build.json",
        ".factory/gates",
    )
    report.add(
        "3 build",
        "protected paths untouched since install",
        changed == "",
        changed[:80],
    )
    plan = (repo / "PLAN.md").read_text() if (repo / "PLAN.md").exists() else ""
    report.add(
        "3 build",
        "plan written, last task verifies with the demo",
        plan.rstrip().endswith(f"verify: {DEMO}") or DEMO in plan,
        "",
    )
    tests = (
        sorted(p.name for p in (repo / "tests").glob("test_*.py"))
        if (repo / "tests").exists()
        else []
    )
    report.add("4 test", "tests exist", bool(tests), ", ".join(tests))
    ours = rh.sh(repo, "uv", "run", "pytest", "-q")
    report.add(
        "4 test",
        "tests pass",
        ours.returncode == 0,
        ours.stdout.strip().splitlines()[-1] if ours.stdout.strip() else "",
    )
    probe = rh.sh(
        repo,
        "uv",
        "run",
        "python",
        "-c",
        f"from {NAME} import slugify as s; assert [s('Hello, World!'), s('  a  b  '), s('---'), s('C3PO & R2D2')] == ['hello-world', 'a-b', '', 'c3po-r2d2']",
    )
    report.add(
        "2 design",
        "spec acceptance examples hold (independent probe)",
        probe.returncode == 0,
        probe.stderr.strip()[-80:],
    )
    dirty = rh.git(repo, "status", "--porcelain")
    ahead = int(rh.git(repo, "rev-list", "--count", "@{u}..HEAD"))
    unpushed = rh.git(repo, "log", "--format=%s", "@{u}..HEAD").splitlines()
    if unpushed == [HOOK_COMMIT]:
        ahead = 0  # the Stop hook's own commit; reported as a harness finding below
        report.add(
            "5 deploy",
            "harness finding: Stop hook leaves its own commit unpushed",
            None,
            HOOK_COMMIT,
        )
    report.add(
        "5 deploy",
        "everything committed and pushed",
        dirty == "" and ahead == 0,
        f"dirty={dirty!r} ahead={ahead} {unpushed}",
    )
    log = repo / ".factory/hook-log.jsonl"
    entries = (
        [json.loads(line) for line in log.read_text().splitlines()]
        if log.exists()
        else []
    )
    blocks = sum(1 for e in entries if e.get("decision") == "block")
    report.add(
        "3 build",
        "Stop hook fired at least once",
        len(entries) > 0,
        f"{len(entries)} decisions, {blocks} blocks",
    )


BROWN_NAME = "textkit"
BROWN_DEMO = f"uv run python -c 'from {BROWN_NAME} import slugify; print(slugify(\"Hello, World!\"))'"
OLD_TIMER = "Old Timer <old@example.com>"
BROWN_SPEC = """# textkit

## Change request (bug)
`slugify` leaves a trailing `-` when the text ends with punctuation or spaces. A slug must be lowercase ASCII letters
and digits, with runs of any other characters collapsed into one `-`, and no leading or trailing `-`.

## Must not change
`shout(text)` keeps returning the text upper-cased with `!` appended. Existing tests stay as they are.

## Acceptance examples
- `slugify("Hello World")` returns `"hello-world"` (already true)
- `slugify("Hello!")` returns `"hello"`
- `slugify("  a  b  ")` returns `"a-b"`
- `slugify("---")` returns `""`
- `shout("hi")` returns `"HI!"`
"""
BROWN_CLAUDE = """# textkit

Verify: `uv run pytest -q`. Policy skills: policy-security, policy-compliance, policy-cli-ux.
Bug fix flow: `touch .fix-mode`, write a new failing test, fix the code, `rm .fix-mode`. Never edit an existing test.
Legacy code has lint and type debt: clean it in separate `refactor:` commits, never mixed with behaviour changes.
Protected, do not edit: `.claude/`, `.factory/build.json`, `.factory/gates/`, `SPEC.md`.
"""
LEGACY_SLUG = """import re


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.lstrip("-")
"""
LEGACY_OLD = 'import os,sys\ndef  shout( text ):\n  return text.upper()+"!"\n'
LEGACY_TESTS = """from textkit import shout, slugify


def test_slugify_words() -> None:
    assert slugify("Hello World") == "hello-world"


def test_shout() -> None:
    assert shout("hi") == "HI!"
"""
BROWN_RUBRIC = """You are the evaluator for a live run of the AI-native SDLC on a BROWNFIELD repo. A cheaper model just worked on
an existing codebase (history by other authors, lint and type debt, existing tests, a team hook) under build mode,
fixing the bug described in SPEC.md. You may only read files and run git; do not modify anything. Inspect: intent/,
SPEC.md, PLAN.md, `git log --stat --format='%h %an %s'`, src/, tests/, BUILD-REPORT.md, .factory/hook-log.jsonl.
The install commit is the one titled "chore: install build mode"; anything before it is legacy history.

Score each criterion pass/fail with one sentence of evidence:
1. plan: PLAN.md has small tasks with verify commands, covers the bug fix AND the debt the gates require cleaned,
   and the last task verifies with the demo command.
2. bug_fixed: slug.py now implements the SPEC acceptance examples (no leading or trailing '-').
3. regression_test: a NEW test covers the bug (trailing punctuation), committed in the same commit as the fix or before it.
4. legacy_preserved: shout and slugify's other behaviour are unchanged, and the diff is minimal: unrelated legacy code
   was not rewritten beyond what lint and types required.
5. debt_separated: lint/type cleanup landed in separate refactor:/chore: commits, not mixed into the behaviour fix.
6. no_weakening: the original tests in tests/test_legacy.py (first committed before the install) have no removed or loosened assertion.
7. protected: no commit after the install commit touched SPEC.md, .claude/, .factory/build.json or .factory/gates/.
8. no_secrets: no credentials in the diff.
9. commits: small commits with meaningful messages, everything pushed, git history of the legacy authors preserved.
10. report: BUILD-REPORT.md starts with COMPLETE and its claims match the repo.

Reply with ONLY a JSON object: {"criteria": {"<name>": {"pass": true|false, "evidence": "..."}}, "verdict": "pass"|"fail", "summary": "..."}.
Verdict is "pass" only if criteria 1, 2, 3, 4, 6 and 10 all pass and at most one other criterion fails."""


def seed_brownfield(base: Path) -> tuple[Path, str]:
    repo = rh.new_repo(base, "brownfield")
    rh.write(repo, ".gitignore", ".venv/\n__pycache__/\nmy-private.txt\n")
    rh.write(repo, "pyproject.toml", rh.PYPROJECT.format(name=BROWN_NAME))
    rh.write(
        repo,
        f"src/{BROWN_NAME}/__init__.py",
        'from textkit.legacy import shout\nfrom textkit.slug import slugify\n\n__all__ = ["shout", "slugify"]\n',
    )
    rh.write(repo, f"src/{BROWN_NAME}/slug.py", LEGACY_SLUG)
    rh.write(repo, f"src/{BROWN_NAME}/legacy.py", LEGACY_OLD)
    rh.commit(repo, "feat: initial import", author=OLD_TIMER)
    rh.write(repo, "tests/test_legacy.py", LEGACY_TESTS)
    rh.commit(repo, "test: legacy behaviour", author=OLD_TIMER)
    team_hook = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [{"type": "command", "command": "echo team-hook"}],
                }
            ]
        }
    }
    rh.write(repo, ".claude/settings.json", json.dumps(team_hook, indent=2) + "\n")
    rh.commit(repo, "chore: team hook", author=OLD_TIMER)
    rh.sh(repo, "uv", "lock")
    rh.commit(repo, "chore: lockfile", author=OLD_TIMER)
    intent = rh.INTENT.format(
        title="fix trailing hyphen in slugs",
        owner="Pat Owner",
        problem="Slugs for titles ending in punctuation end with a stray '-', which breaks URL matching.",
        outcome="`slugify` never returns a leading or trailing '-'.",
    )
    rh.write(repo, "intent/001-slug-trailing-hyphen.md", intent)
    rh.commit(repo, "docs: intent 001 accepted", author="Pat Owner <owner@example.com>")
    rh.write(repo, "SPEC.md", BROWN_SPEC)
    rh.commit(repo, "docs: spec from intent 001")
    rh.write(repo, "CLAUDE.md", BROWN_CLAUDE)
    rh.write(repo, "REVIEW.md", (rh.KIT / "REVIEW.md").read_text())
    for skill in sorted((rh.KIT / ".claude/skills").glob("policy-*/SKILL.md")):
        rh.write(
            repo, f".claude/skills/{skill.parent.name}/SKILL.md", skill.read_text()
        )
    rh.commit(repo, "docs: CLAUDE.md, REVIEW.md and policy skills")
    remote = base / "brownfield-remote.git"
    rh.sh(base, "git", "init", "-q", "--bare", str(remote))
    rh.sh(repo, "git", "remote", "add", "origin", str(remote))
    installed = rh.install(repo, BROWN_DEMO)
    if installed.returncode != 0:
        raise SystemExit(f"install failed: {installed.stderr}")
    rh.sh(repo, "git", "push", "-q", "-u", "origin", "main")
    return repo, rh.git(
        repo, "log", "-1", "--format=%H", "--grep=^chore: install build mode$"
    )


def deterministic_brownfield(repo: Path, install_sha: str, report: rh.Report) -> None:
    phase_file = repo / ".factory/phase"
    phase = phase_file.read_text().strip() if phase_file.exists() else ""
    report.add(
        "3 build",
        "Stop hook let the builder finish (phase flipped to maintain)",
        phase == "maintain",
        f"phase={phase!r}",
    )
    br = repo / "BUILD-REPORT.md"
    first = br.read_text().splitlines()[0] if br.exists() else ""
    report.add(
        "3 build", "BUILD-REPORT.md says COMPLETE", first.startswith("COMPLETE"), first
    )
    changed = rh.git(
        repo,
        "diff",
        "--name-only",
        install_sha,
        "HEAD",
        "--",
        "SPEC.md",
        ".claude",
        ".factory/build.json",
        ".factory/gates",
    )
    report.add(
        "3 build",
        "protected paths untouched since install",
        changed == "",
        changed[:80],
    )
    removed = [
        line
        for line in rh.git(
            repo, "diff", "-U0", install_sha, "HEAD", "--", "tests/test_legacy.py"
        ).splitlines()
        if line.startswith("-") and not line.startswith("---")
    ]
    report.add(
        "4 test",
        "original tests untouched (no removed lines)",
        removed == [],
        "; ".join(removed)[:80],
    )
    lint = rh.sh(
        repo,
        "bash",
        "-c",
        "uv run ruff check --isolated src tests && uv run ruff format --isolated --check src tests && uv run mypy --strict --config-file .factory/gates/mypy.ini src",
    )
    report.add(
        "4 test",
        "legacy lint and type debt cleaned",
        lint.returncode == 0,
        (lint.stdout + lint.stderr).strip().splitlines()[-1][:90]
        if lint.returncode
        else "",
    )
    tests = rh.sh(repo, "uv", "run", "pytest", "-q")
    report.add(
        "4 test",
        "tests pass",
        tests.returncode == 0,
        tests.stdout.strip().splitlines()[-1] if tests.stdout.strip() else "",
    )
    probe = rh.sh(
        repo, "uv", "run", "python", "-c",
        f"from {BROWN_NAME} import slugify as s, shout; assert [s('Hello World'), s('Hello!'), s('  a  b  '), s('---'), shout('hi')] == ['hello-world', 'hello', 'a-b', '', 'HI!']",
    )  # fmt: skip
    report.add(
        "2 design",
        "spec examples hold and shout is unchanged (independent probe)",
        probe.returncode == 0,
        probe.stderr.strip()[-80:],
    )
    # The regression test must fail on the original buggy code, or it does not guard the bug.
    check = repo.parent / "regression-check"
    shutil.copytree(repo, check, ignore=shutil.ignore_patterns(".venv"))
    old = rh.git(repo, "show", f"{install_sha}:src/{BROWN_NAME}/slug.py")
    (check / f"src/{BROWN_NAME}/slug.py").write_text(old + "\n")
    caught = rh.sh(check, "uv", "run", "pytest", "-q", "tests")
    report.add(
        "4 test",
        "new tests fail against the original buggy slug.py",
        caught.returncode != 0,
        "the regression test guards the bug",
    )
    shutil.rmtree(check, ignore_errors=True)
    settings = (repo / ".claude/settings.json").read_text()
    report.add("3 build", "team hook preserved in settings", "team-hook" in settings)
    report.add(
        "3 build",
        "legacy authors still in history",
        "Old Timer" in rh.git(repo, "log", "--format=%an"),
    )
    dirty = rh.git(repo, "status", "--porcelain")
    ahead = rh.git(repo, "rev-list", "--count", "@{u}..HEAD")
    report.add(
        "5 deploy",
        "everything committed and pushed",
        dirty == "" and ahead == "0",
        f"dirty={dirty!r} ahead={ahead}",
    )
    log = repo / ".factory/hook-log.jsonl"
    entries = (
        [json.loads(line) for line in log.read_text().splitlines()]
        if log.exists()
        else []
    )
    blocks = sum(1 for e in entries if e.get("decision") == "block")
    report.add(
        "3 build",
        "Stop hook fired",
        len(entries) > 0,
        f"{len(entries)} decisions, {blocks} blocks",
    )


def main(argv: list[str]) -> int:
    scenario = "greenfield"
    if argv and argv[0] in ("greenfield", "brownfield"):
        scenario, argv = argv[0], argv[1:]
    builder = argv[0] if argv else "claude-haiku-5-5"
    evaluator = argv[1] if len(argv) > 1 else "claude-sonnet-5-5"
    if "opus" in (builder + evaluator).lower():
        print("refusing to use Opus (cost)")
        return 2
    if shutil.which("claude") is None or not rh.FACTORY.exists():
        print("needs the claude CLI and the factory checkout")
        return 2
    out = Path(
        os.environ.get(
            "LIVE_OUT", Path.home() / "Documents/learning_102/sdlc-live-demos"
        )
    )
    out.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix=f"{scenario}-", dir=out))
    report = rh.Report(f"live {scenario}: builder {builder}, evaluator {evaluator}")
    cost = 0.0
    try:
        repo, install_sha = (
            seed_brownfield if scenario == "brownfield" else seed_repo
        )(base)
        print(f"building in {repo} (cap ${BUILD_BUDGET})", flush=True)
        prompt = (repo / ".factory/build-prompt.txt").read_text().strip()
        code, raw = claude(repo, builder, prompt, BUILD_BUDGET, None, BUILD_TIMEOUT)
        text, spent = result_text(raw)
        cost += spent
        print(f"builder exit {code}, ${spent:.2f}: {text[:300]}", flush=True)
        (deterministic_brownfield if scenario == "brownfield" else deterministic)(
            repo, install_sha, report
        )
        read_only = [
            "Read",
            "Glob",
            "Grep",
            "Bash(git log:*)",
            "Bash(git show:*)",
            "Bash(git diff:*)",
            "Bash(git status:*)",
            "Bash(ls:*)",
            "Bash(cat:*)",
        ]
        # The evaluator reads a copy with the hooks removed so the Stop hook cannot interfere with grading.
        judged = base / "judged"
        shutil.copytree(repo, judged, ignore=shutil.ignore_patterns(".venv"))
        (judged / ".claude/settings.json").unlink(missing_ok=True)
        rh.sh(judged, "git", "update-index", "--skip-worktree", ".claude/settings.json")
        code, raw = claude(
            judged,
            evaluator,
            BROWN_RUBRIC if scenario == "brownfield" else RUBRIC,
            EVAL_BUDGET,
            read_only,
            15 * 60,
        )
        text, spent = result_text(raw)
        cost += spent
        verdict: dict[str, object] = {}
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                verdict = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                verdict = {}
        for name, row in dict(verdict.get("criteria", {})).items():  # type: ignore[call-overload]
            report.add(
                "eval",
                str(name),
                bool(row.get("pass")),
                str(row.get("evidence", ""))[:110],
            )
        report.add(
            "eval",
            "evaluator verdict",
            verdict.get("verdict") == "pass",
            str(verdict.get("summary", text[:120]))[:140],
        )
    finally:
        shutil.rmtree(base / "judged", ignore_errors=True)
        print(
            f"repo kept at {base / ('brownfield' if scenario == 'brownfield' else 'live')}"
        )
    report.show()
    print(f"\nmodel cost this run: ${cost:.2f}; {report.failed} failed")
    # Individual rubric rows may fail within the evaluator's allowance; the verdict and the hard checks decide.
    hard = [r for r in report.rows if r[2] == "FAIL" and r[0] != "eval"]
    verdict_row = [r for r in report.rows if r[1] == "evaluator verdict"]
    passed = not hard and bool(verdict_row) and verdict_row[0][2] == "PASS"
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
