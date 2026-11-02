"""Architecture fitness tests: the layering and purity rules the design depends on.

Each failure message says what to change, so an agent can fix it unaided.
"""

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "src" / "mini_agent_kit"
NAME = "mini_agent_kit"

# module -> package modules it may import. Anything else is a layering violation.
ALLOWED: dict[str, set[str]] = {
    "types": set(),
    "model": {"types"},
    "registry": {"types"},
    "trace": {"types"},
    "scripted": {"types"},
    "fireworks": {"types"},
    "toys": {"registry"},
    "agent": {"model", "registry", "trace", "types"},
    "cli": {"agent", "fireworks", "model", "scripted", "toys", "trace"},
}
# Only these modules may touch the network.
NETWORK_MODULES = {"fireworks"}
NETWORK_IMPORTS = {"urllib", "socket", "http", "ssl", "requests", "httpx"}


def _modules() -> dict[str, ast.Module]:
    return {
        p.stem: ast.parse(p.read_text())
        for p in sorted(PKG.glob("*.py"))
        if p.stem not in {"__init__", "__main__"}
    }


def _imports(tree: ast.Module) -> list[str]:
    """Dotted names imported anywhere in the module."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
    return names


def test_every_module_has_a_layer() -> None:
    unknown = set(_modules()) - set(ALLOWED)
    assert not unknown, (
        f"new module(s) {sorted(unknown)} have no layer: add them to ALLOWED in "
        "tests/test_architecture.py with the modules they may import"
    )


def test_modules_only_import_their_allowed_layers() -> None:
    for name, tree in _modules().items():
        for imported in _imports(tree):
            top, _, rest = imported.partition(".")
            if top != NAME:
                continue
            target = rest.split(".")[0]
            assert target in ALLOWED[name], (
                f"{name}.py imports {NAME}.{target}, which the layering forbids; "
                f"{name} may only import {sorted(ALLOWED[name])}. "
                "Move the shared code down a layer, or pass it in as an argument"
            )


def test_runtime_depends_on_the_standard_library_only() -> None:
    stdlib = sys.stdlib_module_names
    for name, tree in _modules().items():
        for imported in _imports(tree):
            top = imported.split(".")[0]
            assert top == NAME or top in stdlib, (
                f"{name}.py imports third-party '{top}'; SPEC.md requires "
                "the runtime to use the standard library only"
            )


def test_only_the_provider_module_touches_the_network() -> None:
    for name, tree in _modules().items():
        if name in NETWORK_MODULES:
            continue
        used = {i.split(".")[0] for i in _imports(tree)} & NETWORK_IMPORTS
        assert not used, (
            f"{name}.py imports {sorted(used)}; network access is confined to "
            f"{sorted(NETWORK_MODULES)} (SPEC.md Out of scope). "
            "Take a Model in as a parameter instead"
        )


SECRET = re.compile(
    r"(fw_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    r"(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"])",
    re.IGNORECASE,
)


def test_no_secrets_in_tracked_files() -> None:
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for rel in filter(None, listing.split("\0")):
        path = ROOT / rel
        if not path.is_file() or path.suffix in {".lock", ".pyc"}:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        match = SECRET.search(text)
        assert not match, (
            f"{rel} looks like it contains a credential ('{match and match.group(0)[:8]}...'); "
            "remove it and read the value from the environment, as fireworks.py does"
        )
