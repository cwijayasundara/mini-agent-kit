"""metrics.py: DORA-style rates and plan-to-diff drift, computed on a throwaway git repo."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

_tools = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(_tools))
_spec = importlib.util.spec_from_file_location("metrics", _tools / "metrics.py")
assert _spec and _spec.loader
metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(metrics)

DAY = 86400


def _commit(repo: Path, subject: str, when: int) -> str:
    (repo / "f.txt").write_text(subject)
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": f"{when} +0000",
        "GIT_COMMITTER_DATE": f"{when} +0000",
    }
    for args in (["add", "."], ["commit", "-q", "-m", subject]):
        subprocess.run(
            ["git", *args], cwd=repo, check=True, env=env, capture_output=True
        )
    out = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "a"], cwd=tmp_path, check=True)
    return tmp_path


def test_deploys_per_week_counts_commits_over_the_span(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    for i in range(4):
        _commit(repo, f"feat: {i}", 1_700_000_000 + i * 7 * DAY)
    assert metrics.deploys_per_week(repo) == 4 / 3  # 4 commits across 3 weeks


def test_deploys_per_week_floors_the_span_at_one_week(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, "feat: a", 1_700_000_000)
    _commit(repo, "feat: b", 1_700_000_000 + 3600)
    assert metrics.deploys_per_week(repo) == 2.0


def test_fix_lag_hours_is_mean_gap_before_each_fix(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, "feat: a", 1_700_000_000)
    _commit(repo, "fix: a", 1_700_000_000 + 7200)
    _commit(repo, "feat: b", 1_700_000_000 + 8000)
    _commit(repo, "fix: b", 1_700_000_000 + 8000 + 14400)
    assert metrics.fix_lag_hours(repo) == 3.0


def test_fix_lag_hours_is_none_without_fixes(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, "feat: a", 1_700_000_000)
    assert metrics.fix_lag_hours(repo) is None


def test_plan_drift_is_share_of_feat_commits_missing_from_plan(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    planned = _commit(repo, "feat: planned", 1_700_000_000)
    _commit(repo, "feat: unplanned", 1_700_000_100)
    _commit(repo, "docs: not a feature", 1_700_000_200)
    (repo / "PLAN.md").write_text(f"- [x] 1. thing\n  done: {planned}\n")
    assert metrics.plan_drift(repo) == 0.5


def test_plan_drift_without_feat_commits_is_zero(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, "docs: only", 1_700_000_000)
    assert metrics.plan_drift(repo) == 0.0
