import pytest

from mini_agent_kit.registry import Registry


def test_register_returns_function_unchanged() -> None:
    reg = Registry()

    def add(a: int) -> int:
        """Add."""
        return a

    assert reg.register(add) is add


def test_decorator_returns_function_unchanged() -> None:
    reg = Registry()

    @reg.tool
    def add(a: int) -> int:
        """Add."""
        return a + 1

    assert add(1) == 2
    assert reg.schemas()[0]["name"] == "add"


def test_description_is_first_paragraph() -> None:
    reg = Registry()

    @reg.tool
    def f(a: int) -> int:
        """First line
        continues here.

        Second paragraph.
        """
        return a

    assert reg.schemas()[0]["description"] == "First line continues here."


def test_missing_docstring_rejected() -> None:
    def f(a: int) -> int:
        return a

    with pytest.raises(ValueError, match="f"):
        Registry().register(f)


def test_blank_docstring_rejected() -> None:
    def f(a: int) -> int:
        return a

    f.__doc__ = "   "
    with pytest.raises(ValueError):
        Registry().register(f)


def test_duplicate_name_rejected() -> None:
    reg = Registry()

    def f() -> int:
        """F."""
        return 1

    reg.register(f)
    with pytest.raises(ValueError, match="already"):
        reg.register(f)
