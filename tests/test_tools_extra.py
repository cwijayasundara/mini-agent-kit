"""Metrics, fix-mode guard and live-eval checking."""

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def _load(name: str):  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_metrics_from_a_small_repo(tmp_path: Path) -> None:
    metrics = _load("metrics")
    _git(tmp_path, "init", "-q")
    (tmp_path / "PLAN.md").write_text("- [x] 1. a\n- [ ] 2. b\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("x")
    (tmp_path / "evals").mkdir()
    (tmp_path / "evals" / "a.json").write_text("{}")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "feat: one")
    (tmp_path / "f.txt").write_text("f")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "fix: two")
    got = metrics.collect(tmp_path)
    assert got == {
        "commits": 2,
        "fix_share": 0.5,
        "test_touch_share": 0.5,
        "rework_share": 0.0,
        "plan_drift": 1.0,
        "deploys_per_week": 2.0,
        "plan_done_share": 0.5,
        "evals": 1,
        "live_evals": 0,
    }
    assert metrics.main([str(tmp_path)]) == 0


def test_metrics_on_empty_inputs(tmp_path: Path) -> None:
    metrics = _load("metrics")
    _git(tmp_path, "init", "-q")
    (tmp_path / "x").write_text("x")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "chore: x")
    got = metrics.collect(tmp_path)
    assert got["plan_done_share"] == 0.0 and got["fix_share"] == 0.0


class _Model:
    """Stands in for FireworksModel: answers immediately."""

    def complete(self, messages, tools):  # type: ignore[no-untyped-def]
        from mini_agent_kit.types import ModelReply

        return ModelReply("the answer is 42", ())


def test_live_eval_check_passes_and_fails(tmp_path: Path) -> None:
    live = _load("live_evals")
    out = tmp_path / "t.json"
    assert live.check({"question": "q", "contains": "42"}, _Model(), out) == []
    assert out.exists()
    failed = live.check({"question": "q", "contains": "99"}, _Model(), out)
    assert len(failed) == 1 and "lacks '99'" in failed[0]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_fix_mode_guard(tmp_path: Path) -> None:
    hook = ROOT / ".claude" / "hooks" / "fix-mode-guard.mjs"
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "old.py").write_text("x")

    def ask(path: str) -> str:
        return subprocess.run(
            ["node", str(hook)],
            check=False,
            input=json.dumps({"tool_input": {"file_path": str(tmp_path / path)}}),
            env={
                "CLAUDE_PROJECT_DIR": str(tmp_path),
                "PATH": "/usr/bin:/opt/homebrew/bin",
            },
            capture_output=True,
            text=True,
        ).stdout

    assert ask("tests/old.py") == ""  # not in fix mode
    (tmp_path / ".fix-mode").write_text("")
    assert "fix mode" in ask("tests/old.py")  # existing test blocked
    assert ask("tests/new.py") == ""  # new test allowed
    assert ask("src/code.py") == ""  # code allowed


def test_rework_share_counts_overlapping_files(tmp_path: Path) -> None:
    metrics = _load("metrics")
    _git(tmp_path, "init", "-q")
    for i, name in enumerate(["a", "b", "a", "c"]):
        (tmp_path / f"{name}.txt").write_text(str(i))
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-qm", f"commit {i}")
    assert metrics.rework_share(tmp_path) == pytest.approx(
        1 / 3
    )  # only the second edit of a.txt


def test_ci_pass_share_is_none_without_gh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    metrics = _load("metrics")
    monkeypatch.setenv("PATH", "/nonexistent")
    assert metrics.ci_pass_share(tmp_path) is None
