"""Rehearse the AI-native SDLC locally on a throwaway greenfield repo and a throwaway brownfield repo.

Usage: uv run python tools/sdlc_rehearsal.py [greenfield|brownfield|kit|all|all-gates]
Env:   LIGHTS_ON_FACTORY = path to the lights_on_factory checkout (default ~/Documents/learning_102/lights_on_factory_v2.0)
       KEEP=1 keeps the temp repos for inspection

For each of the playbook's six stages (plan, design, build, test, deploy, maintain) it checks the artifact is
committed and that the gate behind it fires: it installs build mode with the factory installer, then drives the real
hooks and gates with the JSON the Claude Code harness would send. No network, no CI, no model.
It does NOT prove a model follows the process; it proves the guards stop it when it does not.
`all-gates` additionally lets the Stop hook run all six gates (including mutation) on the greenfield repo; it is slow.
Exit 0 only when no check FAILed. SKIP means the check needs GitHub or a live model.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
FACTORY = Path(
    os.environ.get(
        "LIGHTS_ON_FACTORY",
        Path.home() / "Documents/learning_102/lights_on_factory_v2.0",
    )
)
INTENT_SECTIONS = (
    "Problem",
    "Outcome",
    "Users and systems",
    "Constraints",
    "Open questions",
)
FAKE_KEY = "sk-" + "a1b2c3d4e5f6g7h8i9j0k1l2"


@dataclass
class Report:
    scenario: str
    rows: list[tuple[str, str, str, str]] = field(default_factory=list)

    def add(self, stage: str, name: str, ok: bool | None, detail: str = "") -> None:
        status = "SKIP" if ok is None else "PASS" if ok else "FAIL"
        self.rows.append((stage, name, status, detail))

    @property
    def failed(self) -> int:
        return sum(1 for r in self.rows if r[2] == "FAIL")

    def show(self) -> None:
        print(f"\n== {self.scenario} ==")
        for stage, name, status, detail in self.rows:
            print(f"{status:4}  {stage:9} {name}" + (f"  [{detail}]" if detail else ""))


def sh(cwd: Path, *cmd: str, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
    )


def git(cwd: Path, *args: str) -> str:
    return sh(cwd, "git", *args).stdout.strip()


def commit(cwd: Path, message: str, author: str = "Rehearsal <r@example.com>") -> None:
    sh(cwd, "git", "add", "-A")
    name, mail = author.rstrip(">").split(" <")
    sh(
        cwd,
        "git",
        "-c",
        f"user.name={name}",
        "-c",
        f"user.email={mail}",
        "commit",
        "-q",
        "-m",
        message,
    )


def new_repo(base: Path, name: str) -> Path:
    repo = base / name
    repo.mkdir()
    sh(repo, "git", "init", "-q", "-b", "main")
    return repo


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _run_hook(
    repo: Path, command: list[str], payload: dict[str, object]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        input=json.dumps(payload),
        check=False,
        capture_output=True,
        text=True,
        timeout=3600,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)},
    )


def hook(repo: Path, name: str, tool: str, tool_input: dict[str, str]) -> str:
    """Run a PreToolUse hook as the harness would; return 'deny', 'allow' or 'error: ...'."""
    proc = _run_hook(
        repo,
        ["node", str(repo / ".claude/hooks" / name)],
        {"cwd": str(repo), "tool_name": tool, "tool_input": tool_input},
    )
    if proc.returncode != 0:
        return f"error: {proc.stderr.strip()[:80]}"
    if not proc.stdout.strip():
        return "allow"
    return str(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"])


def stop_hook(repo: Path) -> dict[str, str]:
    """Run the Stop hook exactly as settings.json wires it (pinned copy from the install commit)."""
    settings = json.loads((repo / ".claude/settings.json").read_text())
    command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
    proc = _run_hook(repo, ["bash", "-c", command], {"cwd": str(repo)})
    if proc.returncode != 0:
        return {"decision": "crash", "reason": proc.stderr.strip()[-200:]}
    return (
        dict(json.loads(proc.stdout)) if proc.stdout.strip() else {"decision": "allow"}
    )


INTENT = """# Intent: {title}

Status: accepted by {owner}

## Problem
{problem}

## Outcome
{outcome}

## Users and systems
Developers using the package.

## Constraints
Standard library only.

## Open questions
None.
"""

SPEC = """# {title}

## Behavior
`count_words(text, min_len)` returns the number of whitespace-separated words in `text` with at least `min_len` characters.

## Acceptance examples
- `count_words("a b c", 1)` returns 3
- `count_words("a bb ccc", 2)` returns 2
- `count_words("", 1)` returns 0
"""

PLAN_DONE = """# PLAN

- [x] 1. count_words
  verify: uv run pytest -q
  done: {sha}
- [x] 2. demo runs
  verify: {demo}
  done: {sha}
"""

PLAN_OPEN = """# PLAN

- [ ] 1. {task}
  verify: {demo}
"""

PYPROJECT = """[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.11"

[dependency-groups]
dev = ["pytest", "pytest-cov", "ruff", "mypy"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{name}"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
"""

CODE = '''"""Word counting."""


def count_words(text: str, min_len: int) -> int:
    """Number of whitespace-separated words in text that are at least min_len long."""
    return sum(1 for word in text.split() if len(word) >= min_len)
'''

TEST = """from {name} import count_words


def test_counts_all_words() -> None:
    assert count_words("a b c", 1) == 3


def test_empty() -> None:
    assert count_words("", 1) == 0


def test_min_len_filters_short_words() -> None:
    assert count_words("a bb ccc", 2) == 2


def test_min_len_is_inclusive() -> None:
    assert count_words("ccc", 3) == 1
    assert count_words("cc", 3) == 0


def test_one_letter_words_count_at_min_len_one() -> None:
    assert count_words("a bb", 1) == 2
"""

CLAUDE = """# {name}

Verify: `uv run pytest -q`. Bugs: write a failing test first, never weaken one.
Protected, do not edit: `.claude/`, `.factory/build.json`, `.factory/gates/`, `SPEC.md`.
"""


def seed(repo: Path, name: str, legacy: bool) -> None:
    write(repo, "pyproject.toml", PYPROJECT.format(name=name))
    write(
        repo,
        f"src/{name}/__init__.py",
        f'from {name}.core import count_words\n\n__all__ = ["count_words"]\n',
    )
    write(repo, f"src/{name}/core.py", CODE)
    write(repo, "tests/test_core.py", TEST.format(name=name))
    if legacy:
        write(
            repo, f"src/{name}/old.py", "import os,sys\ndef  messy( x ):\n  return x\n"
        )


def adopt_artifacts(repo: Path, name: str, owner: str) -> None:
    """Plan, design and build-guide artifacts the playbook wants committed before the guards matter."""
    intent = INTENT.format(
        title="count words",
        owner=owner,
        problem="Callers cannot count words consistently.",
        outcome="`count_words` exists and is tested.",
    )
    write(repo, "intent/001-word-count.md", intent)
    commit(repo, "docs: intent 001 accepted", author=f"{owner} <owner@example.com>")
    write(repo, "SPEC.md", SPEC.format(title=name))
    commit(repo, "docs: spec from intent 001")
    write(repo, "CLAUDE.md", CLAUDE.format(name=name))
    write(repo, "REVIEW.md", (KIT / "REVIEW.md").read_text())
    commit(repo, "docs: CLAUDE.md and REVIEW.md")


def install(repo: Path, demo: str) -> subprocess.CompletedProcess[str]:
    return sh(
        KIT,
        "node",
        str(FACTORY / "scripts/install-build-mode.ts"),
        str(repo),
        "--demo",
        demo,
    )


def stage_plan_design(r: Report, repo: Path) -> None:
    intent = next(iter((repo / "intent").glob("*.md")), None)
    text = intent.read_text() if intent else ""
    missing = [s for s in INTENT_SECTIONS if f"## {s}" not in text]
    r.add(
        "1 plan",
        "intent committed with all template sections",
        intent is not None and not missing,
        ", ".join(missing),
    )
    log = git(repo, "log", "--format=%an|%aI", "--", "intent")
    r.add(
        "1 plan",
        "intent has author and timestamp in git",
        "|" in log and not log.startswith("|"),
        log[:40],
    )
    r.add("1 plan", "owner acceptance recorded", "Status: accepted" in text)
    spec = repo / "SPEC.md"
    r.add(
        "2 design",
        "spec committed",
        spec.exists() and git(repo, "log", "--format=%h", "--", "SPEC.md") != "",
    )
    r.add(
        "2 design",
        "spec has acceptance examples",
        "## Acceptance examples" in (spec.read_text() if spec.exists() else ""),
    )
    r.add(
        "2 design",
        "policy skills (security/compliance/UX)",
        None,
        "none exist yet; pending item 4",
    )


def stage_build(
    r: Report, repo: Path, installed: subprocess.CompletedProcess[str]
) -> None:
    subjects = git(repo, "log", "--format=%s")
    r.add(
        "3 build",
        "build mode installs with one install commit",
        installed.returncode == 0 and "chore: install build mode" in subjects,
        installed.stderr.strip()[-120:],
    )
    if installed.returncode != 0:
        return
    paths = {
        "SPEC.md edit": ("Edit", "SPEC.md"),
        ".claude/settings.json write": ("Write", ".claude/settings.json"),
        "gate rewrite": ("Write", ".factory/gates/tests.py"),
    }
    for label, (tool, rel) in paths.items():
        verdict = hook(repo, "protect-paths.mjs", tool, {"file_path": str(repo / rel)})
        r.add("3 build", f"protect-paths denies {label}", verdict == "deny", verdict)
    verdict = hook(
        repo, "protect-paths.mjs", "Write", {"file_path": str(repo / "src/x.py")}
    )
    r.add("3 build", "protect-paths allows a source edit", verdict == "allow", verdict)
    verdict = hook(
        repo,
        "secret-guard.mjs",
        "Write",
        {"file_path": "a.py", "content": f'KEY = "{FAKE_KEY}"'},
    )
    r.add("3 build", "secret-guard denies a credential", verdict == "deny", verdict)
    verdict = hook(
        repo, "secret-guard.mjs", "Write", {"file_path": "a.py", "content": "x = 1"}
    )
    r.add("3 build", "secret-guard allows clean code", verdict == "allow", verdict)
    lines = (repo / "CLAUDE.md").read_text().count("\n")
    r.add("3 build", "CLAUDE.md under a page", lines <= 60, f"{lines} lines")
    r.add(
        "3 build",
        "plan committed",
        (repo / "PLAN.md").exists()
        and git(repo, "log", "--format=%h", "--", "PLAN.md") != "",
    )


def stage_test(r: Report, repo: Path, name: str) -> None:
    fast = sh(
        repo,
        "bash",
        "-c",
        "uv run pytest -q && uv run ruff check --isolated src tests --exclude old.py && uv run mypy --strict --config-file .factory/gates/mypy.ini src/"
        + name
        + "/core.py",
    )
    tail = (fast.stdout + fast.stderr).strip().splitlines()
    r.add(
        "4 test",
        "tests, lint and types run as single commands",
        fast.returncode == 0,
        tail[-1][:100] if fast.returncode and tail else "",
    )
    (repo / ".fix-mode").write_text("")
    existing = {"file_path": str(repo / "tests/test_core.py")}
    verdict = hook(repo, "fix-mode-guard.mjs", "Edit", existing)
    r.add(
        "4 test", "fix-mode blocks editing an existing test", verdict == "deny", verdict
    )
    verdict = hook(
        repo,
        "fix-mode-guard.mjs",
        "Write",
        {"file_path": str(repo / "tests/test_new.py")},
    )
    r.add("4 test", "fix-mode allows a new failing test", verdict == "allow", verdict)
    (repo / ".fix-mode").unlink()
    verdict = hook(repo, "fix-mode-guard.mjs", "Edit", existing)
    r.add("4 test", "fix-mode off allows editing a test", verdict == "allow", verdict)
    r.add(
        "4 test",
        "evals for agent behaviour",
        None,
        "kit scenario only; a generic repo has no model to eval",
    )


def stage_deploy(r: Report, repo: Path) -> None:
    review = (repo / "REVIEW.md").read_text() if (repo / "REVIEW.md").exists() else ""
    r.add(
        "5 deploy",
        "REVIEW.md has passes and severity levels",
        "Severity" in review and "blocker" in review,
    )
    deny = json.loads((repo / ".claude/settings.json").read_text())["permissions"][
        "deny"
    ]
    wanted = ("push --force", "git reset", "commit --amend")
    r.add(
        "5 deploy",
        "deny rules block force push, hard reset, amend",
        all(any(p in d for d in deny) for p in wanted),
    )
    r.add(
        "5 deploy",
        "branch protection and AI PR review",
        None,
        "needs GitHub; pending item 3",
    )
    r.add(
        "5 deploy", "rollback rehearsal", None, "a library has no deploy to roll back"
    )


def stage_stop_report(r: Report, repo: Path) -> None:
    """Complete plan but no report yet: the cheap completeness check must block before any gate runs."""
    out = stop_hook(repo)
    reason = out.get("reason", "")
    r.add(
        "3 build",
        "Stop hook blocks until BUILD-REPORT.md is written",
        out.get("decision") == "block" and "BUILD-REPORT.md" in reason,
        reason[:70],
    )


def stage_stop_complete(r: Report, repo: Path) -> None:
    write(repo, "BUILD-REPORT.md", "COMPLETE\n\nrehearsal\n")
    commit(repo, "docs: build report")
    sh(repo, "git", "push", "-q", "-u", "origin", "main")
    out = stop_hook(repo)
    report_file = repo / "BUILD-REPORT.md"
    report = report_file.read_text().splitlines()[0] if report_file.exists() else ""
    allowed = out.get("decision") not in ("block", "crash")
    r.add(
        "3 build",
        "Stop hook allows a finished build after all six gates",
        allowed,
        out.get("reason", "")[:90],
    )
    phase_file = repo / ".factory/phase"
    phase = phase_file.read_text().strip() if phase_file.exists() else ""
    r.add(
        "6 maintain",
        "phase flips to maintain after COMPLETE",
        phase == "maintain",
        f"phase={phase!r} report={report!r}",
    )
    ahead = git(repo, "rev-list", "--count", "@{u}..HEAD")
    r.add(
        "5 deploy",
        "the flip-to-maintain commit is pushed",
        ahead == "0",
        f"ahead={ahead}",
    )
    write(repo, "SPEC.md", "tampered\n")
    out = stop_hook(repo)
    r.add(
        "6 maintain",
        "maintain phase still blocks a protected-file edit",
        out.get("decision") == "block" and "protected" in out.get("reason", ""),
        out.get("reason", "")[:70],
    )


def greenfield(base: Path, full: bool) -> Report:
    r = Report("greenfield: empty repo -> intent -> spec -> plan -> build mode")
    name = "wordkit"
    repo = new_repo(base, "green")
    write(repo, ".gitignore", ".venv/\n__pycache__/\n")
    seed(repo, name, legacy=False)
    commit(repo, "feat: count_words")
    sha = git(repo, "rev-parse", "--short", "HEAD")
    adopt_artifacts(repo, name, "Pat Owner")
    demo = f"uv run python -c 'import {name}'"
    write(repo, "PLAN.md", PLAN_DONE.format(sha=sha, demo=demo))
    commit(repo, "docs: plan")
    remote = base / "green-remote.git"
    sh(base, "git", "init", "-q", "--bare", str(remote))
    sh(repo, "git", "remote", "add", "origin", str(remote))
    sh(repo, "uv", "lock")
    commit(repo, "chore: lockfile")
    stage_plan_design(r, repo)
    installed = install(repo, demo)
    stage_build(r, repo, installed)
    if installed.returncode == 0:
        stage_test(r, repo, name)
        stage_deploy(r, repo)
        sh(repo, "git", "push", "-q", "-u", "origin", "main")
        stage_stop_report(r, repo)
        if full:
            stage_stop_complete(r, repo)
        else:
            r.add(
                "3 build",
                "Stop hook allows a finished build (all six gates)",
                None,
                "slow; run `all-gates`",
            )
    return r


def brownfield(base: Path) -> Report:
    r = Report(
        "brownfield: existing code with history, user hooks and legacy lint debt"
    )
    name = "legacykit"
    repo = new_repo(base, "brown")
    write(repo, ".gitignore", ".venv/\n__pycache__/\nmy-private.txt\n")
    seed(repo, name, legacy=True)
    user_hook = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [{"type": "command", "command": "echo user-hook"}],
                }
            ]
        }
    }
    write(repo, ".claude/settings.json", json.dumps(user_hook, indent=2) + "\n")
    commit(repo, "feat: initial import", author="Old Timer <old@example.com>")
    extra = f"from {name} import count_words\n\n\ndef test_one() -> None:\n    assert count_words('x', 1) == 1\n"
    write(repo, "tests/test_more.py", extra)
    commit(repo, "test: more", author="Old Timer <old@example.com>")
    sh(repo, "uv", "lock")
    commit(repo, "chore: lockfile")
    history = int(git(repo, "rev-list", "--count", "HEAD"))
    # Playbook adoption order: plays with no prerequisites first (intent, CLAUDE.md, review guide), then guards.
    adopt_artifacts(repo, name, "Pat Owner")
    demo = f"uv run python -c 'import {name}'"
    write(repo, "PLAN.md", PLAN_OPEN.format(task="clean up legacy module", demo=demo))
    commit(repo, "docs: adoption plan")
    stage_plan_design(r, repo)
    installed = install(repo, demo)
    stage_build(r, repo, installed)
    if installed.returncode == 0:
        settings = json.loads((repo / ".claude/settings.json").read_text())
        kept = any(
            "user-hook" in h["command"]
            for g in settings["hooks"].get("PostToolUse", [])
            for h in g["hooks"]
        )
        r.add("3 build", "install keeps the team's existing hooks", kept)
        grew = int(git(repo, "rev-list", "--count", "HEAD")) > history
        r.add(
            "3 build",
            "install keeps existing history",
            grew and "Old Timer" in git(repo, "log", "--format=%an"),
        )
        r.add(
            "3 build",
            "install keeps existing .gitignore entries",
            "my-private.txt" in (repo / ".gitignore").read_text(),
        )
        lint = sh(
            repo,
            "bash",
            "-c",
            "uv run ruff check --isolated src tests && uv run ruff format --isolated --check src tests",
        )
        r.add(
            "4 test",
            "baseline: legacy code fails the lint gate (the expected debt)",
            lint.returncode != 0,
            "needs a cleanup task or ratchet before the Stop gate can pass",
        )
        r.add(
            "4 test",
            "baseline: existing tests pass",
            sh(repo, "uv", "run", "pytest", "-q").returncode == 0,
        )
        stage_test(r, repo, name)
        stage_deploy(r, repo)
        out = stop_hook(repo)
        reason = out.get("reason", "")
        r.add(
            "3 build",
            "Stop hook sends the agent to the open legacy task",
            out.get("decision") == "block" and reason.startswith("next task: 1."),
            reason[:70],
        )
    return r


def kit(base: Path) -> Report:
    """Stage 4 evals and stage 6 maintain, on mini-agent-kit's own sensors with seeded traces."""
    r = Report("kit: evals, sensors, drift tiers and the maintain loop")
    traces = base / "t"
    out = sh(KIT, "uv", "run", "python", "tools/eval_traces.py", "evals", str(traces))
    count = len(list(traces.glob("*.json")))
    r.add(
        "4 test",
        "offline evals run end to end",
        out.returncode == 0 and count >= 26,
        f"{count} traces",
    )
    r.add(
        "4 test",
        "pytest runs the evals",
        sh(KIT, "uv", "run", "pytest", "-q", "tests/test_evals.py").returncode == 0,
    )
    series, intents = base / "series", base / "intents"
    series.mkdir()
    intents.mkdir()
    for i in range(10):
        (series / f"{i:03d}.json").write_text((traces / "word-count.json").read_text())
    drift = [
        "uv",
        "run",
        "python",
        "tools/drift.py",
        str(series),
        "tools/drift.json",
        str(intents),
    ]
    steady = sh(KIT, *drift)
    r.add(
        "6 maintain",
        "steady traces stay within bands (tier 0)",
        steady.returncode == 0,
        steady.stdout.strip().splitlines()[-1] if steady.stdout else "",
    )
    for i in range(5, 10):
        (series / f"{i:03d}.json").write_text(
            (traces / "empty-script-is-error.json").read_text()
        )
    drifted = sh(KIT, *drift)
    r.add(
        "6 maintain",
        "100% recent failures reach tier 3 (propose)",
        drifted.returncode == 3,
        f"exit {drifted.returncode}",
    )
    written = list(intents.glob("*.md"))
    r.add(
        "6 maintain",
        "tier 3 writes intent files, not code",
        len(written) > 0 and not list(intents.glob("*.py")),
        f"{len(written)} intents",
    )
    sensor = sh(
        KIT, "uv", "run", "python", "tools/trace_sensor.py", str(series / "009.json")
    )
    r.add("6 maintain", "trace sensor flags the bad trace", sensor.returncode == 1)
    metrics = sh(KIT, "uv", "run", "python", "tools/metrics.py")
    r.add(
        "6 maintain",
        "metrics report plan drift, deploys/week, fix lag",
        metrics.returncode == 0 and "plan_drift" in metrics.stdout,
    )
    return r


def main(argv: list[str]) -> int:
    which = argv[0] if argv else "all"
    if not FACTORY.exists() and which != "kit":
        print(f"factory not found at {FACTORY}; set LIGHTS_ON_FACTORY")
        return 2
    base = Path(tempfile.mkdtemp(prefix="sdlc-rehearsal-"))
    reports: list[Report] = []
    try:
        if which in ("greenfield", "all", "all-gates"):
            reports.append(greenfield(base, full=which == "all-gates"))
        if which in ("brownfield", "all", "all-gates"):
            reports.append(brownfield(base))
        if which in ("kit", "all", "all-gates"):
            reports.append(kit(base))
    finally:
        if os.environ.get("KEEP"):
            print(f"kept {base}")
        else:
            shutil.rmtree(base, ignore_errors=True)
    for report in reports:
        report.show()
    failed = sum(r.failed for r in reports)
    print(f"\n{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
