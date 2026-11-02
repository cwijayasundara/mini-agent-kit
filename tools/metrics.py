"""Harness metrics derived from git history and the plan.

Usage: uv run python tools/metrics.py [repo-dir]
Reports: commits, share that are fixes, share of commits touching tests, plan tasks done,
plan-to-diff drift, deploys per week, fix lag, and eval counts. Lead time needs PRs (n/a). A rising fix share or falling plan completion is a signal to improve a guide.
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


def deploys_per_week(repo: Path) -> float:
    """DORA deployment frequency: every commit on main counts as a deploy; span floored at one week."""
    stamps = [int(t) for t in _git(repo, "log", "--format=%ct").split()]
    if not stamps:
        return 0.0
    weeks = max((max(stamps) - min(stamps)) / (7 * 86400), 1.0)
    return len(stamps) / weeks


def fix_lag_hours(repo: Path) -> float | None:
    """Mean hours between a fix commit and the commit before it (a proxy for time to restore)."""
    rows = [
        line.split(" ", 1)
        for line in _git(repo, "log", "--reverse", "--format=%ct %s").splitlines()
    ]
    gaps = [
        (int(rows[i][0]) - int(rows[i - 1][0])) / 3600
        for i in range(1, len(rows))
        if re.match(r"(fix|revert)\b", rows[i][1])
    ]
    return sum(gaps) / len(gaps) if gaps else None


def plan_drift(repo: Path) -> float:
    """Share of feat commits whose sha is not recorded as a `done:` in PLAN.md (work outside the plan)."""
    plan = repo / "PLAN.md"
    planned = (
        set(re.findall(r"^\s*done: (\w+)", plan.read_text(), re.MULTILINE))
        if plan.exists()
        else set()
    )
    feats = [
        line.split()[0]
        for line in _git(repo, "log", "--format=%h %s").splitlines()
        if re.match(r"\w+ feat\b", line)
    ]
    return sum(1 for sha in feats if sha not in planned) / len(feats) if feats else 0.0


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
        "plan_drift": plan_drift(repo),
        "deploys_per_week": deploys_per_week(repo),
        "plan_done_share": done / total if total else 0.0,
        "evals": len(list((repo / "evals").glob("*.json"))),
        "live_evals": len(list((repo / "evals" / "live").glob("*.json"))),
    }


def main(argv: list[str]) -> int:
    repo = Path(argv[0]) if argv else Path(".")
    ci = ci_pass_share(repo)
    print(f"ci_pass_share: {ci:.2f}" if ci is not None else "ci_pass_share: n/a")
    lag = fix_lag_hours(repo)
    print(f"fix_lag_hours: {lag:.2f}" if lag is not None else "fix_lag_hours: n/a")
    print("lead_time: n/a (needs a PR flow)")
    for name, value in collect(repo).items():
        print(
            f"{name}: {value:.2f}" if isinstance(value, float) else f"{name}: {value}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
