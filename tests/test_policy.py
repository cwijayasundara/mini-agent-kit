"""Policy tests: the rules in the policy skills that must always hold, enforced mechanically.

The skills under .claude/skills/policy-* are advisory; these tests are the hook behind them.
"""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "src" / "mini_agent_kit"
SKILLS = ROOT / ".claude" / "skills"
POLICIES = ("policy-security", "policy-compliance", "policy-cli-ux")
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_IMPORTS = {"subprocess", "pickle", "marshal", "shelve", "ctypes"}


def _trees() -> dict[str, ast.Module]:
    return {p.name: ast.parse(p.read_text()) for p in sorted(PKG.glob("*.py"))}


def test_no_dynamic_code_execution_in_runtime() -> None:
    bad = [
        f"{name}:{node.lineno} {node.func.id}()"
        for name, tree in _trees().items()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in FORBIDDEN_CALLS
    ]
    assert bad == [], f"policy-security: remove dynamic execution: {bad}"


def test_no_process_or_unsafe_deserialization_imports_in_runtime() -> None:
    bad = []
    for name, tree in _trees().items():
        for node in ast.walk(tree):
            mods = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            bad += [
                f"{name}:{node.lineno} {m}"
                for m in mods
                if m.split(".")[0] in FORBIDDEN_IMPORTS
            ]
    assert bad == [], f"policy-security: runtime may not import these: {bad}"


def test_api_key_is_only_read_in_fireworks_and_never_formatted_into_text() -> None:
    readers = [n for n, t in _trees().items() if "FIREWORKS_API_KEY" in ast.unparse(t)]
    assert readers == ["fireworks.py"], (
        f"policy-security: key read outside fireworks.py: {readers}"
    )
    tree = _trees()["fireworks.py"]
    leaks = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.JoinedStr)
        and ast.unparse(node) != "f'Bearer {api_key}'"  # the one Authorization header
        and any(
            isinstance(v, ast.FormattedValue)
            and re.search(r"\b(key|api_key)\b", ast.unparse(v.value))
            for v in node.values
        )
    ]
    assert leaks == [], (
        f"policy-security: key interpolated into a string at lines {leaks}"
    )


def test_runtime_has_no_third_party_dependencies() -> None:
    import sys

    allowed = set(sys.stdlib_module_names) | {"mini_agent_kit"}
    bad = []
    for name, tree in _trees().items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                mods = [node.module or ""]
            else:
                continue
            bad += [
                f"{name}:{node.lineno} {m}"
                for m in mods
                if m.split(".")[0] not in allowed
            ]
    assert bad == [], f"policy-compliance: runtime must stay stdlib-only: {bad}"


def test_demo_output_is_the_four_spec_lines() -> None:
    import contextlib
    import io

    from mini_agent_kit.cli import main

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["demo"]) == 0
    lines = out.getvalue().splitlines()
    assert lines[0].startswith("question: ") and lines[-1].startswith("answer: "), (
        "policy-cli-ux: the demo keeps its question: / step N: / answer: shape"
    )


@pytest.mark.parametrize("name", POLICIES)
def test_policy_skill_exists_with_frontmatter_and_enforcement_section(
    name: str,
) -> None:
    path = SKILLS / name / "SKILL.md"
    assert path.exists(), (
        f"add {path.relative_to(ROOT)} (see docs/sdlc-gap-analysis.md, stage 2)"
    )
    text = path.read_text()
    head = text.split("---")[1] if text.startswith("---") else ""
    assert f"name: {name}" in head and "description:" in head, (
        f"{name}: frontmatter needs name and description"
    )
    assert "## Enforced by" in text, (
        f"{name}: say which test or hook backs each rule, under '## Enforced by'"
    )


def test_claude_md_points_at_the_policy_skills() -> None:
    text = (ROOT / "CLAUDE.md").read_text()
    assert all(name in text for name in POLICIES), "list the policy skills in CLAUDE.md"


def test_ai_review_workflow_is_safe_and_cheap() -> None:
    lines = (ROOT / ".github/workflows/ai-review.yml").read_text().splitlines()
    text = "\n".join(
        line.split(" # ")[0] for line in lines if not line.lstrip().startswith("#")
    )
    assert "pull_request_target" not in text, (
        "policy-security: fork PRs must never receive secrets"
    )
    assert re.search(r"claude-code-action@[0-9a-f]{40}", "\n".join(lines)), (
        "policy-security: pin the action to a commit SHA"
    )
    assert "opus" not in text.lower(), (
        "policy-compliance: the reviewer runs on Sonnet, not Opus (cost)"
    )
    assert "contents: write" not in text and "id-token" not in text, (
        "policy-security: the reviewer may only read and comment"
    )
    assert (
        "--allowedTools" in text and "Write" not in text.split("--allowedTools")[1]
    ), "the reviewer may not edit files"
    assert "REVIEW.md" in text, "the review follows REVIEW.md"


def test_codeowners_covers_the_guards() -> None:
    owners = (ROOT / ".github/CODEOWNERS").read_text()
    for path in ("/.claude/", "/.factory/", "/.github/", "/SPEC.md"):
        assert path in owners, f"policy-security: CODEOWNERS must cover {path}"
