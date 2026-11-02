"""Harness metrics derived from git history and the plan.

Usage: uv run python tools/metrics.py [repo-dir]
Reports: commits, share that are fixes, share of commits touching tests, plan tasks done,
and eval counts. A rising fix share or falling plan completion is a signal to improve a guide.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


REWORK_LOOKBACK = 3


def rework_share(repo: Path) -> float:
    """Share of commits (after the first) touching a file changed in one of the 3 commits before."""
    shas = _git(repo, "log", "--reverse", "--format=%H").split()
    touched = [
        set(_git(repo, "show", "--name-only", "--format=", s).split()) for s in shas
    ]
    if len(touched) < 2:
        return 0.0
    hits = sum(
        1
        for i in range(1, len(touched))
        if touched[i] & set().union(*touched[max(0, i - REWORK_LOOKBACK) : i])
    )
    return hits / (len(touched) - 1)


def ci_pass_share(repo: Path) -> float | None:
    """Share of recent GitHub Actions runs that passed, or None when gh is unavailable."""
    try:
        out = subprocess.run(
            ["gh", "run", "list", "--limit", "30", "--json", "conclusion"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    runs = [r["conclusion"] for r in json.loads(out) if r["conclusion"]]
    return runs.count("success") / len(runs) if runs else None


def collect(repo: Path) -> dict[str, float]:
    """Return the metrics as a name -> value mapping."""
    subjects = _git(repo, "log", "--format=%s").splitlines()
    commits = len(subjects)
    fixes = sum(1 for s in subjects if re.match(r"(fix|revert)\b", s))
    with_tests = sum(
        1
        for sha in _git(repo, "log", "--format=%H").split()
        if "tests/" in _git(repo, "show", "--name-only", "--format=", sha)
    )
    plan = repo / "PLAN.md"
    text = plan.read_text() if plan.exists() else ""
    done, total = (
        len(re.findall(r"^- \[x\]", text, re.MULTILINE)),
        len(re.findall(r"^- \[[ x!]\]", text, re.MULTILINE)),
    )
    return {
        "commits": commits,
        "fix_share": fixes / commits if commits else 0.0,
        "test_touch_share": with_tests / commits if commits else 0.0,
        "rework_share": rework_share(repo),
        "plan_done_share": done / total if total else 0.0,
        "evals": len(list((repo / "evals").glob("*.json"))),
        "live_evals": len(list((repo / "evals" / "live").glob("*.json"))),
    }


def main(argv: list[str]) -> int:
    repo = Path(argv[0]) if argv else Path(".")
    ci = ci_pass_share(repo)
    print(f"ci_pass_share: {ci:.2f}" if ci is not None else "ci_pass_share: n/a")
    for name, value in collect(repo).items():
        print(
            f"{name}: {value:.2f}" if isinstance(value, float) else f"{name}: {value}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
