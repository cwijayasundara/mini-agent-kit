"""Harness metrics derived from git history and the plan.

Usage: uv run python tools/metrics.py [repo-dir]
Reports: commits, share that are fixes, share of commits touching tests, plan tasks done,
and eval counts. A rising fix share or falling plan completion is a signal to improve a guide.
"""

import re
import subprocess
import sys
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


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
        "plan_done_share": done / total if total else 0.0,
        "evals": len(list((repo / "evals").glob("*.json"))),
        "live_evals": len(list((repo / "evals" / "live").glob("*.json"))),
    }


def main(argv: list[str]) -> int:
    for name, value in collect(Path(argv[0]) if argv else Path(".")).items():
        print(
            f"{name}: {value:.2f}" if isinstance(value, float) else f"{name}: {value}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
